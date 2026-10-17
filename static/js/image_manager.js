(function () {
    document.addEventListener("DOMContentLoaded", () => {
      const input = document.getElementById("image-input");
      const preview = document.getElementById("preview");
      const dropzone = document.getElementById("dropzone");
      const countEl = document.getElementById("image-count");
      const form = input?.closest("form");
  
      if (!input || !preview || !form) return;
  
      // Source of truth. Always kept in the same order as the DOM.
      let items = [];
      const deletedIds = [];
      let counter = 0;
  
      // Existing images (edit page) are rendered by Django as placeholders
      preview.querySelectorAll('[data-existing="1"]').forEach((el) => {
        items.push({
          key: "e" + el.dataset.id,
          id: el.dataset.id,
          existing: true,
          file: null,
          src: el.dataset.src,
        });
      });
  
      const style = document.createElement("style");
      style.textContent = `
        .is-ghost { opacity: .35; }
        .is-chosen { outline: 2px solid #000; outline-offset: -2px; }
      `;
      document.head.appendChild(style);
  
      function render() {
        preview.innerHTML = "";
  
        items.forEach((item) => {
          const card = document.createElement("div");
          card.className =
            "relative bg-gray-100 border border-gray-200 overflow-hidden select-none cursor-grab active:cursor-grabbing";
          card.style.aspectRatio = "3 / 4";
          card.dataset.key = item.key;
  
          card.innerHTML = `
            <img src="${item.src}" alt="" draggable="false"
                 class="absolute inset-0 w-full h-full object-contain pointer-events-none">
            <span class="badge absolute top-2 left-2 bg-black text-white text-xs px-2 py-1"></span>
            <button type="button" aria-label="Remove image"
                    class="remove-btn absolute top-2 right-2 w-8 h-8 flex items-center justify-center bg-white/90 border text-lg leading-none hover:bg-black hover:text-white cursor-pointer">
              ×
            </button>
          `;
  
          preview.appendChild(card);
        });
  
        updateBadges();
      }
  
      function updateBadges() {
        Array.from(preview.children).forEach((card, i) => {
          card.querySelector(".badge").textContent = i === 0 ? "Main" : String(i + 1);
        });
  
        if (countEl) {
          countEl.textContent = items.length
            ? `${items.length} image${items.length > 1 ? "s" : ""}`
            : "";
        }
      }
  
      // After a drag, reorder the array to match the DOM (no re-render needed)
      function syncFromDom() {
        const order = Array.from(preview.children).map((c) => c.dataset.key);
        items.sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
        updateBadges();
      }
  
      function addFiles(fileList) {
        Array.from(fileList)
          .filter((f) => f.type.startsWith("image/"))
          .forEach((file) => {
            items.push({
              key: "n" + counter++,
              existing: false,
              file,
              src: URL.createObjectURL(file),
            });
          });
        render();
      }
  
      // Reordering: no animation, whole card is the handle
      new Sortable(preview, {
        animation: 0,
        filter: ".remove-btn",
        preventOnFilter: false,
        delay: 120,
        delayOnTouchOnly: true,
        ghostClass: "is-ghost",
        chosenClass: "is-chosen",
        onEnd: syncFromDom,
      });
  
      // Remove
      preview.addEventListener("click", (e) => {
        const btn = e.target.closest(".remove-btn");
        if (!btn) return;
  
        const key = btn.closest("[data-key]").dataset.key;
        const item = items.find((i) => i.key === key);
        if (!item) return;
  
        if (item.existing) deletedIds.push(item.id);
        else URL.revokeObjectURL(item.src);
  
        items = items.filter((i) => i !== item);
        render();
      });
  
      // Pick files
      input.addEventListener("change", () => {
        addFiles(input.files);
        input.value = "";
      });
  
      // Drop files on the drop zone
      ["dragenter", "dragover"].forEach((evt) =>
        dropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          dropzone.classList.add("border-black", "bg-gray-50");
        })
      );
      ["dragleave", "drop"].forEach((evt) =>
        dropzone.addEventListener(evt, (e) => {
          e.preventDefault();
          dropzone.classList.remove("border-black", "bg-gray-50");
        })
      );
      dropzone.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
  
      function setHidden(name, value) {
        let el = form.querySelector(`input[type="hidden"][name="${name}"]`);
        if (!el) {
          el = document.createElement("input");
          el.type = "hidden";
          el.name = name;
          form.appendChild(el);
        }
        el.value = value;
      }
  
      form.addEventListener("submit", () => {
        // New files, in the order they appear on screen
        const dt = new DataTransfer();
        items.filter((i) => !i.existing).forEach((i) => dt.items.add(i.file));
        input.files = dt.files;
  
        // Final order of everything (existing + new), used by the edit view
        let fileIndex = 0;
        const layout = items.map((i) =>
          i.existing
            ? { type: "existing", id: Number(i.id) }
            : { type: "new", index: fileIndex++ }
        );
  
        setHidden("image_layout", JSON.stringify(layout));
        setHidden("images_to_delete", deletedIds.join(","));
      });
  
      render();
    });
  })();