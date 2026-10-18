import {esc} from './core.js';
export const emoticons=[['uWu','uwu'],['OwO','😳'],[':)', '🙂'],[':D','😄'],[';)','😉'],[':P','😛'],[':(','🙁'],[":'(",'😢'],['<3','❤️'],['</3','💔']];
const expressions={':)':'🙂',':-)':'🙂',':d':'😄',':-d':'😄',';)':'😉',';-)':'😉',':p':'😛',':-p':'😛',':(':'🙁',':-(':'🙁',":'(":'😢','<3':'❤️','</3':'💔','owo':'😳'};
export function messageHTML(text){
    const source=String(text||''),pattern=/(?<![\w])(?:\buwu\b|:uwu:|\bowo\b|:-?\)|:-?d|;-?\)|:-?p|:-?\(|:'\(|<\/3|<3)(?![\w])/gi;let html='',last=0;
    for(const m of source.matchAll(pattern)){html+=esc(source.slice(last,m.index));const key=m[0].toLowerCase();html+=key==='uwu'||key===':uwu:'?'<img class="chat-emoji" src="emoji/uwu.png" alt="uWu" title="uWu — scene kid" draggable="false">':`<span class="text-emoji" role="img" aria-label="${esc(m[0])}" title="${esc(m[0])}">${expressions[key]||esc(m[0])}</span>`;last=m.index+m[0].length;}
    return html+esc(source.slice(last));
}
export function pickerHTML(target){return `<details class="emoji-picker"><summary><img src="emoji/uwu.png" alt=""> EMOTICONS</summary><div>${emoticons.map(([code,icon])=>`<button type="button" data-insert-emoji="${esc(code)}" data-emoji-target="${esc(target)}" title="${esc(code)}">${icon==='uwu'?'<img src="emoji/uwu.png" alt="uWu">':icon}<small>${esc(code)}</small></button>`).join('')}</div></details>`;}
export function installEmojiPicker(){document.addEventListener('click',e=>{const button=e.target.closest('[data-insert-emoji]');if(!button)return;const input=document.querySelector(button.dataset.emojiTarget);if(!input)return;const start=input.selectionStart??input.value.length,end=input.selectionEnd??start;const value=button.dataset.insertEmoji;input.setRangeText((start&&input.value[start-1]!==' '?' ':'')+value+' ',start,end,'end');input.focus();input.dispatchEvent(new Event('input',{bubbles:true}));});}
