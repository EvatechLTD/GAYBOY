import {state,$,esc,api,on,notify,box,refresh,pageLink} from './core.js';
import {showPage} from './homepage.js';
import {openEditor} from './editor.js';
import {studio} from './studio.js';
import {directory,desk,pins,rooms,room,rings,board,globalSocial,openDM,closeDM} from './social.js';

function home(){
    $('#view').innerHTML=`<section class="window"><h2>WELCOME TO THE OTHER SIDE OF MIDNIGHT <span>00:00</span></h2><div class="hero"><div class="eyebrow">Y2KCRISIS / HOMEPAGES & HANGOUTS</div><span class="stamp">PLEASE DO NOT<br>FEED THE BUG</span><h1>your computer<br>has friends<br>in it.</h1><p>Decorate a homepage. Burn a virtual mixtape. Find somebody’s sticker in the bathroom. Stay up talking.</p><div class="actions"><button id="move-in">${state.me?'DECORATE MY HOMEPAGE':'MAKE MY HOMEPAGE ↗'}</button><a href="#directory">wander around →</a></div><a class="see-example" href="/~GAYBOY">Visit GAYBOY’s homepage / try the playable app ↗</a></div></section><div class="section-grid">${box('01 / THE HOMEPAGE BUILDER','<h3>Customize until<br>it breaks.</h3><p>Fonts, wallpapers, pixel art, photos, badges, a scrolling ticker. Pick a template, move things around, make it yours.</p><a href="#edit">Decorate your corner →</a>')}${box('02 / YOUR PAGE HAS A SOUNDTRACK','<h3>Play it<br>where you live.</h3><p>YouTube. SoundCloud. Spotify. Vimeo. Bandcamp embeds. Mixcloud. Twitch. Paste a link and put the player on your page.</p><a href="#edit">Build a little listening room →</a>')}${box('03 / A LITTLE TIN OF STORIES','<h3>I made two.<br>You have the other.</h3><p>Finite pins with real ownership. One active sticker signature. Bathroom graffiti, doodled guestbooks and private postcards.</p><a href="#paint">Make your mark →</a>')}${box('04 / THE BUDDY LIST IS OPEN','<h3>“you still up?”</h3><p>A floating instant messenger, away messages, member-hosted chatrooms, and a bulletin board you can reach the end of.</p><a href="#chat">Find a room →</a>')}</div><div class="home-shortcuts"><a href="#board">Bulletin board ↗</a><a href="#rings">Webrings ↗</a><a href="#desk">My desk ↗</a></div>`;
    on('#move-in','click',()=>{if(state.me)location.hash='edit';else $('#auth').showModal();});
}
function routeParts(){if(location.hash.length>1)return location.hash.slice(1).split('/').map(decodeURIComponent);const match=location.pathname.match(/^\/~([^/]+)(?:\/([^/]+))?\/?$/);return match?['page',decodeURIComponent(match[1]),decodeURIComponent(match[2]||'')]:['home'];}
async function render(){
    state.version++;clearInterval(state.timer);state.timer=null;if(state.cleanup){state.cleanup();state.cleanup=null;}
    const parts=routeParts(),kind=parts[0];document.body.classList.toggle('page-route',kind==='page');document.body.classList.toggle('editor-route',kind==='edit');document.title='Y2KCRISIS / your computer has friends in it.';
    try{
        if(kind==='home')home();
        else if(kind==='directory')await directory();
        else if(kind==='page'){if(!parts[1]&&!state.me){$('#view').innerHTML=box('MAKE YOURSELF AT HOME','<h1 class="big-title">Your little corner awaits.</h1><button data-signin>CREATE AN ACCOUNT ↗</button>');return;}await showPage(parts[1]||state.me.id,parts[2]||'');}
        else if(kind==='edit')await openEditor(parts[1]||'');
        else if(kind==='paint')await studio();
        else if(kind==='pins')await pins();
        else if(kind==='desk')await desk();
        else if(kind==='chat'&&parts[1]==='room')await room(parts[2]);
        else if(kind==='chat'&&parts[1]==='dm'){await desk();await openDM(+parts[2]);}
        else if(kind==='chat')await rooms();
        else if(kind==='rings')await rings();
        else if(kind==='board')await board();
        else if(kind==='apps')$('#view').innerHTML=box('APP DRAWER / MADE ON Y2KCRISIS','<h1 class="big-title">Small apps. Big feelings.</h1><article class="app-card"><img src="apps/gayboy/images/train.png" alt="GAYBOY beatmaker pixel art"><div><h2>GAYBOY</h2><p>A playable Game Boy music workstation with synths, drums, a sequencer and a tutorial.</p><div class="actions"><a href="/~GAYBOY">VISIT ITS HOMEPAGE ↗</a><a href="apps/gayboy/player.html" target="_blank" rel="noopener">LAUNCH PLAYER ↗</a></div><p class="muted">The GAYBOY page uses the same customizable homepage system as yours.</p></div></article>');
        else home();
    }catch(e){$('#view').innerHTML=box('CONNECTION INTERRUPTED',`<p>${esc(e.message)}</p><a href="#home">Back to start →</a>`);}
}
on('#account','click',()=>{if(!state.me){$('#auth').showModal();return;}$('#account-menu').innerHTML=`<div class="dialog-title">@${esc(state.me.handle)}<button id="close-account" aria-label="Close">×</button></div><div class="pad"><div class="account-links"><a href="${pageLink(state.me)}">My homepage ↗</a><a href="#edit">Homepage builder ↗</a><a href="#desk">My desk / account recovery ↗</a><a href="#pins">My pin tin ↗</a><a href="#paint">Tag studio ↗</a></div><button id="logout">SIGN OUT</button></div>`;$('#account-menu').showModal();on('#close-account','click',()=>$('#account-menu').close());$('#account-menu').querySelectorAll('a').forEach(a=>a.onclick=()=>$('#account-menu').close());on('#logout','click',async()=>{await api('logout',{});closeDM();$('#account-menu').close();await refresh();location.hash='home';await render();notify('Signed out. See you around.');});});
on('#close-auth','click',()=>$('#auth').close());
on('#auth-form','submit',async e=>{e.preventDefault();$('#auth-error').textContent='';const b=e.submitter;b.disabled=true;try{const r=await api(b.value,Object.fromEntries(new FormData(e.target)));if(b.value==='recover'){notify('Password reset. Sign in with your new password.');$('#recovery-fields').hidden=true;return;}state.csrf=r.csrf;$('#auth').close();e.target.reset();await refresh();location.hash=b.value==='register'?'edit':'desk';await render();}catch(err){$('#auth-error').textContent=err.message;}finally{b.disabled=false;}});
on('#show-recover','click',()=>{$('#recovery-fields').hidden=!$('#recovery-fields').hidden;});
document.addEventListener('click',e=>{if(e.target.closest('[data-signin]'))$('#auth').showModal();});
globalSocial();window.addEventListener('hashchange',render);
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'&&$('#save-page')){e.preventDefault();$('#save-page').click();}});
setInterval(()=>{$('#clock').textContent=new Date().toLocaleTimeString('en-GB');},1000);
setInterval(()=>{if(state.me&&!document.hidden)api('heartbeat',{}).catch(()=>{});},45000);
window.addEventListener('beforeunload',()=>{if(state.cleanup)state.cleanup();});
(async()=>{try{await refresh();if(state.me)await api('heartbeat',{});await render();}catch(e){$('#view').innerHTML=box('CONNECTION INTERRUPTED',`<p>${esc(e.message)}</p><p>Please refresh in a moment.</p>`);}})();

window.addEventListener('message',e=>{if(e.origin===location.origin&&e.data?.type==='y2k-signin')document.querySelector('#auth').showModal();});
