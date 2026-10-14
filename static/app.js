function toast(msg, err=false){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (err ? ' err' : '');
  clearTimeout(window._toast);
  window._toast = setTimeout(() => t.classList.remove('show'), 3500);
}