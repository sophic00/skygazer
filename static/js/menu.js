document.addEventListener("DOMContentLoaded", () => {
  const header = document.querySelector("header");
  const toggle = document.querySelector(".menu-toggle");
  if (!header || !toggle) return;

  toggle.addEventListener("click", () => {
    header.classList.toggle("menu-open");
    toggle.setAttribute("aria-expanded", header.classList.contains("menu-open"));
  });
});
