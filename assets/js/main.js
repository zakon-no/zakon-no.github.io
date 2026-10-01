(function () {
  "use strict";

  var burger = document.getElementById("burger");
  var nav = document.getElementById("nav");

  if (burger && nav) {
    burger.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("is-open");
      burger.classList.toggle("is-open", isOpen);
      burger.setAttribute("aria-expanded", String(isOpen));
      burger.setAttribute("aria-label", isOpen ? "Закрыть меню" : "Открыть меню");
    });

    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        nav.classList.remove("is-open");
        burger.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
        burger.setAttribute("aria-label", "Открыть меню");
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        burger.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
        burger.setAttribute("aria-label", "Открыть меню");
        burger.focus();
      }
    });
  }

  var links = Array.prototype.slice.call(
    document.querySelectorAll(".nav__link[href^='#']")
  );
  var sections = links
    .map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          links.forEach(function (link) {
            link.classList.toggle(
              "is-active",
              link.getAttribute("href") === "#" + entry.target.id
            );
          });
        });
      },
      { rootMargin: "-40% 0px -55% 0px", threshold: 0 }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  }

  /* Частые вопросы — аккордеон.
     Текст лежит в Markdown обычным списком `.faq`; здесь каждый пункт
     превращается в <details>, чтобы работали клавиатура и скринридеры.
     Если скрипт не выполнится, останется обычный список — вид нормальный. */
  var faqLists = Array.prototype.slice.call(document.querySelectorAll(".faq"));

  faqLists.forEach(function (list) {
    var items = Array.prototype.slice.call(list.children);

    items.forEach(function (item) {
      var blocks = Array.prototype.slice.call(item.children);
      if (blocks.length < 2) return;

      var details = document.createElement("details");
      var summary = document.createElement("summary");
      summary.textContent = blocks[0].textContent.trim();

      var body = document.createElement("div");
      body.className = "faq__answer";
      blocks.slice(1).forEach(function (block) {
        body.appendChild(block);
      });

      details.appendChild(summary);
      details.appendChild(body);
      item.textContent = "";
      item.appendChild(details);

      details.addEventListener("toggle", function () {
        if (!details.open) return;
        items.forEach(function (other) {
          var otherDetails = other.querySelector("details");
          if (otherDetails && otherDetails !== details) {
            otherDetails.open = false;
          }
        });
      });
    });
  });

  var year = document.getElementById("year");
  if (year) {
    year.textContent = String(new Date().getFullYear());
  }
})();
