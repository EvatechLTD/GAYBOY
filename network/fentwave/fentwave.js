'use strict';
const dialog = document.querySelector('#waitlist');
const form = document.querySelector('#waitlist-form');
const status = document.querySelector('#signup-status');
const submit = document.querySelector('#signup-submit');
let token = null;
let loading = null;
async function prepare() {
  if (token) return token;
  if (!loading) loading = fetch('waitlist.php', {credentials:'same-origin', cache:'no-store'})
    .then(async response => { const data = await response.json(); if (!response.ok || !data.csrf) throw new Error(data.error || 'Could not connect. Please try again.'); token = data.csrf; return token; })
    .finally(() => { loading = null; });
  return loading;
}
for (const button of document.querySelectorAll('[data-waitlist]')) button.addEventListener('click', () => {
  status.textContent = ''; dialog.showModal();
  prepare().catch(error => { status.textContent = error.message; });
});
document.querySelector('#close-waitlist').addEventListener('click', () => dialog.close());
document.querySelector('#back-to-page').addEventListener('click', () => dialog.close());
document.querySelector('#dialog-privacy').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
form.addEventListener('submit', async event => {
  event.preventDefault(); if (!form.reportValidity()) return;
  submit.disabled = true; status.textContent = 'Connecting…';
  try {
    const data = new FormData(form);
    const response = await fetch('waitlist.php', {
      method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({csrf:await prepare(), name:data.get('name'), email:data.get('email'), website:data.get('website'), consent:data.get('consent') === 'on'})
    });
    const result = await response.json();
    if (!response.ok || !result.ok) { if (response.status === 403) token = null; throw new Error(result.error || 'Could not join just yet. Please try again.'); }
    form.reset(); status.textContent = '';
    document.querySelector('#signup-content').hidden = true;
    const success = document.querySelector('#signup-success'); success.hidden = false; success.focus();
  } catch (error) { status.textContent = error.message || 'Could not connect. Please try again.'; }
  finally { submit.disabled = false; }
});
const shots = {main:{src:'images/main.png',alt:'Actual FENTWAVE software screen showing SID patch controls and an envelope editor'},mod:{src:'images/mod.png',alt:'Actual FENTWAVE modulation editing screen on the Commodore 64'}};
for (const button of document.querySelectorAll('[data-screen]')) button.addEventListener('click', () => {
  const shot = shots[button.dataset.screen]; const screen = document.querySelector('#screen'); screen.src = shot.src; screen.alt = shot.alt;
  for (const tab of document.querySelectorAll('[data-screen]')) { const active = tab === button; tab.classList.toggle('selected',active); tab.setAttribute('aria-pressed',String(active)); }
});
for (const button of document.querySelectorAll('.swatches [data-color]')) button.addEventListener('click', () => {
  document.querySelector('.mini-homepage').dataset.color = button.dataset.color;
  for (const swatch of document.querySelectorAll('.swatches [data-color]')) swatch.setAttribute('aria-pressed', String(swatch === button));
});
