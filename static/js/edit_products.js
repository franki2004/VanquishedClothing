let selectedRelated = new Map();
let newImages = [];
let page = 1;
let search = "";

function uid() {
    return crypto.randomUUID();
}

document.addEventListener("DOMContentLoaded", () => {
    initRelated();
    initImages();
    initTagSearch();
    preloadRelated();
});

/* ================= RELATED ================= */

function initRelated() {

    const modal = document.getElementById("related-modal");
    const openBtn = document.getElementById("open-related");
    const closeBtn = document.getElementById("close-related");

    openBtn?.addEventListener("click", () => {
        modal.classList.remove("hidden");
        load();
    });

    closeBtn?.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    document.getElementById("product-search")?.addEventListener("input", e => {
        search = e.target.value;
        page = 1;
        load();
    });

    document.getElementById("prev-page")?.addEventListener("click", () => {
        if (page > 1) {
            page--;
            load();
        }
    });

    document.getElementById("next-page")?.addEventListener("click", () => {
        page++;
        load();
    });
}

async function load() {

  const res = await fetch(`/product/search/?page=${page}&q=${encodeURIComponent(search)}`);
  const data = await res.json();

  const box = document.getElementById("product-results");
  box.innerHTML = "";

  data.products.forEach(p => {

      const id = String(p.id);

      const el = document.createElement("label");
      el.className = "flex items-center gap-3 border p-3 text-sm";

      el.innerHTML = `
          <input type="checkbox" value="${id}" ${selectedRelated.has(id) ? "checked" : ""}>
          <img src="${p.image || ''}" class="w-20 h-28 object-contain border">
          <span class="flex-1">${p.name}</span>
      `;

      const cb = el.querySelector("input");

      cb.onchange = () => {
          if (cb.checked) selectedRelated.set(id, p.name);
          else selectedRelated.delete(id);
          renderRelated();
      };

      box.appendChild(el);
  });

  document.getElementById("page-number").innerText =
      `${data.page} / ${data.pages}`;

  document.getElementById("prev-page").disabled = !data.has_previous;
  document.getElementById("next-page").disabled = !data.has_next;
}

function renderRelated() {

    const box = document.getElementById("selected-products");
    box.innerHTML = "";

    selectedRelated.forEach((name, id) => {

        const el = document.createElement("div");
        el.className = "border px-3 py-2 flex justify-between text-sm";

        el.innerHTML = `
            <span>${name}</span>
            <button type="button">×</button>
            <input type="hidden" name="related_products" value="${id}">
        `;

        el.querySelector("button").onclick = () => {
            selectedRelated.delete(id);
            renderRelated();
        };

        box.appendChild(el);
    });
}

function preloadRelated() {
  const items = window.EDIT_DATA?.related_products || [];

  selectedRelated.clear();

  items.forEach(p => {
      selectedRelated.set(String(p.id), p.name);
  });

  renderRelated();
}

/* ================= TAGS ================= */

function initTagSearch() {
    document.querySelectorAll('input[placeholder="Search tags..."]')
        .forEach(input => {

            input.addEventListener("input", () => {

                const f = input.value.toLowerCase();

                input.closest("section")
                    .querySelectorAll("label")
                    .forEach(l => {
                        l.style.display =
                            l.textContent.toLowerCase().includes(f)
                                ? "flex"
                                : "none";
                    });
            });
        });
}

/* ================= IMAGES (SOURCE OF TRUTH = DOM) ================= */

function initImages() {

  const input = document.querySelector('input[name="images"]');
  const preview = document.getElementById("preview");
  const form = input?.closest("form");

  if (!input || !preview || !form) return;

  let images = [];

  // load existing images into state
  preview.querySelectorAll("[data-id]").forEach(el => {
      images.push({
          id: el.getAttribute("data-id"),
          file: null,
          existing: true
      });
  });

  new Sortable(preview, {
      animation: 150,
      handle: ".drag-handle"
  });

  input.addEventListener("change", (e) => {

      Array.from(e.target.files).forEach(file => {
          images.push({ id: crypto.randomUUID(), file, existing: false });
      });

      input.value = "";
      renderImages();
  });

  function renderImages() {

      preview.innerHTML = "";

      images.forEach(img => {

          const box = document.createElement("div");
          box.className = "border p-2 relative bg-white";
          box.setAttribute("data-id", img.id);
          box.setAttribute("data-existing", img.existing ? "1" : "0");

          box.innerHTML = `
              <div class="drag-handle cursor-move text-gray-600 text-md">
                  ⠿
              </div>

              <button type="button"
                      class="absolute top-1 right-1 bg-black text-white w-6 h-6 text-xs">
                  ×
              </button>

              ${img.file
                  ? `<img src="${URL.createObjectURL(img.file)}" class="w-full h-48 object-contain">`
                  : `<img src="${preview.querySelector('[data-id="'+img.id+'"] img')?.src || ''}" class="w-full h-48 object-contain">`
              }
          `;

          box.querySelector("button").addEventListener("click", () => {
              images = images.filter(x => x.id !== img.id);
              renderImages();
          });

          preview.appendChild(box);
      });
  }

  form.addEventListener("submit", () => {

      const orderedNodes = Array.from(preview.children);

      const ordered = orderedNodes
          .map(node => images.find(i => i.id === node.getAttribute("data-id")))
          .filter(Boolean);

      const dt = new DataTransfer();

      ordered.forEach(img => {
          if (img.file) dt.items.add(img.file);
      });

      input.files = dt.files;

      const existingOrder = ordered
          .filter(i => i.existing)
          .map(i => i.id);

      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "existing_image_order";
      hidden.value = JSON.stringify(existingOrder);

      form.appendChild(hidden);
  });
}