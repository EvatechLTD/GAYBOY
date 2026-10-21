(() => {
  const profile = 'https://github.com/EvatechLTD';
  let recent;
  function repositories() {
    return recent ||= fetch('github-repos.json', {cache: 'no-cache'})
      .then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(data => data.repositories.filter(repo => {
        try { const url = new URL(repo.url); return url.origin === 'https://github.com' && url.pathname.startsWith('/EvatechLTD/'); } catch { return false; }
      }).slice(0, 4));
  }
  function mount() {
    const galleries = [...document.querySelectorAll('.site-shell #screenshots')];
    document.querySelectorAll('.homepage:not([data-preview])').forEach(page => {
      const official = [...page.querySelectorAll('a.hp-download')].some(a => {
        const url = new URL(a.href);
        return url.origin === location.origin && /^\/apps\/gayboy\/downloads\/GAYBOY(?:-[0-9][a-z0-9._-]*)?\.gb$/i.test(url.pathname);
      });
      if (official) { const gallery = page.querySelector('.hp-main .hp-gallery')?.closest('.hp-panel'); if (gallery) galleries.push(gallery); }
    });
    galleries.forEach(gallery => {
      if (gallery.parentElement.querySelector('.gayboy-github')) return;
      const panel = document.createElement('section');
      panel.className = 'panel hp-panel gayboy-github';
      panel.setAttribute('aria-label', 'GAYBOY source code and recent GitHub repositories');
      panel.innerHTML = `<h2>under the cartridge / GitHub</h2><div class="gbgh-content"><p>GAYBOY is a Game Boy synth, piano-roll sequencer and chiptune drum machine. Follow the code, see what changed, or help squash a bug.</p><p><a href="${profile}/GAYBOY">GAYBOY source code ↗</a> · <a href="${profile}/GAYBOY/commits/">recent commits</a> · <a href="${profile}/GAYBOY/issues">bugs + ideas</a></p><h3>recently updated public repos</h3><ul class="gbgh-repos"><li><a href="${profile}/GAYBOY">GAYBOY</a> — Game Boy synth and sequencer</li></ul><p class="gbgh-note"><a href="${profile}?tab=repositories">all repos by EvatechLTD ↗</a></p></div>`;
      const guide = document.createElement('p');
      const guideBase = gallery.closest('.site-shell') ? 'guide/' : 'apps/gayboy/guide/';
      guide.innerHTML = `<strong>user guides / review drafts</strong><br><a href="${guideBase}">Read the illustrated guide</a> · <a href="${guideBase}GAYBOY-user-guide-review.pdf">download PDF</a> · <a href="${profile}/GAYBOY/tree/main/docs/user-guide">guide files on GitHub</a>`;
      panel.querySelector('.gbgh-content').insertBefore(guide, panel.querySelector('h3'));
      gallery.after(panel);
      repositories().then(repos => {
        if (!repos.length || !panel.isConnected) return;
        const list = panel.querySelector('.gbgh-repos'); list.replaceChildren();
        repos.forEach(repo => {
          const li = document.createElement('li'), link = document.createElement('a');
          link.href = repo.url; link.textContent = repo.name; li.append(link);
          const p = document.createElement('p'); p.textContent = repo.description || 'Explore this project on GitHub.'; li.append(p);
          const date = new Date(repo.updated);
          if (!Number.isNaN(date.valueOf())) { const time = document.createElement('time'); time.dateTime = date.toISOString(); time.textContent = 'Updated ' + date.toLocaleDateString(undefined, {year:'numeric',month:'short',day:'numeric'}); li.append(time); }
          list.append(li);
        });
      }).catch(() => {});
    });
  }
  new MutationObserver(mount).observe(document.body, {childList:true, subtree:true});
  mount();
})();
