document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("checkoutForm");
  const addressModal = document.getElementById("addressModal");
  const deleteModal = document.getElementById("deleteModal");

  function openModal(m) { m.classList.remove("hidden"); m.classList.add("flex"); }
  function hideModal(m) { m.classList.add("hidden"); m.classList.remove("flex"); }
  function closeModal() { hideModal(addressModal); }
  function closeDeleteModal() { hideModal(deleteModal); }

  /* ---------- ADDRESS MODALS ---------- */
  document.getElementById("openAddressModal")?.addEventListener("click", () => {
    ["addressIdInput", "modalAddress", "modalCountry", "modalCity", "modalPostal"]
      .forEach((id) => (document.getElementById(id).value = ""));
    openModal(addressModal);
  });

  document.querySelectorAll(".editAddressBtn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById("addressIdInput").value = btn.dataset.id;
      document.getElementById("modalAddress").value = btn.dataset.address;
      document.getElementById("modalCountry").value = btn.dataset.country;
      document.getElementById("modalCity").value = btn.dataset.city;
      document.getElementById("modalPostal").value = btn.dataset.postal;
      openModal(addressModal);
    });
  });

  document.querySelectorAll(".deleteAddressBtn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById("deleteAddressId").value = btn.dataset.id;
      openModal(deleteModal);
    });
  });

  // close on backdrop click / Escape
  [addressModal, deleteModal].forEach((m) =>
    m.addEventListener("click", (e) => { if (e.target === m) hideModal(m); })
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeModal(); closeDeleteModal(); }
  });

  /* ---------- ADDRESS SELECTION ---------- */
  const boxes = document.querySelectorAll(".address-box");
  const selectedAddressInput = document.getElementById("selectedAddressInput");
  const addressError = document.getElementById("addressError");

  boxes.forEach((box) => {
    box.addEventListener("click", () => {
      boxes.forEach((b) => b.classList.remove("ring-2", "ring-black"));
      box.classList.add("ring-2", "ring-black");
      selectedAddressInput.value = box.dataset.id;
      addressError?.classList.add("hidden");
    });
  });

  /* ---------- PAYMENT + TOTALS ---------- */
  const radios = document.querySelectorAll('input[name="payment_method"]');
  const codRow = document.getElementById("codRow");
  const submitLabel = document.getElementById("submitLabel");
  const submitTotal = document.getElementById("submitTotal");
  const submitBtn = document.getElementById("submitBtn");

  function updatePayment() {
    const val = document.querySelector('input[name="payment_method"]:checked').value;
    const subtotal = parseFloat(window.CHECKOUT_DATA.subtotal);
    const delivery = parseFloat(window.CHECKOUT_DATA.delivery);
    const codFee = val === "cod" ? Math.round(subtotal * 3) / 100 : 0;
    const total = "€" + (subtotal + delivery + codFee).toFixed(2);

    codRow.classList.toggle("hidden", val !== "cod");
    document.getElementById("codFee").textContent = "€" + codFee.toFixed(2);
    document.getElementById("totalValue").textContent = total;

    submitLabel.textContent = val === "cod" ? "Place order" : "Pay now";
    submitTotal.textContent = " · " + total;
    submitTotal.classList.remove("hidden");
  }

  radios.forEach((r) => r.addEventListener("change", updatePayment));
  updatePayment();

  /* ---------- SUBMIT ---------- */
  form.addEventListener("submit", (e) => {
    if (form.dataset.auth === "true" && !selectedAddressInput.value) {
      e.preventDefault();
      addressError?.classList.remove("hidden");
      document.getElementById("addressSection").scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    submitBtn.disabled = true;
    submitLabel.textContent = "Processing…";
    submitTotal.classList.add("hidden");
  });

  window.addEventListener("pageshow", () => {
    submitBtn.disabled = false;
    updatePayment();
  });

  window.closeModal = closeModal;
  window.closeDeleteModal = closeDeleteModal;
});