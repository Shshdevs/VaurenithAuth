(() => {
  const storageKey = "vaurenith.register.scrollY";
  const restoreRegistrationScroll = () => {
    const form = document.querySelector("#kc-register-form");

    try {
      if (!form) {
        sessionStorage.removeItem(storageKey);
        return;
      }

      const savedScrollY = sessionStorage.getItem(storageKey);
      if (savedScrollY !== null) {
        sessionStorage.removeItem(storageKey);
        window.requestAnimationFrame(() => {
          window.scrollTo(0, Number(savedScrollY));
        });
      }

      form.addEventListener("submit", () => {
        sessionStorage.setItem(storageKey, String(window.scrollY));
      });
    } catch {
      return;
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", restoreRegistrationScroll, { once: true });
  } else {
    restoreRegistrationScroll();
  }
})();
