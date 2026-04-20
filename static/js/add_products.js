(function () {
  if (window.__bulkProductsInitialized) return;
  window.__bulkProductsInitialized = true;

  let rowIndex = 1;

  const sizes = window.APP_DATA.sizes;
  const tags = window.APP_DATA.tags;
  const categoriesOptions = window.APP_DATA.categoriesOptions;

  const selectedFiles = {};

  window.removeRow = function (btn) {
    const row = btn.closest(".product-row");
    const idx = Array.from(document.querySelectorAll(".product-row")).indexOf(row);
    delete selectedFiles[idx];
    row.remove();
  };

  window.previewImages = function (input, idx) {
    const preview = document.getElementById(`preview-${idx}`);
    preview.innerHTML = "";
    selectedFiles[idx] = selectedFiles[idx] || [];

    Array.from(input.files).forEach(f => selectedFiles[idx].push(f));
    input.value = "";

    selectedFiles[idx].forEach((file, i) => {
      const reader = new FileReader();

      reader.onload = e => {
        const div = document.createElement("div");
        div.className = "flex flex-col items-center w-32 relative";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.innerText = "×";
        btn.className =
          "absolute top-[-4px] right-[-4px] flex items-center justify-center bg-black hover:bg-red-600 text-white w-4 h-4 text-sm cursor-pointer";

        btn.onclick = () => {
          selectedFiles[idx].splice(i, 1);
          div.remove();
          rebuildInputFiles(idx);
        };

        const img = document.createElement("img");
        img.src = e.target.result;
        img.className = "w-full h-32 object-cover border";

        const order = document.createElement("input");
        order.type = "number";
        order.name = `image_order_${idx}[]`;
        order.value = i;
        order.className = "mt-1 w-full border p-1 text-center text-sm";

        div.appendChild(btn);
        div.appendChild(img);
        div.appendChild(order);

        preview.appendChild(div);
      };

      reader.readAsDataURL(file);
    });

    rebuildInputFiles(idx);
  };

  function rebuildInputFiles(idx) {
    const input = document.querySelector(`input[name="images_${idx}"]`);
    if (!input) return;

    const dt = new DataTransfer();
    selectedFiles[idx].forEach(f => dt.items.add(f));
    input.files = dt.files;
  }

  window.addRow = function () {
    const productsDiv = document.getElementById("products");

    const div = document.createElement("div");
    div.className =
      "product-row relative grid grid-cols-1 lg:grid-cols-3 gap-6 p-4 border";

    div.innerHTML = `
      <button type="button" onclick="removeRow(this)"
        class="absolute top-2 right-4 text-gray-500 hover:text-red-600 text-xl font-bold cursor-pointer">×</button>

      <div class="space-y-4">
        <label class="block font-semibold">Category</label>
        <select name="category_${rowIndex}" class="border px-4 py-3 w-full cursor-pointer">
          <option value="">—</option>${categoriesOptions}
        </select>

        <label class="block font-semibold">Product Name</label>
        <input name="name" placeholder="Product Name"
          class="border p-3 w-full" required />

        <label class="block font-semibold">Price</label>
        <input name="price" type="number" step="0.01"
          placeholder="Price"
          class="border p-3 w-full" required />

        <label class="block font-semibold">Discount %</label>
        <input name="discount_percent" type="number" min="0" max="100"
          placeholder="Discount %"
          class="border p-3 w-full" />

        <div class="grid grid-cols-3 grid-rows-2 gap-4 mt-2">
          ${sizes
            .map(
              s => `
            <div class="flex flex-col items-center">
              <label class="text-sm font-semibold">${s}</label>
              <input name="stock_${s}_${rowIndex}" type="number" min="0"
                placeholder="Stock"
                class="border p-2 w-18 text-center" />
            </div>
          `
            )
            .join("")}
        </div>
      </div>

      <div>
        <label class="block font-semibold mb-2">Tags</label>

        <input
          type="text"
          placeholder="Search tags..."
          class="border px-3 py-2 w-full mb-2"
          onkeyup="filterTags(this, ${rowIndex})"
        />

        <div id="tags-container-${rowIndex}"
          class="flex flex-col gap-2 max-h-[400px] overflow-y-auto">

          ${tags
            .map(
              t => `
            <label class="flex items-center gap-2 cursor-pointer border px-3 py-1 hover:bg-gray-100 tag-item">
              <input type="checkbox" name="tags_${rowIndex}" value="${t.id}">
              <span>${t.name}</span>
            </label>
          `
            )
            .join("")}

        </div>
      </div>

      <div>
        <label class="block font-semibold mb-2">Images</label>

        <input type="file" name="images_${rowIndex}" multiple
          class="border p-2 w-full cursor-pointer"
          onchange="previewImages(this, ${rowIndex})" />

        <div id="preview-${rowIndex}" class="flex gap-4 flex-wrap mt-4"></div>
      </div>
    `;

    productsDiv.appendChild(div);
    rowIndex++;
  };

  window.filterTags = function (input, idx) {
    const filter = input.value.toLowerCase();
    const container = document.getElementById(`tags-container-${idx}`);

    container.querySelectorAll(".tag-item").forEach(tag => {
      tag.style.display = tag.innerText.toLowerCase().includes(filter)
        ? "flex"
        : "none";
    });
  };
})();