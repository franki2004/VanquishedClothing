document.addEventListener("DOMContentLoaded", () => {
    const images = window.PRODUCT_IMAGES || [];
    let index = 0;
  
    const imgElement = document.getElementById("product-image");
    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");
  
    if (!imgElement || images.length <= 1) return;
  
    prevBtn?.addEventListener("click", () => {
      index = (index - 1 + images.length) % images.length;
      imgElement.src = images[index];
    });
  
    nextBtn?.addEventListener("click", () => {
      index = (index + 1) % images.length;
      imgElement.src = images[index];
    });
  });