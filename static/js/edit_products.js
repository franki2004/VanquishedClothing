let imagesToDelete = [];
let selectedFiles = []; // Tracks new files only

function filterTags(input) {
  const filter = input.value.toLowerCase();
  const container = document.getElementById("tags-container");
  container.querySelectorAll(".tag-item").forEach(tag => {
    tag.style.display = tag.innerText.toLowerCase().includes(filter) ? "flex" : "none";
  });
}

// Remove existing image
function removeExistingImage(btn) {
  const container = btn.closest("[data-image-id]");
  const imageId = container.dataset.imageId;
  imagesToDelete.push(imageId);
  document.getElementById("images_to_delete").value = imagesToDelete.join(",");
  container.remove();
}

// Preview new uploaded images
function previewImages(input) {
  const previewContainer = document.getElementById("preview");
  selectedFiles = selectedFiles.concat(Array.from(input.files));
  input.value = ""; // clear input so user can select more files later

  rebuildPreview();
}

// Rebuild preview for new images
function rebuildPreview() {
  const previewContainer = document.getElementById("preview");
  
  // Keep existing images in DOM (they already have data-image-id)
  const existingImages = Array.from(previewContainer.querySelectorAll("[data-image-id]"));

  // Remove old new previews
  previewContainer.querySelectorAll(".new-image-preview").forEach(el => el.remove());

  selectedFiles.forEach((file, i) => {
    const reader = new FileReader();
    reader.onload = e => {
      const div = document.createElement("div");
      div.className = "flex flex-col items-center w-32 relative new-image-preview";

      const btn = document.createElement("button");
      btn.type = "button";
      btn.innerText = "×";
      btn.className = "absolute top-[-4px] right-[-4px] flex items-center justify-center bg-black hover:bg-red-600 text-white  w-4 h-4 text-sm cursor-pointer";
      btn.onclick = () => {
        selectedFiles.splice(i, 1);
        rebuildPreview();
      };

      const img = document.createElement("img");
      img.src = e.target.result;
      img.className = "w-full h-32 object-cover border ";

      const orderInput = document.createElement("input");
      orderInput.type = "number";
      orderInput.name = `new_image_order_${i}`;
      orderInput.value = i;
      orderInput.className = "mt-1 w-full border p-1 text-center text-sm";

      div.appendChild(btn);
      div.appendChild(img);
      div.appendChild(orderInput);

      previewContainer.appendChild(div);
    };
    reader.readAsDataURL(file);
  });

  rebuildInputFiles();
}

// Update hidden input.files for submission
function rebuildInputFiles() {
  const input = document.querySelector('input[name="images"]');
  if (!input) return;
  const dt = new DataTransfer();
  selectedFiles.forEach(f => dt.items.add(f));
  input.files = dt.files;
}