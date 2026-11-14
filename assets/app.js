/* X3 dashboard behaviour: table filter, column sort, row count, back-to-top. */
(function () {
  "use strict";

  function initFilter(table) {
    var wrap = table.closest(".table-wrap");
    if (!wrap) return;
    var tools = wrap.previousElementSibling;
    if (!tools || !tools.classList.contains("table-tools")) return;
    if (tools.dataset.bound === "1") return;
    tools.dataset.bound = "1";

    var input = tools.querySelector("input");
    var count = tools.querySelector(".count");
    if (!input) return;

    var rows = Array.prototype.slice.call(table.tBodies[0].rows);

    function apply() {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (row) {
        var hit = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (count) {
        count.textContent = q
          ? shown + " of " + rows.length + " rows"
          : rows.length + " rows";
      }
    }
    input.addEventListener("input", apply);
    apply();
  }

  function initSort(table) {
    var headers = table.querySelectorAll("thead th.sortable");
    Array.prototype.forEach.call(headers, function (th, idx) {
      var arrow = document.createElement("span");
      arrow.className = "arrow";
      arrow.textContent = "▼";
      th.appendChild(arrow);
      th.addEventListener("click", function () {
        var tbody = table.tBodies[0];
        var rows = Array.prototype.slice.call(tbody.rows);
        var numeric = th.dataset.numeric === "1";
        var dir = th.dataset.dir === "asc" ? -1 : 1;
        Array.prototype.forEach.call(headers, function (o) {
          o.dataset.dir = "";
          var a = o.querySelector(".arrow");
          if (a) a.textContent = "▼";
        });
        th.dataset.dir = dir === 1 ? "asc" : "desc";
        arrow.textContent = dir === 1 ? "▲" : "▼";
        rows.sort(function (a, b) {
          var ac = a.cells[idx], bc = b.cells[idx];
          if (!ac || !bc) return 0;
          var av = ac.textContent.trim(), bv = bc.textContent.trim();
          if (numeric) {
            var an = parseFloat(av.replace(/[^0-9.\-]/g, "")) || 0;
            var bn = parseFloat(bv.replace(/[^0-9.\-]/g, "")) || 0;
            return (an - bn) * dir;
          }
          return av.localeCompare(bv) * dir;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll("table"), function (table) {
      initFilter(table);
      initSort(table);
    });

    var top = document.createElement("button");
    top.className = "to-top";
    top.title = "Back to top";
    top.textContent = "↑";
    top.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    document.body.appendChild(top);
    window.addEventListener("scroll", function () {
      top.classList.toggle("show", window.scrollY > 500);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
