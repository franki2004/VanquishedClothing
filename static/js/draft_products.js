document.getElementById("select-all").addEventListener("change", function () {
    document
      .querySelectorAll('input[name="selected_products"]')
      .forEach((cb) => (cb.checked = this.checked));
  });