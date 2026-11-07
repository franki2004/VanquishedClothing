document.addEventListener("DOMContentLoaded", () => {
  const denyModal = document.getElementById("denyModal");
  const denyOrderIdInput = document.getElementById("denyOrderId");
  const closeBtn = document.getElementById("closeDeny");

  document.querySelectorAll(".openDenyModal").forEach(btn => {
    btn.addEventListener("click", () => {
      denyModal.classList.remove("hidden");
      denyModal.classList.add("flex");
      denyOrderIdInput.value = btn.dataset.id;
    });
  });

  closeBtn.addEventListener("click", () => {
    denyModal.classList.add("hidden");
    denyModal.classList.remove("flex");
  });
  const rejectModal = document.getElementById("rejectReturnModal");

  document.querySelectorAll(".openRejectModal").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("rejectOrderId").value = btn.dataset.orderId;
      document.getElementById("rejectItemId").value = btn.dataset.itemId;
      rejectModal.classList.remove("hidden");
      rejectModal.classList.add("flex");
    });
  });

  document.getElementById("closeRejectReturn")?.addEventListener("click", () => {
    rejectModal.classList.add("hidden");
    rejectModal.classList.remove("flex");
  });
});