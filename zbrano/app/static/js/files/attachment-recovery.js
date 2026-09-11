(() => {
  const attach = document.getElementById("attach-file");
  const picker = document.getElementById("attachment-input");
  if (!attach || !picker) return;

  window.zbranoAttachRecovery = {
    installed: true,
    attachId: attach.id,
    pickerId: picker.id,
  };

  // Capture phase intentionally owns the picker-open action. The historical
  // upload/change handler remains untouched; this only restores the dead click.
  attach.addEventListener("click", event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    picker.click();
  }, true);
})();
