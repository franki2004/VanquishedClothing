let page = 1;
let search = "";
const selected = new Map();

let images = [];

function uid() {
    return crypto.randomUUID();
}

document.addEventListener("DOMContentLoaded", () => {

    initTagSearch();
    initRelatedProducts();
    initImages();
});

/* =========================
   RELATED PRODUCTS
========================= */

function initRelatedProducts() {

    const modal = document.getElementById("related-modal");
    const openBtn = document.getElementById("open-related");
    const closeBtn = document.getElementById("close-related");
    const searchInput = document.getElementById("product-search");
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");

    openBtn?.addEventListener("click", () => {
        page = 1;
        search = "";
        modal.classList.remove("hidden");
        loadProducts();
    });

    closeBtn?.addEventListener("click", () => {
        modal.classList.add("hidden");
    });

    searchInput?.addEventListener("input", (e) => {
        search = e.target.value;
        page = 1;
        loadProducts();
    });

    prevBtn?.addEventListener("click", () => {
        if (page > 1) {
            page--;
            loadProducts();
        }
    });

    nextBtn?.addEventListener("click", () => {
        page++;
        loadProducts();
    });
}

async function loadProducts() {

    const res = await fetch(`/product/search/?page=${page}&q=${encodeURIComponent(search)}`);
    const data = await res.json();

    const container = document.getElementById("product-results");
    if (!container) return;

    container.innerHTML = "";

    data.products.forEach(product => {

        const id = String(product.id);
        const checked = selected.has(id);

        const row = document.createElement("label");
        row.className = "flex items-center gap-3 border p-3 text-sm cursor-pointer";

        row.innerHTML = `
            <input type="checkbox" value="${id}" ${checked ? "checked" : ""}>
            <img src="${product.image || ''}" class="w-20 h-32 object-contain">
            <span class="flex-1">${product.name}</span>
        `;

        const cb = row.querySelector("input");

        cb.addEventListener("change", () => {

            if (cb.checked) {
                selected.set(id, product.name);
            } else {
                selected.delete(id);
            }

            renderSelected();
        });

        container.appendChild(row);
    });

    updatePagination(data);
}

function updatePagination(data) {

    const pageLabel = document.getElementById("page-number");
    const prevBtn = document.getElementById("prev-page");
    const nextBtn = document.getElementById("next-page");

    if (pageLabel) pageLabel.innerText = `${data.page} / ${data.pages}`;

    if (prevBtn) {
        prevBtn.disabled = !data.has_previous;
        prevBtn.classList.toggle("opacity-50", !data.has_previous);
    }

    if (nextBtn) {
        nextBtn.disabled = !data.has_next;
        nextBtn.classList.toggle("opacity-50", !data.has_next);
    }
}

function renderSelected() {

    const container = document.getElementById("selected-products");
    if (!container) return;

    container.innerHTML = "";

    selected.forEach((name, id) => {

        const div = document.createElement("div");
        div.className = "border px-3 py-2 flex justify-between text-sm";

        div.innerHTML = `
            <span>${name}</span>
            <button type="button" class="cursor-pointer">×</button>
            <input type="hidden" name="related_products" value="${id}">
        `;

        div.querySelector("button").addEventListener("click", () => {
            selected.delete(id);
            renderSelected();
        });

        container.appendChild(div);
    });
}

/* =========================
   TAG SEARCH
========================= */

function initTagSearch() {

    document.querySelectorAll('input[placeholder="Search tags..."]')
        .forEach(input => {

            input.addEventListener("input", () => {

                const filter = input.value.toLowerCase();
                const section = input.closest("section");

                if (!section) return;

                section.querySelectorAll("label").forEach(tag => {
                    tag.style.display =
                        tag.textContent.toLowerCase().includes(filter)
                            ? "flex"
                            : "none";
                });
            });
        });
}

/* =========================
   IMAGES (FIXED + WORKING)
========================= */

function initImages() {

    const input = document.querySelector('input[name="images"]');
    const preview = document.getElementById("preview");
    const form = input?.closest("form");

    if (!input || !preview || !form) return;

    new Sortable(preview, {
        animation: 150,
        handle: ".drag-handle"
    });

    input.addEventListener("change", (e) => {

        Array.from(e.target.files).forEach(file => {
            images.push({ id: uid(), file });
        });

        input.value = "";
        renderImages(preview);
    });

    function renderImages() {

        preview.innerHTML = "";

        images.forEach(img => {

            const reader = new FileReader();

            reader.onload = (e) => {

                const box = document.createElement("div");
                box.className = "border p-2 relative bg-white";
                box.setAttribute("data-id", img.id);

                box.innerHTML = `
                  <div class="drag-handle cursor-move text-gray-600 text-md">
                      ⠿
                  </div>

                    <button type="button"
                        class="absolute top-1 right-1 bg-black text-white w-6 h-6 text-xs">
                        ×
                    </button>

                    <img src="${e.target.result}"
                         class="w-full h-48 object-contain">
                `;

                box.querySelector("button").addEventListener("click", () => {
                    images = images.filter(x => x.id !== img.id);
                    renderImages();
                });

                preview.appendChild(box);
            };

            reader.readAsDataURL(img.file);
        });
    }

    form.addEventListener("submit", () => {

        const orderedIds = Array.from(preview.children)
            .map(el => el.getAttribute("data-id"));

        const ordered = orderedIds
            .map(id => images.find(i => i.id === id))
            .filter(Boolean);

        const dt = new DataTransfer();

        ordered.forEach(img => dt.items.add(img.file));

        input.files = dt.files;
    });
}