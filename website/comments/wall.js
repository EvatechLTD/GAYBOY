(() => {
  'use strict';
  const root = document.querySelector('#comments');
  if (!root) return;
  const form = root.querySelector('form');
  const list = root.querySelector('.wall-list');
  const status = root.querySelector('#wall-status');
  const submit = root.querySelector('[type=submit]');
  const file = form.elements.avatar;
  const preview = root.querySelector('#wall-preview');
  const defaultAvatar = root.querySelector('#wall-default-preview');
  const removeAvatar = root.querySelector('#wall-remove-avatar');
  const loadMore = root.querySelector('#wall-more');
  const codeImage = root.querySelector('#wall-code-image');
  const codeAudio = root.querySelector('#wall-code-audio');
  const refresh = root.querySelector('#wall-refresh-code');
  const api = new URL('comments/api.php', document.baseURI);
  let challenge = null, nextBefore = null, posting = false, challengeRequest = 0;
  const commentSizes = new ResizeObserver(entries => {
    for (const {target:body} of entries) {
      const button=body.nextElementSibling;
      button.hidden=!body.classList.contains('wall-body-expanded') && body.scrollHeight<=body.clientHeight+1;
    }
  });
  let deletions = {};
  try { deletions = JSON.parse(localStorage.getItem('gayboy-wall-deletions') || '{}'); } catch {}
  if (!deletions || typeof deletions !== 'object' || Array.isArray(deletions)) deletions = {};
  try { form.elements.name.value = localStorage.getItem('gayboy-wall-name') || ''; } catch {}
  function url(action, params={}) {
    const value = new URL(api);
    value.searchParams.set('action', action);
    Object.entries(params).forEach(([key,item]) => value.searchParams.set(key, item));
    return value.href;
  }
  function tell(message, error=false) {
    status.textContent = message; status.classList.toggle('wall-error', error);
  }
  async function request(action, options={}, params={}) {
    const response = await fetch(url(action, params), {credentials:'same-origin', cache:'no-store', ...options});
    let data;
    try { data = await response.json(); } catch { throw new Error('The wall is unavailable right now. Please try again.'); }
    if (!response.ok) throw new Error(data.error || 'That request could not be completed.');
    return data;
  }
  async function newChallenge() {
    const generation = ++challengeRequest;
    challenge = null; submit.disabled = true; refresh.disabled = true;
    codeAudio.pause(); codeAudio.removeAttribute('src'); codeImage.hidden = true;
    form.elements.human_code.value = '';
    try {
      const data = await request('challenge');
      if (generation !== challengeRequest) return;
      challenge = data;
      codeImage.src = url('image', {nonce:data.nonce}); codeImage.hidden = false;
      codeAudio.src = url('audio', {nonce:data.nonce});
    } finally {
      if (generation === challengeRequest) {
        refresh.disabled = false; submit.disabled = !challenge || posting;
      }
    }
  }
  function clearThumbnail() {
    file.value = ''; preview.hidden = true; defaultAvatar.hidden = false; removeAvatar.hidden = true;
  }
  file.addEventListener('change', async () => {
    const image = file.files[0];
    if (!image) { clearThumbnail(); return; }
    if (!['image/png','image/jpeg','image/webp'].includes(image.type) || image.size > 2097152) {
      clearThumbnail(); tell('Choose a PNG, JPEG or WebP smaller than 2 MB.', true); return;
    }
    try {
      if (!window.createImageBitmap) return;
      const bitmap = await createImageBitmap(image);
      if (bitmap.width > 2048 || bitmap.height > 2048) {
        bitmap.close(); clearThumbnail(); tell('Use a thumbnail up to 2048 × 2048 pixels.', true); return;
      }
      if (file.files[0] !== image) { bitmap.close(); return; }
      const crop = Math.min(bitmap.width, bitmap.height);
      preview.getContext('2d').drawImage(bitmap, (bitmap.width-crop)/2, (bitmap.height-crop)/2, crop,crop, 0,0,96,96);
      bitmap.close(); preview.hidden = false; defaultAvatar.hidden = true; removeAvatar.hidden = false;
      tell('Thumbnail ready. It will be cropped to a square with your comment.');
    } catch { clearThumbnail(); tell('That image could not be read. Try another thumbnail.', true); }
  });
  removeAvatar.addEventListener('click', clearThumbnail);
  function commentRow(comment) {
    const article = document.createElement('article');
    article.className = 'wall-comment'; article.dataset.commentId = String(comment.id);
    const profile = document.createElement('div'); profile.className = 'wall-profile';
    const name = document.createElement('strong'); name.textContent = comment.name;
    const avatar = document.createElement('img'); avatar.width = 96; avatar.height = 96;
    avatar.alt = comment.has_avatar ? `${comment.name}'s profile thumbnail` : 'Default Game Boy profile picture';
    avatar.loading = 'lazy'; avatar.src = comment.has_avatar ? url('avatar',{id:comment.id}) : 'comments/default-avatar.svg';
    profile.append(name, avatar);
    const content = document.createElement('div'); content.className = 'wall-message';
    const date = document.createElement('time'); date.dateTime = new Date(comment.created_at*1000).toISOString();
    date.textContent = new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(comment.created_at*1000));
    const body = document.createElement('p'); body.textContent = comment.body;
    body.className='wall-body';body.id='wall-comment-body-'+comment.id;
    const expand=document.createElement('button');expand.type='button';expand.className='wall-expand';expand.hidden=true;
    expand.textContent='▾ read more';expand.setAttribute('aria-expanded','false');expand.setAttribute('aria-controls',body.id);
    expand.addEventListener('click',()=>{
      const expanded=body.classList.toggle('wall-body-expanded');
      expand.textContent=expanded?'▴ show less':'▾ read more';expand.setAttribute('aria-expanded',String(expanded));
    });
    content.append(date, body, expand);commentSizes.observe(body);
    if (typeof deletions[comment.id] === 'string') {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'wall-delete';
      button.textContent = 'delete my comment';
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          if (!challenge) await newChallenge();
          const data = new FormData(); data.set('csrf',challenge.csrf); data.set('id',comment.id);
          data.set('delete_token',deletions[comment.id]);
          await request('delete',{method:'POST',body:data});
          delete deletions[comment.id];
          try { localStorage.setItem('gayboy-wall-deletions',JSON.stringify(deletions)); } catch {}
          await loadComments(); tell('Your comment has been removed.');
        } catch (error) { tell(error.message,true); button.disabled = false; }
      });
      content.append(button);
    }
    article.append(profile, content); return article;
  }
  async function loadComments(append=false) {
    loadMore.disabled = true;
    try {
      const data = await request('list',{},append && nextBefore ? {before:nextBefore} : {});
      if (!append) { commentSizes.disconnect();list.replaceChildren(); }
      data.comments.forEach(comment => list.append(commentRow(comment)));
      if (!data.total) {
        const empty = document.createElement('p'); empty.className = 'wall-empty';
        empty.textContent = 'No comments yet. Be the first to leave a little love ♥'; list.append(empty);
      }
      root.querySelector('#wall-count').textContent = `(${data.total})`;
      nextBefore = data.next_before; loadMore.hidden = !nextBefore;
    } finally { loadMore.disabled = false; }
  }
  loadMore.addEventListener('click', () => loadComments(true).catch(error => tell(error.message,true)));
  refresh.addEventListener('click', () => newChallenge().catch(error => tell(error.message,true)));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (posting || !challenge || !form.reportValidity()) return;
    posting = true; submit.disabled = true; tell('Posting your comment…');
    const data = new FormData(form); data.set('csrf',challenge.csrf); data.set('nonce',challenge.nonce);
    try {
      const result = await request('post',{method:'POST',body:data});
      deletions[result.id] = result.delete_token;
      try {
        localStorage.setItem('gayboy-wall-deletions',JSON.stringify(deletions));
        localStorage.setItem('gayboy-wall-name',form.elements.name.value);
      } catch {}
      form.elements.body.value = ''; clearThumbnail();
      await loadComments(); tell('Submitted! Your comment will appear after the site owner approves it.');
    } catch (error) { tell(error.message,true); }
    finally {
      posting = false;
      try { await newChallenge(); } catch { tell('Get a new human-check code before posting again.',true); }
    }
  });
  Promise.allSettled([loadComments(),newChallenge()]).then(results => {
    const failure = results.find(result => result.status === 'rejected');
    if (failure) tell(failure.reason.message,true);
  });
})();
