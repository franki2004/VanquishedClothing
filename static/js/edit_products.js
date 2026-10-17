let selectedRelated = new Map();
let page = 1;
let search = "";

document.addEventListener("DOMContentLoaded", () => {
    initRelated();
    initTagSearch();
    initAddTag();
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

/* ================= ADD NEW TAG ================= */

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