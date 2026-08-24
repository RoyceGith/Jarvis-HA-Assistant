(() => {
  const form = document.getElementById("plugin-install-form");
  const button = document.getElementById("install-plugin");
  form?.addEventListener("submit", event => {
    event.preventDefault();
    button?.click();
  });
})();
