const extensionApi = globalThis.browser ?? globalThis.chrome;

extensionApi.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "GET_SELECTED_TEXT") {
    return;
  }

  const text = getSelectedText();

  sendResponse({
    text
  });
});

function getSelectedText() {
  const selection = window.getSelection();

  if (!selection) {
    return "";
  }

  return selection.toString().trim();
}
