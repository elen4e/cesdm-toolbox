/* Collapsible nested sections in the right-hand table of contents (Material theme). */
(function () {
  var enhanced = false;

  function enhanceTocItem(item, idPrefix, index) {
    if (item.classList.contains("toc-collapsible")) {
      return index;
    }

    var nestedNav = item.querySelector(":scope > nav.md-nav");
    if (!nestedNav) {
      return index;
    }

    item.classList.add("md-nav__item--nested", "toc-collapsible");

    var toggleId = idPrefix + "-" + index;
    index += 1;

    var toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.className = "md-nav__toggle md-toggle toc-collapse-toggle";
    toggle.id = toggleId;
    toggle.checked = false;

    var link = item.querySelector(":scope > a.md-nav__link");
    if (!link) {
      return index;
    }

    var chevron = document.createElement("label");
    chevron.className = "md-nav__link toc-collapse-chevron";
    chevron.setAttribute("for", toggleId);
    chevron.setAttribute("aria-label", "Expand section");
    chevron.innerHTML = '<span class="md-nav__icon md-icon"></span>';

    link.before(toggle);
    link.after(chevron);

    nestedNav.querySelectorAll(":scope > .md-nav__list > .md-nav__item").forEach(function (child) {
      index = enhanceTocItem(child, idPrefix, index);
    });

    return index;
  }

  function expandActivePath() {
    document.querySelectorAll('a.md-nav__link--active').forEach(function (active) {
      var el = active.closest(".md-nav__item");
      while (el) {
        var toggle = el.querySelector(":scope > .toc-collapse-toggle");
        if (toggle) {
          toggle.checked = true;
        }
        el = el.parentElement ? el.parentElement.closest(".md-nav__item") : null;
      }
    });
  }

  function init() {
    var tocLists = document.querySelectorAll('ul[data-md-component="toc"]');
    if (!tocLists.length) {
      return;
    }

    tocLists.forEach(function (toc, listIndex) {
      if (toc.dataset.tocCollapseEnhanced === "true") {
        return;
      }
      toc.dataset.tocCollapseEnhanced = "true";

      var idPrefix = "toc-collapse-" + listIndex;
      var index = 0;
      toc.querySelectorAll(":scope > .md-nav__item").forEach(function (item) {
        index = enhanceTocItem(item, idPrefix, index);
      });
    });

    expandActivePath();
    enhanced = true;

    if (!window.__tocCollapseObserver) {
      var secondary = document.querySelector(".md-sidebar--secondary");
      if (secondary) {
        window.__tocCollapseObserver = new MutationObserver(expandActivePath);
        window.__tocCollapseObserver.observe(secondary, {
          subtree: true,
          attributes: true,
          attributeFilter: ["class"],
        });
      }
    }
  }

  function boot() {
    init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  /* Re-run when Material swaps pages (mkdocs serve / instant navigation). */
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      document.querySelectorAll('ul[data-md-component="toc"]').forEach(function (toc) {
        delete toc.dataset.tocCollapseEnhanced;
      });
      init();
    });
  }
})();
