document.addEventListener("DOMContentLoaded", () => {
    const addressModal = document.getElementById("addressModal");
    const deleteModal = document.getElementById("deleteModal");
  
    document.getElementById("openAddressModal")?.addEventListener("click", () => {
      document.getElementById("addressIdInput").value = "";
      document.getElementById("modalAddress").value = "";
      document.getElementById("modalCountry").value = "";
      document.getElementById("modalCity").value = "";
      document.getElementById("modalPostal").value = "";
      addressModal.classList.remove("hidden");
    });
  
    function closeModal() { addressModal.classList.add("hidden"); }
    function closeDeleteModal() { deleteModal.classList.add("hidden"); }
  
    document.querySelectorAll(".editAddressBtn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("addressIdInput").value = btn.dataset.id;
        document.getElementById("modalAddress").value = btn.dataset.address;
        document.getElementById("modalCountry").value = btn.dataset.country;
        document.getElementById("modalCity").value = btn.dataset.city;
        document.getElementById("modalPostal").value = btn.dataset.postal;
        addressModal.classList.remove("hidden");
      });
    });
  
    document.querySelectorAll(".deleteAddressBtn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        document.getElementById("deleteAddressId").value = btn.dataset.id;
        deleteModal.classList.remove("hidden");
      });
    });
  
    const boxes = document.querySelectorAll(".address-box");
    const selectedAddressInput = document.getElementById("selectedAddressInput");
  
    boxes.forEach((box) => {
      box.addEventListener("click", () => {
        boxes.forEach(b => b.classList.remove("ring-2", "ring-black"));
        box.classList.add("ring-2", "ring-black");
        selectedAddressInput.value = box.dataset.id;
      });
    });
  
    const paymentOptions = document.querySelectorAll(".payment-option");
    const paymentMethodInput = document.getElementById("paymentMethodInput");
  
    function updatePaymentUI(selected) {
      paymentOptions.forEach(o => {
        o.classList.remove("ring-2", "ring-black");
        o.querySelector(".dot").classList.add("hidden");
      });
  
      selected.classList.add("ring-2", "ring-black");
      selected.querySelector(".dot").classList.remove("hidden");
  
      const val = selected.querySelector("input").value;
      paymentMethodInput.value = val;
  
      const subtotal = parseFloat(window.CHECKOUT_DATA.subtotal);
      const delivery = parseFloat(window.CHECKOUT_DATA.delivery);
      let codFee = val === "cod" ? subtotal * 0.03 : 0;
  
      document.getElementById("codFee").textContent = "€" + codFee.toFixed(2);
      document.getElementById("totalValue").textContent = "€" + (subtotal + delivery + codFee).toFixed(2);
    }
  
    paymentOptions.forEach(option => {
      option.addEventListener("click", () => {
        option.querySelector("input").checked = true;
        updatePaymentUI(option);
      });
    });
  
    updatePaymentUI(document.querySelector(".payment-option"));
  
    // Expose close functions globally (for onclick in HTML buttons)
    window.closeModal = closeModal;
    window.closeDeleteModal = closeDeleteModal;
  });