import {esc,url} from './core.js';

// Provider URLs are constructed here, never pasted into executable HTML.
export function mediaInfo(input){
    let value=String(input||'').trim();
    if(value.includes('<iframe')){const doc=new DOMParser().parseFromString(value,'text/html');value=doc.querySelector('iframe')?.getAttribute('src')||'';}
    if(value.startsWith('//'))value='https:'+value;
    if(value.startsWith('spotify:'))value='https://open.spotify.com/'+value.slice(8).replace(':','/');
    let u;try{u=new URL(value);}catch{return {error:'Paste a song, playlist, video URL, or a provider’s iframe embed code.'};}
    if(u.protocol!=='https:')return {error:'Use an HTTPS media URL.'};
    const host=u.hostname.toLowerCase(),path=u.pathname;
    if(['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be','www.youtube-nocookie.com'].includes(host)){
        const id=host==='youtu.be'?path.split('/')[1]:u.searchParams.get('v')||path.match(/^\/(?:embed|shorts|live)\/([\w-]{11})/)?.[1];const list=u.searchParams.get('list');let src='';
        if(id&&/^[\w-]{11}$/.test(id))src='https://www.youtube-nocookie.com/embed/'+id;
        else if(list&&/^[\w-]{8,100}$/.test(list))src='https://www.youtube-nocookie.com/embed/videoseries';
        else return {error:'Use a YouTube video or playlist link.'};
        const q=new URLSearchParams({rel:'0',playsinline:'1'});if(list&&/^[\w-]{8,100}$/.test(list))q.set('list',list);const start=u.searchParams.get('t')||u.searchParams.get('start');if(start){const m=start.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);if(m)q.set('start',String((+m[1]||0)*3600+(+m[2]||0)*60+(+m[3]||0)));}
        return {provider:'YouTube',src:src+'?'+q,kind:'iframe',height:360};
    }
    if(['soundcloud.com','www.soundcloud.com','api.soundcloud.com','w.soundcloud.com','on.soundcloud.com'].includes(host)){
        const track=host==='w.soundcloud.com'?u.searchParams.get('url'):u.href;if(!track)return {error:'Paste a SoundCloud track or playlist link.'};
        return {provider:'SoundCloud',src:'https://w.soundcloud.com/player/?'+new URLSearchParams({url:track,auto_play:'false',visual:'true',show_comments:'false',hide_related:'true'}),kind:'iframe',height:300};
    }
    if(host==='open.spotify.com'){
        const m=path.match(/\/(?:intl-[a-z]+\/)?(?:embed\/)?(track|album|playlist|episode|show|artist)\/([a-zA-Z0-9]+)/);if(!m)return {error:'Use a Spotify track, album, playlist, artist, show, or episode link.'};
        return {provider:'Spotify',src:`https://open.spotify.com/embed/${m[1]}/${m[2]}?utm_source=generator`,kind:'iframe',height:m[1]==='track'?152:352};
    }
    if(['vimeo.com','www.vimeo.com','player.vimeo.com'].includes(host)){
        const id=path.match(/(?:^|\/)(\d+)(?:\/|$)/)?.[1];if(!id)return {error:'Use a Vimeo video URL.'};const h=u.searchParams.get('h')||path.match(/\d+\/([a-f0-9]+)/)?.[1];return {provider:'Vimeo',src:'https://player.vimeo.com/video/'+id+(h?'?h='+encodeURIComponent(h):''),kind:'iframe',height:360};
    }
    if(['mixcloud.com','www.mixcloud.com','player-widget.mixcloud.com'].includes(host)){
        const feed=u.searchParams.get('feed')||(host.includes('widget')?'':u.pathname);if(!feed)return {error:'Use a Mixcloud show or playlist link.'};return {provider:'Mixcloud',src:'https://www.mixcloud.com/widget/iframe/?'+new URLSearchParams({feed,hide_cover:'0',light:'1'}),kind:'iframe',height:180};
    }
    if(host==='bandcamp.com'&&path.startsWith('/EmbeddedPlayer/')&&/\/(?:album|track)=\d+/.test(path))return {provider:'Bandcamp',src:u.href,kind:'iframe',height:400};
    if(host.endsWith('.bandcamp.com'))return {error:'On Bandcamp choose Share/Embed → embed this album, then paste the embed code here.'};
    if(['twitch.tv','www.twitch.tv','player.twitch.tv','clips.twitch.tv'].includes(host)){
        const q=new URLSearchParams({parent:location.hostname,autoplay:'false'});if(host==='clips.twitch.tv'){q.set('clip',path.split('/').filter(Boolean)[0]||'');return {provider:'Twitch clip',src:'https://clips.twitch.tv/embed?'+q,kind:'iframe',height:360};}
        const video=path.match(/\/videos\/(\d+)/)?.[1]||u.searchParams.get('video');if(video)q.set('video','v'+video.replace(/^v/,''));else q.set('channel',u.searchParams.get('channel')||path.split('/').filter(Boolean)[0]||'');return {provider:'Twitch',src:'https://player.twitch.tv/?'+q,kind:'iframe',height:360};
    }
    if(/\.(mp3|wav|ogg|m4a|aac|flac)(?:$|\?)/i.test(u.href))return {provider:'Audio',src:u.href,kind:'audio',height:80};
    if(/\.(mp4|webm|ogv|mov)(?:$|\?)/i.test(u.href))return {provider:'Video',src:u.href,kind:'video',height:360};
    return {error:'That service does not have a supported player yet. Use YouTube, SoundCloud, Spotify, Vimeo, Mixcloud, Twitch, a Bandcamp embed, or a direct audio/video file.'};
}
export function mediaHTML(value,compact=false){
    const m=mediaInfo(value);if(m.error)return `<div class="media-error" role="status">${esc(m.error)}</div>`;
    if(m.kind==='audio')return `<div class="media-player"><audio controls preload="none" src="${esc(m.src)}"></audio><small>Press play to start your soundtrack.</small></div>`;
    if(m.kind==='video')return `<div class="media-player"><video controls playsinline preload="metadata" src="${esc(m.src)}"></video></div>`;
    return `<div class="media-player"><iframe title="${esc(m.provider)} player" src="${esc(m.src)}" style="height:${compact?Math.min(m.height,200):m.height}px" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" loading="lazy" allowfullscreen></iframe><small>${esc(m.provider)} · playback follows the creator’s availability and provider rules.</small></div>`;
}
