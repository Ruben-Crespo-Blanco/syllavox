import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const testsDirectory = path.dirname(fileURLToPath(import.meta.url));
const extensionDirectory = path.resolve(testsDirectory, "..");

function makeEvent() {
  const listeners = [];

  return {
    listeners,
    addListener(listener) {
      listeners.push(listener);
    },
    async emit(...args) {
      return Promise.all(listeners.map((listener) => listener(...args)));
    }
  };
}

function makeChromeMock({ selectedText = "" } = {}) {
  const installed = makeEvent();
  const clicked = makeEvent();
  const messages = makeEvent();
  const createdMenus = [];
  const notifications = [];

  const chrome = {
    runtime: {
      onInstalled: installed,
      onMessage: messages
    },
    contextMenus: {
      onClicked: clicked,
      create(menu) {
        createdMenus.push(menu);
      }
    },
    tabs: {
      async sendMessage() {
        return { text: selectedText };
      }
    },
    notifications: {
      create(notification) {
        notifications.push(notification);
      }
    }
  };

  return {
    chrome,
    events: { installed, clicked, messages },
    createdMenus,
    notifications
  };
}

class TestAbortController {
  constructor() {
    this.signal = { aborted: false };
  }

  abort() {
    this.signal.aborted = true;
  }
}

function makeResponse(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return payload;
    }
  };
}

function loadBackground({
  fetchImpl = async () => makeResponse({}),
  apiNamespace = "chrome"
} = {}) {
  const browser = makeChromeMock();
  const apiGlobals = apiNamespace === "browser"
    ? { browser: browser.chrome, chrome: undefined }
    : { browser: undefined, chrome: browser.chrome };
  const context = vm.createContext({
    AbortController: TestAbortController,
    ...apiGlobals,
    clearTimeout,
    console,
    crypto: {
      getRandomValues(bytes) {
        bytes.fill(0x0a);
        return bytes;
      }
    },
    fetch: fetchImpl,
    setTimeout,
    Uint8Array
  });

  const source = fs.readFileSync(
    path.join(extensionDirectory, "background.js"),
    "utf8"
  );
  vm.runInContext(source, context, {
    filename: "background.js"
  });

  return { ...browser, context };
}

function loadContentScript({ selectedText = "", apiNamespace = "chrome" } = {}) {
  const message = makeEvent();
  const api = {
    runtime: {
      onMessage: message
    }
  };
  const apiGlobals = apiNamespace === "browser"
    ? { browser: api, chrome: undefined }
    : { browser: undefined, chrome: api };
  const context = vm.createContext({
    ...apiGlobals,
    window: {
      getSelection() {
        return {
          toString() {
            return selectedText;
          }
        };
      }
    }
  });

  const source = fs.readFileSync(
    path.join(extensionDirectory, "content.js"),
    "utf8"
  );
  vm.runInContext(source, context, {
    filename: "content.js"
  });

  return { message };
}

function readJson(filename) {
  return JSON.parse(
    fs.readFileSync(path.join(extensionDirectory, filename), "utf8")
  );
}

function toPlainValue(value) {
  return JSON.parse(JSON.stringify(value));
}

test("manifests reference the required extension files and permissions", () => {
  for (const filename of ["manifest.json", "manifest.firefox.json"]) {
    const manifest = readJson(filename);

    assert.equal(manifest.manifest_version, 3);
    assert.ok(manifest.permissions.includes("contextMenus"));
    assert.ok(manifest.permissions.includes("notifications"));
    assert.ok(!manifest.permissions.includes("activeTab"));
    assert.ok(!manifest.permissions.includes("scripting"));
    assert.ok(manifest.host_permissions.includes("http://127.0.0.1:8765/*"));
    assert.equal(manifest.content_scripts, undefined);

    const backgroundFiles = manifest.background.service_worker
      ? [manifest.background.service_worker]
      : manifest.background.scripts;

    for (const backgroundFile of backgroundFiles) {
      assert.ok(fs.existsSync(path.join(extensionDirectory, backgroundFile)));
    }

    for (const iconPath of Object.values(manifest.icons)) {
      assert.ok(fs.existsSync(path.join(extensionDirectory, iconPath)));
    }
  }
});

test("Firefox manifest declares a stable Gecko identity and no data collection", () => {
  const manifest = readJson("manifest.firefox.json");

  assert.deepEqual(manifest.background, {
    scripts: ["background.js"]
  });
  assert.equal(
    manifest.browser_specific_settings.gecko.id,
    "@syllavox"
  );
  assert.deepEqual(
    manifest.browser_specific_settings.gecko.data_collection_permissions,
    { required: ["none"] }
  );
  assert.equal(manifest.minimum_chrome_version, undefined);
});

test("installation lifecycle creates the selection context menu", async () => {
  const browser = loadBackground();

  assert.equal(browser.events.installed.listeners.length, 1);

  await browser.events.installed.emit();

  assert.deepEqual(toPlainValue(browser.createdMenus), [
    {
      id: "read-selected-text-locally",
      title: "Read selected text locally",
      contexts: ["selection"]
    }
  ]);
});

test("selected text is sent to the local API after a healthy status check", async () => {
  const calls = [];
  const browser = loadBackground({
    fetchImpl: async (url, options) => {
      calls.push({ url, options });

      if (url.endsWith("/status")) {
        return makeResponse({ backend: { healthy: true } });
      }

      return makeResponse({ status: "accepted", requestId: "request-1" });
    }
  });

  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: "  Selected text  "
    },
    { id: 42 }
  );

  assert.equal(calls.length, 2);
  assert.ok(calls[0].url.endsWith("/v1/status"));
  assert.ok(calls[1].url.endsWith("/v1/speak"));

  const requestBody = JSON.parse(calls[1].options.body);
  assert.equal(requestBody.text, "Selected text");
  assert.match(requestBody.requestId, /^browser-extension-/);
  assert.deepEqual(browser.notifications, []);
});

test("Firefox browser namespace supports context-menu speech", async () => {
  const calls = [];
  const browser = loadBackground({
    apiNamespace: "browser",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });

      if (url.endsWith("/status")) {
        return makeResponse({ backend: { healthy: true } });
      }

      return makeResponse({ status: "accepted" });
    }
  });

  await browser.events.installed.emit();
  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: "Firefox text"
    },
    { id: 3 }
  );

  assert.equal(browser.createdMenus.length, 1);
  assert.equal(calls.length, 2);
  assert.ok(calls[1].url.endsWith("/v1/speak"));
  assert.deepEqual(browser.notifications, []);
});

test("missing context-menu selection is reported without requesting page access", async () => {
  const calls = [];
  const browser = loadBackground({
    fetchImpl: async (url, options) => {
      calls.push({ url, options });

      if (url.endsWith("/status")) {
        return makeResponse({ backend: { healthy: true } });
      }

      return makeResponse({ status: "accepted" });
    }
  });
  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: ""
    },
    { id: 7 }
  );

  assert.equal(calls.length, 0);
  assert.equal(browser.notifications[0].title, "No text selected");
});

test("an empty selection produces a user notification without an API call", async () => {
  const calls = [];
  const browser = loadBackground({
    fetchImpl: async (...args) => {
      calls.push(args);
      return makeResponse({ backend: { healthy: true } });
    }
  });

  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: ""
    },
    null
  );

  assert.equal(calls.length, 0);
  assert.deepEqual(toPlainValue(browser.notifications), [
    {
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "No text selected",
      message: "Select text first, then try again."
    }
  ]);
});

test("an unhealthy backend is reported without sending speech", async () => {
  const calls = [];
  const browser = loadBackground({
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return makeResponse({ backend: { healthy: false } });
    }
  });

  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: "Selected text"
    },
    null
  );

  assert.equal(calls.length, 1);
  assert.ok(calls[0].url.endsWith("/v1/status"));
  assert.equal(browser.notifications[0].title, "Read aloud unavailable");
});

test("structured API rejection is translated into a helpful notification", async () => {
  const browser = loadBackground({
    fetchImpl: async (url) => {
      if (url.endsWith("/status")) {
        return makeResponse({ backend: { healthy: true } });
      }

      return makeResponse({
        status: "rejected",
        error: {
          code: "TEXT_TOO_LONG",
          message: "Text exceeds the maximum length."
        }
      });
    }
  });

  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: "Selected text"
    },
    null
  );

  assert.deepEqual(toPlainValue(browser.notifications[0]), {
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: "Read aloud failed",
    message: "Selected text is too long. Try a shorter selection."
  });
});

test("API failures produce the unavailable notification", async () => {
  const browser = loadBackground({
    fetchImpl: async () => {
      throw new Error("connection refused");
    }
  });

  await browser.events.clicked.emit(
    {
      menuItemId: "read-selected-text-locally",
      selectionText: "Selected text"
    },
    null
  );

  assert.equal(browser.notifications[0].title, "Read aloud unavailable");
  assert.match(browser.notifications[0].message, /not running/);
});

test("content script returns the current page selection", () => {
  const browser = loadContentScript({ selectedText: "  Page selection  " });

  assert.equal(browser.message.listeners.length, 1);

  let response;
  browser.message.listeners[0](
    { type: "GET_SELECTED_TEXT" },
    {},
    (payload) => {
      response = payload;
    }
  );

  assert.deepEqual(toPlainValue(response), { text: "Page selection" });
});

test("content script supports Firefox's browser namespace", () => {
  const browser = loadContentScript({
    apiNamespace: "browser",
    selectedText: "  Firefox selection  "
  });

  let response;
  browser.message.listeners[0](
    { type: "GET_SELECTED_TEXT" },
    {},
    (payload) => {
      response = payload;
    }
  );

  assert.deepEqual(toPlainValue(response), { text: "Firefox selection" });
});
