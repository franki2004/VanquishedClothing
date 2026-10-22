document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.getElementById("toggle-password");
  const wrapper = document.getElementById("password-wrapper");

  if (!toggleBtn || !wrapper) return;

  const passwordInput = wrapper.querySelector("input");
  const eyeOpenIcon = document.getElementById("eye-open");
  const eyeClosedIcon = document.getElementById("eye-closed");

  if (!passwordInput || !eyeOpenIcon || !eyeClosedIcon) return;

  toggleBtn.addEventListener("click", function () {
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
});