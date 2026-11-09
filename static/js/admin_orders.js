document.addEventListener("DOMContentLoaded", () => {
  function setupModal(modal) {
    return {
      open() { modal.classList.remove("hidden"); modal.classList.add("flex"); },
      close() { modal.classList.add("hidden"); modal.classList.remove("flex"); },
    };
  }

  // DECLINE ORDER
  const denyEl = document.getElementById("denyModal");
  if (denyEl) {
    const deny = setupModal(denyEl);
    document.getElementById("openDeny")?.addEventListener("click", deny.open);
    document.getElementById("closeDeny")?.addEventListener("click", deny.close);
  }

  // REJECT RETURN
  const rejectEl = document.getElementById("rejectReturnModal");
  if (rejectEl) {
    const reject = setupModal(rejectEl);
    document.querySelectorAll(".openRejectModal").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("rejectItemId").value = btn.dataset.itemId;
        reject.open();
      });
    });
    document.getElementById("closeRejectReturn")?.addEventListener("click", reject.close);
  }
});