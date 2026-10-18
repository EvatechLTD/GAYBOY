(() => {
  'use strict';
  const link=document.createElement('a');link.href='admin/';link.className='admin-login';link.textContent='admin login';
  document.querySelector('.system-bar').append(link);
  let checking=false;
  async function check(){
    if(checking||document.hidden)return;checking=true;
    try{
      const response=await fetch('admin/api.php?action=status',{credentials:'same-origin',cache:'no-store'});
      if(!response.ok)return;const data=await response.json();
      const count=data.authenticated?data.new_comments||0:0;
      link.textContent=data.authenticated?count?`Admin · ${count} pending`:'Admin · queue clear':'admin login';
      link.classList.toggle('admin-new',count>0);link.setAttribute('aria-label',count?`Admin: ${count} new comments to moderate`:link.textContent);
    }catch{}finally{checking=false;}
  }
  window.addEventListener('focus',check);document.addEventListener('visibilitychange',check);setInterval(check,60000);check();
})();
