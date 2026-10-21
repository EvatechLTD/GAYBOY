(() => {
  function mountInstagram() {
    const galleries = [...document.querySelectorAll('.site-shell #screenshots')];
    document.querySelectorAll('.homepage:not([data-preview])').forEach(page => {
      const official = [...page.querySelectorAll('a.hp-download')].some(a => {
        const target = new URL(a.href);
        return target.origin === location.origin && /^\/apps\/gayboy\/downloads\/GAYBOY(?:-[0-9][a-z0-9._-]*)?\.gb$/i.test(target.pathname);
      });
      if (official) {
        const gallery = page.querySelector('.hp-main .hp-gallery')?.closest('.hp-panel');
        if (gallery) galleries.push(gallery);
      }
    });
    galleries.forEach(gallery => {
      if (gallery.parentElement.querySelector('.gayboy-instagram')) return;
      const panel = document.createElement('section');
      panel.className = 'panel hp-panel gayboy-instagram';
      panel.setAttribute('aria-label', 'Recent Instagram posts from bestjonever');
      panel.innerHTML = `<h2>life outside the cartridge</h2>
        <div class="gbig-content"><div class="gbig-intro"><div><strong>@bestjonever</strong><p>little machines. big noises. recent posts from my Instagram.</p></div>
        <a href="https://www.instagram.com/bestjonever/" target="_blank" rel="noopener">visit my Instagram &#8599;</a></div>
        <div class="gbig-embed"><iframe src="https://www.instagram.com/bestjonever/embed/" title="Recent posts from @bestjonever on Instagram" loading="lazy" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>
        <p class="gbig-note">Instagram being Instagram? <a href="https://www.instagram.com/bestjonever/" target="_blank" rel="noopener">See the posts over there &#8599;</a></p></div>`;
      gallery.after(panel);
    });
  }
  new MutationObserver(mountInstagram).observe(document.body, {childList: true, subtree: true});
  mountInstagram();
})();
