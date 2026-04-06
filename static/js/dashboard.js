document.addEventListener("DOMContentLoaded", function () {
  // EDIT USER FIELDS
  document.querySelectorAll(".field-form").forEach((form) => {
    const input = form.querySelector(".editable");
    const btn = form.querySelector(".toggle-btn");
    let editing = false;

    btn.addEventListener("click", () => {
      if (!editing) {
        editing = true;
        input.disabled = false;
        btn.textContent = "✔";
        input.focus();
      } else {
        form.submit();
      }
    });
  });

  // DETAILS TOGGLE
  document.querySelectorAll(".toggle-details").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById(btn.dataset.target).classList.toggle("hidden");
    });
  });

  // ADDRESS MODAL
  const modal = document.getElementById("addressModal");

  document.getElementById("addAddressTrigger")?.addEventListener("click", () => {
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.getElementById("modalTitle").textContent = "Add Address";
  });

  document.querySelectorAll(".editAddressBtn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      modal.classList.remove("hidden");
      modal.classList.add("flex");

      document.getElementById("modalTitle").textContent = "Edit Address";
      document.getElementById("editAddressId").value = btn.dataset.id;
    });
  });

  document.getElementById("closeModal").onclick = () =>
    modal.classList.add("hidden");

  // DELETE MODAL
  const deleteModal = document.getElementById("deleteModal");

  document.querySelectorAll(".deleteAddressBtn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteModal.classList.remove("hidden");
      deleteModal.classList.add("flex");
      document.getElementById("deleteAddressId").value = btn.dataset.id;
    });
  });

  document.getElementById("cancelDelete").onclick = () =>
    deleteModal.classList.add("hidden");

  // LOGOUT MODAL (FIXED)
  const logoutBtn = document.getElementById("logoutBtn");
  const logoutModal = document.getElementById("logoutModal");
  const cancelLogout = document.getElementById("cancelLogout");

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      logoutModal.classList.remove("hidden");
      logoutModal.classList.add("flex");
    });
  }

  if (cancelLogout) {
    cancelLogout.addEventListener("click", () => {
      logoutModal.classList.add("hidden");
    });
  }
});