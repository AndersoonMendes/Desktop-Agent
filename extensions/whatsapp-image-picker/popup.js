const scanButton = document.querySelector("#scan");
const status = document.querySelector("#status");

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  status.textContent = "Procurando imagens na conversa aberta…";
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab?.url || "");
    if (url.protocol !== "https:" || url.hostname !== "web.whatsapp.com") {
      throw new Error("Abra web.whatsapp.com e o grupo desejado antes de procurar.");
    }
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
    status.textContent = "O seletor foi aberto na aba do WhatsApp.";
  } catch (error) {
    status.textContent = error.message || "Não foi possível acessar esta aba.";
  } finally {
    scanButton.disabled = false;
  }
});
