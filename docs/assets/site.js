// Simple row filter for tables: <input class="search" data-target="table-id">
document.querySelectorAll('input.search').forEach(function (box) {
  var table = document.getElementById(box.dataset.target);
  if (!table) return;
  box.addEventListener('input', function () {
    var q = box.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function (tr) {
      tr.style.display = tr.textContent.toLowerCase().indexOf(q) > -1 ? '' : 'none';
    });
  });
});
