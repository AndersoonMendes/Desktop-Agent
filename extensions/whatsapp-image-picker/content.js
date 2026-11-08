(() => {
  const ROOT_ID = "desktop-ai-agent-image-picker";
  document.getElementById(ROOT_ID)?.remove();

  const root = document.querySelector("main") || document.body;
  const candidates = [...root.querySelectorAll("img")]
    .map((image) => {
      const rect = image.getBoundingClientRect();
      return { image, rect, src: image.currentSrc || image.src };
    })
    .filter(({ image, rect, src }) => (
      src && image.complete && image.naturalWidth >= 160 && image.naturalHeight >= 100
      && rect.width >= 120 && rect.height >= 80
      && getComputedStyle(image).visibility !== "hidden"
      && getComputedStyle(image).display !== "none"
    ));

  if (!candidates.length) {
    window.alert(
      "Não encontrei fotos carregadas nesta conversa. Abra o grupo, role até as mensagens recentes e tente novamente.",
    );
    return;
  }

  const panel = document.createElement("section");
  panel.id = ROOT_ID;
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Escolher imagem do WhatsApp");
  Object.assign(panel.style, {
    position: "fixed", inset: "5vh 5vw", zIndex: "2147483647", overflow: "auto",
    padding: "20px", borderRadius: "12px", background: "#fff", color: "#202124",
    boxShadow: "0 4px 28px #0008", font: "14px/1.4 Arial, sans-serif",
  });

  const heading = document.createElement("h2");
  const chatName = root.querySelector("header [title]")?.getAttribute("title")
    || root.querySelector("header")?.innerText?.split("\n")[0]?.trim()
    || "conversa aberta";
  heading.textContent = `Imagens em “${chatName}” (${candidates.length})`;
  heading.style.marginTop = "0";
  const hint = document.createElement("p");
  hint.textContent = "A lista segue a ordem visual do chat; a primeira opção é a mais recente entre as imagens carregadas. Confira antes de salvar.";

  const grid = document.createElement("div");
  Object.assign(grid.style, {
    display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
    gap: "12px", margin: "16px 0",
  });

  let selected = candidates.length - 1;
  const cards = candidates.map(({ image }, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.setAttribute("aria-pressed", String(index === selected));
    Object.assign(card.style, {
      padding: "8px", border: index === selected ? "3px solid #087f5b" : "1px solid #bbb",
      borderRadius: "8px", background: "#fff", cursor: "pointer", textAlign: "left",
    });
    const preview = document.createElement("img");
    preview.src = image.currentSrc || image.src;
    preview.alt = `Prévia da imagem ${index + 1}`;
    Object.assign(preview.style, { width: "100%", height: "125px", objectFit: "contain" });
    const label = document.createElement("span");
    const messageElement = image.closest("[data-pre-plain-text]");
    const sentAt = messageElement?.getAttribute("data-pre-plain-text") || "";
    label.textContent = `${index === candidates.length - 1 ? "Mais recente · " : ""}Imagem ${index + 1}${sentAt ? ` · ${sentAt}` : ""}`;
    card.append(preview, label);
    card.addEventListener("click", () => {
      selected = index;
      cards.forEach((other, otherIndex) => {
        other.style.border = otherIndex === selected ? "3px solid #087f5b" : "1px solid #bbb";
        other.setAttribute("aria-pressed", String(otherIndex === selected));
      });
    });
    grid.append(card);
    return card;
  });

  const message = document.createElement("p");
  message.setAttribute("role", "status");
  const actions = document.createElement("div");
  Object.assign(actions.style, { display: "flex", gap: "10px", position: "sticky", bottom: "0", background: "white", padding: "10px 0" });
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = "Salvar imagem selecionada";
  const close = document.createElement("button");
  close.type = "button";
  close.textContent = "Cancelar";
  [save, close].forEach((button) => Object.assign(button.style, {
    padding: "10px 14px", border: "0", borderRadius: "6px", cursor: "pointer",
  }));
  save.style.background = "#087f5b";
  save.style.color = "white";
  close.style.background = "#eee";

  save.addEventListener("click", async () => {
    const { image } = candidates[selected];
    const source = image.currentSrc || image.src;
    save.disabled = true;
    message.textContent = "Preparando o arquivo…";
    try {
      const response = await fetch(source, { credentials: "include" });
      if (!response.ok) throw new Error(`O WhatsApp não entregou a imagem (HTTP ${response.status}).`);
      const blob = await response.blob();
      if (!blob.type.startsWith("image/")) throw new Error("O conteúdo selecionado não parece ser uma imagem.");
      const extension = ({ "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif" })[blob.type] || "jpg";
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `whatsapp-musicas-${new Date().toISOString().replaceAll(":", "-")}.${extension}`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
      message.textContent = "Download iniciado. Depois que terminar, execute /imagem-recente no agente.";
    } catch (error) {
      message.textContent = `${error.message} Você ainda pode baixar a imagem pelo próprio WhatsApp.`;
    } finally {
      save.disabled = false;
    }
  });
  close.addEventListener("click", () => panel.remove());
  actions.append(save, close);
  panel.append(heading, hint, grid, message, actions);
  document.body.append(panel);
})();
