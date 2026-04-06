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
});