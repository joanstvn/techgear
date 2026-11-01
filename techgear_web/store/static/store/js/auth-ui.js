(function () {
  "use strict";

  document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
    button.addEventListener("click", function () {
      var wrapper = button.closest(".auth__input-wrap");
      var input = wrapper && wrapper.querySelector("input");
      if (!input) return;
      var visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
      var icon = button.querySelector("use");
      if (icon) icon.setAttribute("href", icon.getAttribute("href").replace(/#.*$/, visible ? "#visibility_off" : "#visibility"));
    });
  });

  document.querySelectorAll("[data-demo-recovery]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var card = form.closest(".auth__card");
      var state = card && card.querySelector("[data-demo-recovery-form-state]");
      var success = card && card.querySelector("[data-demo-recovery-success]");
      var email = form.querySelector('input[type="email"]');
      var emailTarget = success && success.querySelector("[data-demo-recovery-email]");
      if (emailTarget && email) emailTarget.textContent = email.value;
      if (state && success) {
        state.hidden = true;
        success.hidden = false;
      }
    });
  });

  document.querySelectorAll("[data-google-unavailable]").forEach(function (button) {
    button.addEventListener("click", function () {
      var notice = document.querySelector("[data-google-auth-message]");
      if (notice) notice.hidden = false;
    });
  });
})();
