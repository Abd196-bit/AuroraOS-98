const navToggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");

navToggle?.addEventListener("click", () => {
  const isOpen = nav.classList.toggle("open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

nav?.addEventListener("click", (event) => {
  if (event.target.matches("a")) {
    nav.classList.remove("open");
    navToggle?.setAttribute("aria-expanded", "false");
  }
});

const gallery = document.querySelector("[data-gallery]");
if (gallery) {
  const tabs = [...gallery.querySelectorAll("[role='tab']")];
  const image = gallery.querySelector("[data-gallery-image]");
  const caption = gallery.querySelector("[data-gallery-caption]");

  const selectTab = (tab) => {
    tabs.forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
    image.src = tab.dataset.image;
    image.alt = tab.dataset.alt;
    caption.textContent = tab.dataset.caption;
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      const next = tabs[(index + direction + tabs.length) % tabs.length];
      next.focus();
      selectTab(next);
    });
  });
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const original = button.innerHTML;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(button.dataset.copy);
      } else {
        const temporary = document.createElement("textarea");
        temporary.value = button.dataset.copy;
        temporary.setAttribute("readonly", "");
        temporary.style.position = "fixed";
        temporary.style.opacity = "0";
        document.body.appendChild(temporary);
        temporary.select();
        document.execCommand("copy");
        temporary.remove();
      }
      button.textContent = "Copied";
      button.classList.add("copied");
      window.setTimeout(() => {
        button.innerHTML = original;
        button.classList.remove("copied");
      }, 1800);
    } catch {
      button.textContent = "Select commands above";
      window.setTimeout(() => { button.innerHTML = original; }, 1800);
    }
  });
});

document.querySelector("[data-year]").textContent = new Date().getFullYear();
