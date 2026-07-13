(() => {
  "use strict";

  const errorSummary = document.querySelector("[data-form-error-summary]");
  if (errorSummary) {
    errorSummary.focus({ preventScroll: true });
    errorSummary.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  document.querySelectorAll("[data-secure-form]").forEach((form) => {
    const submitButton = form.querySelector("[data-submit-button]");
    if (!submitButton) {
      return;
    }

    form.addEventListener("submit", () => {
      if (!form.checkValidity()) {
        return;
      }
      submitButton.setAttribute("aria-busy", "true");
      submitButton.disabled = true;
      submitButton.textContent = submitButton.dataset.pendingLabel || "처리 중…";
    });
  });
})();
