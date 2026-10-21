(() => {
  const assets = new URL('.', document.currentScript.src);
  let links = null;
  fetch(new URL('gayboy-tips.json', assets)).then(r => {
    if (!r.ok) throw new Error('Unavailable');
    return r.json();
  }).then(data => {
    if (['five', 'custom'].every(k => /^https:\/\/buy\.stripe\.com\/[A-Za-z0-9_]+$/.test(data[k]))) links = data;
  }).catch(() => {});

  const modal = document.createElement('dialog');
  modal.className = 'gayboy-tip-dialog';
  modal.setAttribute('aria-labelledby', 'gayboy-tip-title');
  modal.innerHTML = `<button type="button" class="tip-close" aria-label="Close donation prompt">X</button>
    <p class="tip-eyebrow">GAYBOY / THE HONEST DOWNLOAD WINDOW</p>
    <h2 id="gayboy-tip-title">tiny ROM. even tinier bank account.</h2>
    <p>We made a whole music studio for a Game Boy. Our bank account is also running on 8 bits.</p>
    <p>If you've got a spare $5, help keep the little machine going. If you're broke too, we get it.</p>
    <div class="tip-options"><button type="button" data-tip="five">Tip $5.00 + download</button>
    <button type="button" data-tip="custom">Custom tip + download</button>
    <button type="button" data-tip="free">$0.00 / just download</button></div>
    <p class="tip-note">USD. One-time, optional tip. Same ROM at every amount. Custom amount entered on Stripe ($0.50 minimum).</p>
    <p class="tip-status" role="status"></p>`;
  document.body.append(modal);
  function addSupportLinks() {
    document.querySelectorAll('a.download-button, a.hp-download').forEach(anchor => {
      if (!/\/GAYBOY(?:-[0-9][a-z0-9._-]*)?\.gb$/i.test(new URL(anchor.href).pathname) || anchor.dataset.tipReady) return;
      anchor.dataset.tipReady = 'true';
      const note = document.createElement('p');
      note.className = 'gayboy-support-note';
      const link = document.createElement('a');
      link.href = anchor.href;
      link.textContent = '\u2665 support GAYBOY';
      note.append(link, ' / ROM\u2019s free. Tips help keep the little machine going.');
      anchor.after(note);
    });
  }
  function addEmulatorSupport() {
    document.querySelectorAll('.hp-app-block, #live-demo').forEach(panel => {
      if (panel.querySelector('.gayboy-emulator-support')) return;
      const note = document.createElement('p');
      note.className = 'gayboy-support-note gayboy-emulator-support';
      const link = document.createElement('a');
      link.href = new URL('downloads/GAYBOY.gb', new URL(panel.matches('.hp-app-block') ? 'apps/gayboy/' : './', document.baseURI)).href;
      link.textContent = '\u2665 SUPPORT GAYBOY';
      note.append(link, ' / Enjoying the little machine? Leave an optional tip.');
      const caption = panel.querySelector('.hp-caption');
      if (caption) caption.replaceWith(note);
      else (panel.querySelector('.hp-content') || panel).append(note);
    });
  }
  new MutationObserver(addEmulatorSupport).observe(document.body, {childList: true, subtree: true});
  addEmulatorSupport();
  new MutationObserver(addSupportLinks).observe(document.body, {childList: true, subtree: true});
  addSupportLinks();
  let pending;
  let downloading = false;
  function download() {
    const a = document.createElement('a');
    a.href = pending.href;
    a.download = pending.download || 'GAYBOY.gb';
    document.body.append(a);
    downloading = true;
    a.click();
    downloading = false;
    a.remove();
  }
  modal.querySelector('.tip-close').onclick = () => modal.close();
  modal.addEventListener('click', event => {
    const choice = event.target.closest('[data-tip]')?.dataset.tip;
    if (!choice) return;
    if (choice === 'free') { download(); modal.close(); return; }
    if (!links) {
      modal.querySelector('.tip-status').textContent = 'Stripe is unavailable right now. You can still download for $0.';
      return;
    }
    const checkout = window.open(links[choice], '_blank');
    if (!checkout) {
      modal.querySelector('.tip-status').textContent = 'Allow the checkout tab to open, or choose the $0 download.';
      return;
    }
    checkout.opener = null;
    download();
    modal.querySelector('.tip-status').textContent = 'Your ROM is downloading. Finish your optional tip in the Stripe tab. Thank you!';
  });
  document.addEventListener('click', event => {
    if (downloading || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest('a[href]');
    if (!anchor || anchor.closest('[data-preview]')) return;
    const target = new URL(anchor.href);
    if (target.origin !== location.origin || !/\/GAYBOY(?:-[0-9][a-z0-9._-]*)?\.gb$/i.test(target.pathname)) return;
    event.preventDefault();
    pending = {href: target.href, download: anchor.getAttribute('download')};
    modal.querySelector('.tip-status').textContent = '';
    modal.showModal();
  });
})();
