const denyModal = document.getElementById("denyModal");

document.querySelectorAll(".openDenyModal").forEach(btn => {
  btn.addEventListener("click", () => {
    denyModal.classList.remove("hidden");
    denyModal.classList.add("flex");
    document.getElementById("denyOrderId").value = btn.dataset.id;
  });
});

document.getElementById("closeDeny").onclick = () => {
  denyModal.classList.add("hidden");
  denyModal.classList.remove("flex");
};