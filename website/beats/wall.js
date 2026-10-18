(() => {
  'use strict';
  const demo=document.querySelector('#live-demo');
  const section=document.createElement('section');section.id='beats';section.className='panel wall-panel beat-wall';
  section.innerHTML=`<h2>♫ BEATS IN MY EXTENDED NETWORK</h2><div class="wall-intro"><p>Made here. Shared here. Click a beat to hear it in GAYBOY.</p></div><p class="beat-status" role="status"></p><div class="beat-list"></div><button type="button" class="wall-more" hidden>more beats</button>`;
  demo.after(section);
  const nav=document.querySelector('nav'),navLink=document.createElement('a');navLink.href='#beats';navLink.textContent='♫ beats';nav.append(navLink);
  const share=document.createElement('button');share.type='button';share.id='demo-share';share.textContent='share beat';demo.querySelector('.handheld-brand i').after(share);
  const back=document.createElement('button');back.type='button';back.textContent='↩ back to my beat';back.hidden=true;demo.querySelector('.demo-toolbar').prepend(back);
  back.addEventListener('click',async()=>{await window.gayboyBeats.returnToMyBeat();back.hidden=true;history.replaceState(null,'',location.pathname+'#beats');});
  const dialog=document.createElement('dialog');dialog.className='beat-dialog';dialog.setAttribute('aria-labelledby','beat-dialog-title');
  dialog.innerHTML=`<div class="beat-window-titlebar"><strong>GAYBOY · share beat</strong><button type="button" class="beat-close" aria-label="Close share form">×</button></div><form class="wall-form"><h3 id="beat-dialog-title">Name your beat ♫</h3><p>Your beat is captured. Name it and share it with the neighborhood.</p><label for="beat-title">Beat name</label><input id="beat-title" name="title" maxlength="80" placeholder="My tiny masterpiece" autofocus required><label for="beat-name">Your display name</label><input id="beat-name" name="name" maxlength="40" autocomplete="nickname" required><label class="wall-honeypot" aria-hidden="true">Leave empty<input name="website" tabindex="-1" autocomplete="off"></label><fieldset><legend>♥ human check</legend><img class="wall-code-image" width="320" height="90" alt="Six-digit human check; audio alternative below."><button type="button" class="beat-refresh">new code</button><details><summary>listen to the code</summary><audio controls preload="none" aria-label="Spoken human-check digits"></audio></details><label for="beat-code">The six digits</label><input id="beat-code" name="human_code" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="off" required></fieldset><button type="submit" class="wall-submit" disabled>SHARE BEAT ♫</button><p class="wall-status" role="status"></p><p class="wall-privacy">Your name, title and playable beat will be public. Only the site admin can remove shared beats.</p></form>`;
  document.body.append(dialog);
  const form=dialog.querySelector('form'),submit=form.querySelector('[type=submit]'),formStatus=form.querySelector('[role=status]');
  const status=section.querySelector('[role=status]'),list=section.querySelector('.beat-list'),more=section.querySelector('.wall-more');
  const api=new URL('beats/api.php',document.baseURI);
  let snapshot=null,challenge=null,offset=null,busy=false,loadingBeat=false,pending=null;
  function url(action,params={}){const u=new URL(api);u.searchParams.set('action',action);Object.entries(params).forEach(([k,v])=>u.searchParams.set(k,v));return u;}
  async function request(action,options={},params={}){
    const response=await fetch(url(action,params),{credentials:'same-origin',cache:'no-store',...options});
    let data;try{data=await response.json();}catch{throw new Error('The beat wall is unavailable. Try again shortly.');}
    if(!response.ok)throw new Error(data.error||'Could not complete that beat request.');return data;
  }
  function link(id){const u=new URL(location.pathname,location.origin);u.searchParams.set('beat',id);u.hash='live-demo';return u.href;}
  async function human(){
    challenge=null;submit.disabled=true;
    challenge=await request('challenge');form.elements.human_code.value='';
    form.querySelector('img').src=url('image',{nonce:challenge.nonce});
    const audio=form.querySelector('audio');audio.pause();audio.src=url('audio',{nonce:challenge.nonce});
    submit.disabled=busy;
  }
  async function openShare(){
    if(busy)return;
    try{
      snapshot=await window.gayboyBeats.capture();
      try{form.elements.name.value=localStorage.getItem('gayboy-wall-name')||'';}catch{}
      formStatus.textContent='';dialog.showModal();await human();
    }catch(error){if(dialog.open)formStatus.textContent=error.message;else{status.textContent=error.message;section.scrollIntoView({block:'start'});}}
  }
  share.addEventListener('click',openShare);
  dialog.querySelector('.beat-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{form.querySelector('audio').pause();});
  form.querySelector('.beat-refresh').addEventListener('click',()=>human().catch(e=>formStatus.textContent=e.message));
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!snapshot||!challenge)return;
    busy=true;submit.disabled=true;formStatus.textContent='Sharing your beat…';
    const data=new FormData(form);data.set('csrf',challenge.csrf);data.set('nonce',challenge.nonce);data.set('snapshot',new Blob([snapshot],{type:'application/octet-stream'}),'beat.gbb');
    try{
      const beat=await request('post',{method:'POST',body:data});
      try{localStorage.setItem('gayboy-wall-name',form.elements.name.value);}catch{}
      dialog.close();form.elements.title.value='';await load().catch(()=>{});
      status.replaceChildren(document.createTextNode('Your beat is on the wall! '));
      const a=document.createElement('a');a.href=link(beat.id);a.textContent='Your share link';status.append(a);
      const copy=document.createElement('button');copy.type='button';copy.textContent='copy link';
      copy.onclick=async()=>{try{await navigator.clipboard.writeText(link(beat.id));copy.textContent='copied!';}catch{status.append(document.createTextNode(' '+link(beat.id)));}};status.append(' ',copy);
      window.gayboyBeats.minimize();section.scrollIntoView({block:'start'});
    }catch(error){formStatus.textContent=error.message;await human().catch(()=>{});}
    finally{busy=false;submit.disabled=!challenge;}
  });
  async function playBeat(id){
    if(loadingBeat)return;
    loadingBeat=true;status.textContent='Loading beat…';
    try{
      window.gayboyBeats.unlock();
      const beat=await request('beat',{}, {id});
      const bytes=Uint8Array.from(atob(beat.snapshot),c=>c.charCodeAt(0));
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
      if(digest!==beat.sha)throw new Error('That beat download was incomplete. Try again.');
      await window.gayboyBeats.listen(bytes);back.hidden=false;pending=null;
      history.replaceState(null,'',link(id));status.textContent=`Now playing: ${beat.title} by ${beat.name}`;
      demo.querySelector('.demo-status').textContent=`♫ ${beat.title} — ${beat.name}. Your own music is preserved; use “back to my beat” to return.`;
    }catch(error){status.textContent=error.message;}finally{loadingBeat=false;}
  }
  function row(beat){
    const article=document.createElement('article');article.className='beat-row';article.dataset.beatId=beat.id;
    const a=document.createElement('a');a.href=link(beat.id);a.className='beat-play';a.textContent='▶ '+beat.title;
    a.addEventListener('click',event=>{if(event.button||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();playBeat(beat.id);});
    const by=document.createElement('p');by.textContent=`by ${beat.name} · ${new Date(beat.created_at*1000).toLocaleDateString()}`;article.append(a,by);
    return article;
  }
  async function load(append=false){
    const data=await request('list',{},append?{offset}:{});if(!append)list.replaceChildren();
    data.beats.forEach(beat=>list.append(row(beat)));offset=data.next_offset;more.hidden=offset===null;
    if(!data.total){const p=document.createElement('p');p.className='wall-empty';p.textContent='No beats yet. Make some noise and be the first on the wall.';list.append(p);}
  }
  more.onclick=()=>load(true).catch(e=>status.textContent=e.message);
  load().catch(e=>status.textContent=e.message);
  const id=new URL(location.href).searchParams.get('beat');
  if(id&&/^[a-f0-9]{24}$/.test(id)){
    pending=id;const button=demo.querySelector('#demo-play');button.textContent='▶ PLAY THIS BEAT';
    demo.querySelector('.demo-cover>span').textContent='a beat from your extended network ♫';
    button.addEventListener('click',event=>{if(!pending)return;event.preventDefault();event.stopImmediatePropagation();playBeat(pending);},true);
    demo.scrollIntoView({block:'start'});
  }
})();
