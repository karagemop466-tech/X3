
document.querySelectorAll('input.filt').forEach(function(inp){
  var t=document.getElementById(inp.dataset.for); if(!t) return;
  var rows=[].slice.call(t.querySelectorAll('tbody tr'));
  inp.addEventListener('input',function(){
    var q=inp.value.toLowerCase().trim();
    rows.forEach(function(r){ r.style.display = !q || r.textContent.toLowerCase().indexOf(q)>=0 ?'':'none'; });
    var n=rows.filter(function(r){return r.style.display!=='none'}).length;
    var c=t.closest('.tblwrap').querySelector('caption');
    if(!c) return; if(!c.dataset.base) c.dataset.base=c.textContent;
    c.textContent = c.dataset.base + '  -  ' + n + ' of ' + rows.length + ' rows';
  });
});
