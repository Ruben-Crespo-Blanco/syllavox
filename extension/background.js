const extensionApi = globalThis.browser ?? globalThis.chrome;

const API_BASE_URL = "http://127.0.0.1:8765";
const SPEAK_ENDPOINT = `${API_BASE_URL}/v1/speak`;
const STATUS_ENDPOINT = `${API_BASE_URL}/v1/status`;

const CONTEXT_MENU_ID = "read-selected-text-locally";

extensionApi.runtime.onInstalled.addListener(() => {
  extensionApi.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Read selected text locally",
    contexts: ["selection"]
  });
});

extensionApi.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== CONTEXT_MENU_ID) {
    return;
  }

  try {
    const selectedText = getSelectedText(info);

    if (!selectedText) {
      showNotification(
        "No text selected",
        "Select text first, then try again."
      );
      return;
    }

    const requestId = createRequestId();

    const statusResult = await getStatus();

    if (!statusResult.ok) {
      showNotification(
        "Read aloud unavailable",
        statusResult.message
      );
      return;
    }

    const speakResult = await speakText(selectedText, requestId);

    if (speakResult.status === "accepted") {
      return;
    }

    showNotification(
      "Read aloud failed",
      getApiErrorMessage(speakResult)
    );
  } catch (error) {
    showNotification(
      "Local app unavailable",
      "Start the Syllavox desktop app and try again."
    );

    console.error("Read selected text locally failed:", error);
  }
});

function getSelectedText(info) {
  return (info.selectionText || "").trim();
}

async function speakText(text, requestId) {
  const result = await requestJson(
    SPEAK_ENDPOINT,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text,
        requestId
      })
    },
    5000,
    {
      timeoutMessage: "Local API request timed out.",
      networkMessage: "Local desktop app is unreachable."
    }
  );

  if (!result.ok) {
    return {
      status: "rejected",
      requestId,
      error: result.error
    };
  }

  return result.payload;
}

async function getStatus() {
  const result = await requestJson(
    STATUS_ENDPOINT,
    { method: "GET" },
    3000,
    {
      timeoutMessage: "Syllavox did not respond. Check that the desktop app is running.",
      networkMessage: "Syllavox is not running. Start the desktop app and try again."
    }
  );

  if (!result.ok) {
    return {
      ok: false,
      ...result.error
    };
  }

  const payload = result.payload;

  if (!payload.backend?.healthy) {
    return {
      ok: false,
      code: "BACKEND_UNAVAILABLE",
      message: "Text-to-speech backend is unavailable. Check the desktop app."
    };
  }

  return {
    ok: true,
    payload
  };
}

async function requestJson(endpoint, options, timeoutMs, messages) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(endpoint, {
      ...options,
      signal: controller.signal
    });

    if (!response.ok) {
      return {
        ok: false,
        error: {
          code: "HTTP_ERROR",
          message: `Local API returned HTTP ${response.status}.`
        }
      };
    }

    return {
      ok: true,
      payload: await response.json()
    };
  } catch (error) {
    return {
      ok: false,
      error: {
        code: error.name === "AbortError" ? "TIMEOUT" : "NETWORK_ERROR",
        message: error.name === "AbortError"
          ? messages.timeoutMessage
          : messages.networkMessage
      }
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

function createRequestId() {
  const bytes = crypto.getRandomValues(new Uint8Array(4));

  const random = Array.from(bytes)
    .map((byteValue) => byteValue.toString(16).padStart(2, "0"))
    .join("");

  return `browser-extension-${Date.now()}-${random}`;
}

function getApiErrorMessage(apiPayload) {
  const code = apiPayload?.error?.code;
  const message = apiPayload?.error?.message || "";

  if (code === "NETWORK_ERROR") {
    return "Syllavox is not running. Start the desktop app and try again.";
  }

  if (code === "TIMEOUT") {
    return "Syllavox did not respond. Check that the desktop app is running.";
  }

  if (code === "EMPTY_TEXT") {
    return "No text selected. Select text first, then try again.";
  }

  if (
    code === "TEXT_TOO_LONG" ||
    message.toLowerCase().includes("maximum length") ||
    message.toLowerCase().includes("too long")
  ) {
    return "Selected text is too long. Try a shorter selection.";
  }

  if (code === "BACKEND_UNAVAILABLE") {
    return "Text-to-speech backend is unavailable. Check the desktop app.";
  }

  if (code === "BUSY") {
    return "The local reader is busy. Try again.";
  }

  return "Could not read text locally. Check the desktop app logs.";
}

function showNotification(title, message) {
  extensionApi.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title,
    message
  });
}
