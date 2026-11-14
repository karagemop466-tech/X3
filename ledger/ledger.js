document.querySelectorAll('input.filter').forEach(function(inp){
  inp.addEventListener('input',function(){
    var q=inp.value.toLowerCase();
    var t=inp.parentElement.querySelector('table');
    if(!t)return;
    t.querySelectorAll('tbody tr').forEach(function(tr){
      tr.style.display=tr.textContent.toLowerCase().indexOf(q)>-1?'':'none';
    });
  });
});
