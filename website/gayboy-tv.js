(() => {
  const videoURL = 'https://www.youtube-nocookie.com/embed/ud--itAd5v0?autoplay=1&mute=1&loop=1&playlist=ud--itAd5v0&playsinline=1&rel=0';
  function mountTV() {
    const hosts = [...document.querySelectorAll('.site-shell .sidebar')];
    document.querySelectorAll('.homepage:not([data-preview])').forEach(page => {
      // The official ROM's download identifies GAYBOY without changing member pages.
      if ([...page.querySelectorAll("a.hp-download")].some(a => {
        const target = new URL(a.href);
        return target.origin === location.origin && /^\/apps\/gayboy\/downloads\/GAYBOY(?:-[0-9][a-z0-9._-]*)?\.gb$/i.test(target.pathname);
      })) {
        const sidebar = page.querySelector('.hp-sidebar');
        if (sidebar) hosts.push(sidebar);
      }
    });
    hosts.forEach(host => {
      if (host.querySelector('.gayboy-tv')) return;
      const tv = document.createElement('section');
      tv.className = 'gayboy-tv';
      tv.setAttribute('aria-label', 'GAYBOY sponsor screen in a Commodore 1702 style monitor');
      tv.innerHTML = `<p class="gbtv-caption">GAYBOY TV / now playing</p>
        <div class="gbtv-set"><div class="gbtv-bezel"><div class="gbtv-screen">
          <div class="gbtv-card"><iframe class="gbtv-video" title="GAYBOY TV: featured YouTube Short" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>
          <span class="gbtv-off" hidden>screen off. world still weird.</span>
        </div></div><div class="gbtv-bottom"><div class="gbtv-nameplate"><span class="gbtv-rainbow" aria-hidden="true"></span><span class="gbtv-brand">commodore <b>1702</b></span></div>
          <div class="gbtv-control-panel"><div class="gbtv-knobs" aria-hidden="true"><span>COLOR<i></i></span><span>BRIGHT<i></i></span><span>CONTRAST<i></i></span></div>
          <button type="button" class="gbtv-power" aria-label="Monitor power" aria-pressed="true"><span aria-hidden="true"></span>POWER</button></div>
          <div class="gbtv-speaker" aria-hidden="true"></div></div></div>
        <div class="gbtv-feet" aria-hidden="true"></div><p class="gbtv-note">On repeat. Starts muted.<br><a href="https://www.youtube.com/shorts/ud--itAd5v0" target="_blank" rel="noopener">Watch on YouTube</a></p>`;
      const frame = tv.querySelector('.gbtv-video');
      frame.src = videoURL;
      tv.querySelector('.gbtv-power').addEventListener('click', event => {
        const button = event.currentTarget;
        const on = button.getAttribute('aria-pressed') !== 'true';
        button.setAttribute('aria-pressed', String(on));
        tv.classList.toggle('gbtv-powered-off', !on);
        tv.querySelector('.gbtv-card').hidden = !on;
        tv.querySelector('.gbtv-off').hidden = on;
        if (on) frame.src = videoURL; else frame.removeAttribute('src');
      });
      const profile = host.querySelector('.contact, .hp-identity');
      if (profile) profile.after(tv); else host.append(tv);
    });
  }
  new MutationObserver(mountTV).observe(document.body, {childList: true, subtree: true});
  mountTV();
})();
