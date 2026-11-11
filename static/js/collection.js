document.addEventListener("DOMContentLoaded", () => {
    const imgs = document.querySelectorAll(".product-img");
    console.log("[collection.js] product images found:", imgs.length);
  
    const RATIO = 3 / 4;
    const W = 90;
    const H = 120;
  
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
  
    function buildBackdrop(img) {
      const nw = img.naturalWidth;
      const nh = img.naturalHeight;
      const a = nw / nh;
  
      let dw, dh;
      if (a < RATIO) { dh = H; dw = H * a; }  
      else           { dw = W; dh = W / a; }   
  
      const dx = (W - dw) / 2;
      const dy = (H - dh) / 2;
  
      ctx.clearRect(0, 0, W, H);
  
      if (dx >= 1) {
        ctx.drawImage(img, 0, 0, 2, nh, 0, 0, dx + 1, H);                
        ctx.drawImage(img, nw - 2, 0, 2, nh, W - dx - 1, 0, dx + 1, H);  
      }
      if (dy >= 1) {
        ctx.drawImage(img, 0, 0, nw, 2, 0, 0, W, dy + 1);               
        ctx.drawImage(img, 0, nh - 2, nw, 2, 0, H - dy - 1, W, dy + 1);  
      }
  
      return canvas.toDataURL("image/png");
    }
  
    function apply(img) {
      try {
        img.style.backgroundImage = `url(${buildBackdrop(img)})`;
        img.style.backgroundSize = "100% 100%";
        img.style.backgroundRepeat = "no-repeat";
      } catch (e) {
        console.warn("[collection.js] cannot read pixels (" + e.name + "):", img.src);
      }
    }
  
    imgs.forEach((img) => {
      img.addEventListener("error", () => {
        if (img.hasAttribute("crossorigin")) {
          img.removeAttribute("crossorigin");
          img.src = img.src;
        }
      }, { once: true });
  
      if (img.complete && img.naturalWidth) apply(img);
      else img.addEventListener("load", () => apply(img), { once: true });
    });
  });