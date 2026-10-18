(() => {
  'use strict';
  const status=document.querySelector('#admin-status'),form=document.querySelector('#login'),moderation=document.querySelector('#moderation');
  const logout=document.querySelector('#logout'),older=document.querySelector('#older');
  let csrf='',setup=false,next=null,working=false;
  const fragment=new URLSearchParams(location.hash.slice(1));let token=fragment.get('setup')||'';
  if(token)history.replaceState(null,'',location.pathname);
  async function request(action,data=null,params={}){
    const url=new URL('api.php',document.baseURI);url.searchParams.set('action',action);Object.entries(params).forEach(([k,v])=>url.searchParams.set(k,v));
    const options={credentials:'same-origin',cache:'no-store'};
    if(data){const body=new FormData();Object.entries({...data,csrf}).forEach(([k,v])=>body.set(k,v));Object.assign(options,{method:'POST',body});}
    const response=await fetch(url,options);const result=await response.json();
    if(!response.ok){if(response.status===401){form.hidden=false;moderation.hidden=true;logout.hidden=true;}throw new Error(result.error||'That action failed.');}
    return result;
  }
  function counts(n){document.querySelector('#review-count').textContent=`Comments · ${n} awaiting approval`;}
  function item(row,beat=false){
    const article=document.createElement('article');article.className='admin-item'+(!beat&&!row.reviewed?' unreviewed':'');article.dataset.id=String(row.id);
    const name=document.createElement('strong');name.textContent=beat?`${row.title} — ${row.name}`:row.name;
    const date=document.createElement('time');date.textContent=new Date(row.created_at*1000).toLocaleString();article.append(name,date);
    if(!beat&&row.has_avatar){const img=document.createElement('img');img.src='api.php?action=avatar&id='+row.id;img.alt='Profile thumbnail';img.loading='lazy';article.append(img);}
    const body=document.createElement(beat?'a':'p');body.textContent=beat?'listen to this beat':row.body;
    if(beat){body.href='../?beat='+row.id+'#live-demo';body.target='_blank';body.rel='noopener';}article.append(body);
    async function act(action,button){
      if(working)return;working=true;button.disabled=true;
      try{const result=await request(action,{id:row.id});if(action==='approve'){article.classList.remove('unreviewed');button.remove();}else article.remove();if(Number.isInteger(result.new_comments))counts(result.new_comments);status.textContent=action==='approve'?'Comment approved and published.':'Comment or beat deleted.';}
      catch(error){status.textContent=error.message;button.disabled=false;}finally{working=false;}
    }
    if(!beat&&!row.reviewed){const review=document.createElement('button');review.type='button';review.textContent='approve comment';review.onclick=()=>act('approve',review);article.append(review);}
    const del=document.createElement('button');del.type='button';del.className='delete';del.textContent=beat?'delete beat':'delete comment';del.onclick=()=>{if(confirm('Permanently delete this '+(beat?'beat':'comment')+'?'))act(beat?'delete-beat':'delete-comment',del);};article.append(del);return article;
  }
  async function load(append=false){
    const result=await request('list',null,append?{before:next}:{}),comments=document.querySelector('#comments-list');
    if(!append)comments.replaceChildren();result.comments.forEach(row=>comments.append(item(row)));counts(result.new_comments);next=result.next_before;older.hidden=!next;
    if(!append&&!result.comments.length)comments.textContent='No comments yet.';
    const beats=document.querySelector('#beats-list');beats.replaceChildren();result.beats.forEach(row=>beats.append(item(row,true)));if(!result.beats.length)beats.textContent='No shared beats yet.';
  }
  async function session(){
    const result=await request('session');csrf=result.csrf;setup=result.setup_required;
    form.hidden=result.authenticated;moderation.hidden=!result.authenticated;logout.hidden=!result.authenticated;
    document.querySelector('#setup-help').hidden=!setup;document.querySelector('#login-title').textContent=setup?'Set your admin password':'Admin login';
    form.querySelector('[type=submit]').textContent=setup?'set password':'log in';form.elements.password.autocomplete=setup?'new-password':'current-password';form.elements.password.minLength=setup?12:1;
    status.textContent=result.authenticated?'You are signed in.':setup&&!token?'Open your private setup link to choose your password.':'Only the site owner can sign in.';
    if(result.authenticated)await load();
  }
  form.onsubmit=async event=>{event.preventDefault();if(working)return;working=true;const button=form.querySelector('button');button.disabled=true;
    try{const result=await request(setup?'setup':'login',{password:form.elements.password.value,...(setup?{setup_token:token}:{})});csrf=result.csrf;token='';form.reset();await session();}
    catch(error){status.textContent=error.message;}finally{working=false;button.disabled=false;}
  };
  logout.onclick=async()=>{try{await request('logout',{});await session();}catch(e){status.textContent=e.message;}};
  document.querySelector('#refresh').onclick=()=>load().catch(e=>status.textContent=e.message);
  older.onclick=()=>load(true).catch(e=>status.textContent=e.message);
  session().catch(e=>status.textContent=e.message);
})();
