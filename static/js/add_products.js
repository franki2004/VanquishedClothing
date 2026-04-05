let rowIndex = 1;
const sizes = window.APP_DATA.sizes;
const tags = window.APP_DATA.tags;
const categoriesOptions = window.APP_DATA.categoriesOptions;

const selectedFiles = {};

window.removeRow = function(btn) {
  const row = btn.closest(".product-row");
  const idx = Array.from(document.querySelectorAll(".product-row")).indexOf(row);
  delete selectedFiles[idx];
  row.remove();
};

window.previewImages = function(input, idx) {
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
      btn.className = "absolute top-[-4px] right-[-4px] bg-black text-white w-4 h-4";

      btn.onclick = () => {
        selectedFiles[idx].splice(i, 1);
        div.remove();
        rebuildInputFiles(idx);
      };

      const img = document.createElement("img");
      img.src = e.target.result;
      img.className = "w-full h-32 object-cover";

      const order = document.createElement("input");
      order.type = "number";
      order.name = `image_order_${idx}[]`;
      order.value = i;

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

window.addRow = function() {
  const productsDiv = document.getElementById("products");
  const div = document.createElement("div");
  div.className = "product-row grid grid-cols-1 lg:grid-cols-3 gap-6 p-4 border";

  div.innerHTML = `
    <button type="button" onclick="removeRow(this)">×</button>

    <div>
      <select name="category_${rowIndex}">
        <option value="">—</option>${categoriesOptions}
      </select>

      <input name="name" placeholder="Product Name" required />
      <input name="price" type="number" step="0.01" required />

      <div>
        ${sizes.map(s => `
          <input name="stock_${s}_${rowIndex}" placeholder="${s}">
        `).join('')}
      </div>
    </div>

    <div>
      ${tags.map(t => `
        <label>
          <input type="checkbox" name="tags_${rowIndex}" value="${t.id}">
          ${t.name}
        </label>
      `).join('')}
    </div>

    <div>
      <input type="file" name="images_${rowIndex}" multiple onchange="previewImages(this, ${rowIndex})">
      <div id="preview-${rowIndex}"></div>
    </div>
  `;

  productsDiv.appendChild(div);
  rowIndex++;
};

window.filterTags = function(input, idx) {
  const filter = input.value.toLowerCase();
  const container = document.getElementById(`tags-container-${idx}`);
  container.querySelectorAll(".tag-item").forEach(tag => {
    tag.style.display = tag.innerText.toLowerCase().includes(filter) ? "flex" : "none";
  });
};