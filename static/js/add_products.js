let page = 1;
let search = "";
const selected = new Map();


document.addEventListener("DOMContentLoaded", () => {

    initTagSearch();
    initAddTag();
    initRelatedProducts();
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
   ADD NEW TAG
========================= */

function initAddTag() {

    const input = document.getElementById("new-tag-name");
    const btn = document.getElementById("add-tag-btn");
    const list = document.getElementById("tag-list");
    const errorEl = document.getElementById("tag-error");

    if (!input || !btn || !list) return;

    const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

    function showError(msg) {
        errorEl.textContent = msg;
        errorEl.classList.toggle("hidden", !msg);
    }

    async function addTag() {
        const name = input.value.trim();
        if (!name) return;

        showError("");
        btn.disabled = true;

        try {
            const res = await fetch(btn.dataset.url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({ name }),
            });

            const data = await res.json();

            if (!res.ok) {
                showError(data.error || "Could not add tag.");
                return;
            }

            // already in the list (e.g. existing tag typed again) -> just check it
            let cb = list.querySelector(`input[name="tags"][value="${data.id}"]`);

            if (!cb) {
                const label = document.createElement("label");
                label.className = "flex items-center gap-2 text-sm";

                cb = document.createElement("input");
                cb.type = "checkbox";
                cb.name = "tags";
                cb.value = data.id;

                label.appendChild(cb);
                label.appendChild(document.createTextNode(" " + data.name));
                list.prepend(label);
            }

            cb.checked = true;
            cb.closest("label").style.display = "flex";
            cb.scrollIntoView({ block: "nearest" });

            input.value = "";
        } catch (e) {
            showError("Something went wrong. Try again.");
        } finally {
            btn.disabled = false;
        }
    }

    btn.addEventListener("click", addTag);

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            addTag();
        }
    });
}