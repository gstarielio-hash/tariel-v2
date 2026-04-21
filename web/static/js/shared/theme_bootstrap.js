(function () {
  var STORAGE_KEY = "tariel_theme";

  function normalizeTheme(value) {
    if (typeof value !== "string") return "";
    var normalized = value.trim().toLowerCase();
    return normalized === "dark" || normalized === "light" ? normalized : "";
  }

  function readThemeFromQuery() {
    try {
      var url = new URL(window.location.href);
      return normalizeTheme(url.searchParams.get("theme") || url.searchParams.get("tema"));
    } catch (_err) {
      return "";
    }
  }

  function applyTheme(theme, persist) {
    var next = normalizeTheme(theme) || "light";
    document.documentElement.setAttribute("data-theme", next);
    if (document.body) {
      document.body.setAttribute("data-theme", next);
    }
    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch (_err) {
        /* no-op */
      }
    }
    return next;
  }

  var queryTheme = readThemeFromQuery();
  var storedTheme = "";

  try {
    storedTheme = normalizeTheme(window.localStorage.getItem(STORAGE_KEY));
  } catch (_err) {
    storedTheme = "";
  }

  var initialTheme = queryTheme || storedTheme || "light";
  applyTheme(initialTheme, Boolean(queryTheme));

  if (!document.body) {
    document.addEventListener("DOMContentLoaded", function () {
      if (document.body) {
        document.body.setAttribute(
          "data-theme",
          document.documentElement.getAttribute("data-theme") || "light"
        );
      }
    });
  }

  window.TarielTheme = {
    get: function () {
      return document.documentElement.getAttribute("data-theme") || "light";
    },
    set: function (theme) {
      return applyTheme(theme, true);
    },
    toggle: function () {
      var current = this.get();
      return applyTheme(current === "dark" ? "light" : "dark", true);
    }
  };
})();
