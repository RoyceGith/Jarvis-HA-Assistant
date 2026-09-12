(() => {
  const toggle = document.getElementById("composer-preferences-toggle");
  const popover = document.getElementById("composer-preferences-popover");
  const close = document.getElementById("composer-preferences-close");
  const model = document.getElementById("agent-model");
  const provider = document.getElementById("speech-provider");
  const voice = document.getElementById("voice-select");
  const summary = document.getElementById("composer-preferences-summary");
  if (!toggle || !popover) return;

  const optionText = select => select?.selectedOptions?.[0]?.textContent?.trim() || "";
  const updateSummary = () => {
    const modelName = optionText(model);
    const voiceName = optionText(voice) || optionText(provider);
    summary.textContent = [modelName, voiceName].filter(Boolean).join(" · ");
  };
  const setOpen = open => {
    popover.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) popover.querySelector("select, input, button")?.focus();
  };

  toggle.addEventListener("click", event => {
    event.stopPropagation();
    setOpen(popover.hidden);
  });
  close?.addEventListener("click", () => { setOpen(false); toggle.focus(); });
  popover.addEventListener("click", event => event.stopPropagation());
  document.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape" || popover.hidden) return;
    setOpen(false);
    toggle.focus();
  });
  for (const control of [model, provider, voice]) control?.addEventListener("change", updateSummary);
  window.addEventListener("zbrano-agent-controls-loaded", updateSummary);
  updateSummary();
  setTimeout(updateSummary, 0);
})();
