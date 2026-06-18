(function () {
    const toggleBtn = document.getElementById("toggle-password");
    if (!toggleBtn) return;
  
    const wrapper = document.getElementById("password-wrapper");
    const passwordInput = wrapper.querySelector("input");
    const eyeOpenIcon = document.getElementById("eye-open");
    const eyeClosedIcon = document.getElementById("eye-closed");
  
    toggleBtn.addEventListener("click", () => {
      const isVisible = passwordInput.type === "text";
  
      passwordInput.type = isVisible ? "password" : "text";
  
      eyeOpenIcon.classList.toggle("hidden", isVisible);
      eyeClosedIcon.classList.toggle("hidden", !isVisible);
  
      toggleBtn.setAttribute("aria-pressed", String(!isVisible));
      toggleBtn.setAttribute(
        "aria-label",
        isVisible ? "Show password" : "Hide password"
      );
    });
  })();