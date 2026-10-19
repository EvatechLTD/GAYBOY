/* Real SameBoy cable: no writes to SB, SC, IF or the ROM's receive queue. */
const fs=require('fs'),assert=require('assert');
(async()=>{
 const core=await require('../build/sync_link_core.cjs')();
 const arg=process.argv.indexOf('--rom'),romPath=arg<0?'build/GAYBOY.gb':process.argv[arg+1];
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return [a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),ptr=core._malloc(rom.length);core.HEAPU8.set(rom,ptr);core._link_init(ptr,rom.length);core._free(ptr);
 core._link_watch_rx(S['_rx']);
 let frames=0;const run=n=>{core._link_run(n);frames+=n;};
 const v=(i,n)=>core._link_read(i,S['_'+n]);
 const word=(i,n)=>v(i,n)|(core._link_read(i,S['_'+n]+1)<<8);
 const put=(i,n,x)=>core._link_write(i,S['_'+n],x);
 const until=(fn,max=3000)=>{for(let n=0;n<max;n++){if(fn())return n;run(1);}throw Error('Timed out at frame '+frames+' '+JSON.stringify([0,1].map(i=>({pc:core._link_pc(i).toString(16),bank:core._link_read(i,0xff90),servicing:v(i,'seqservicing'),armed:v(i,'syncarmed'),sub:v(i,'syncsub'),drops:word(i,'mixunderruns'),ticks:word(i,'seqticks'),pad:v(i,'lastpad'),slot:core._link_state_read(i,S['_mx']+1),pending:core._link_state_read(i,S['_mx']+2),error:core._link_state_read(i,S['_mx']+52),pair:v(i,'link_pair_phase'),hold:v(i,'link_pair_hold'),linked:v(i,'linkstate'),txread:v(i,'linktxread'),txsize:v(i,'linktxsize'),txtype:core._link_state_read(i,S['_linktx']+2),names:core._link_state_read(i,S['_linkmirror']+150),rxready:v(i,'link_rx_ready'),namesDirty:v(i,'link_names_dirty')}))));};
 const key={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function press(i,k,limit=180){const mask=1<<key[k];core._link_key(i,key[k],1);until(()=>v(i,'lastpad')&mask,limit);core._link_key(i,key[k],0);until(()=>!(v(i,'lastpad')&mask),limit);run(4);}
 function choose(i,page){press(i,'start');until(()=>v(i,'navopen'),180);const category=[19,20,24,25].includes(page)?4:page===0?3:0;for(let n=0;n<5&&v(i,'navcategory')!==category;n++)press(i,'right');for(let n=0;n<40&&v(i,'navchoice')!==page;n++)press(i,'down');assert.equal(v(i,'navchoice'),page);press(i,'a');until(()=>!v(i,'navopen'),180);run(35);assert.equal(v(i,'page'),page);}
 until(()=>v(0,'introready')&&v(1,'introready'));
 core._link_key(0,7,1);core._link_key(1,7,1);until(()=>[0,1].every(i=>!v(i,'introactive')&&v(i,'page')===8));core._link_key(0,7,0);core._link_key(1,7,0);run(60);

 const st=(i,a)=>core._link_state_read(i,a),sw=(i,a,x)=>core._link_state_write(i,a,x);
 const mx=S['_mx'];const m=(i,n)=>st(i,mx+n);const setm=(i,n,x)=>sw(i,mx+n,x);
 const bpmArg=process.argv.indexOf('--bpm'),bpm=bpmArg<0?300:Number(process.argv[bpmArg+1]);
 const writeWord=(i,a,x)=>{sw(i,a,x&255);sw(i,a+1,x>>8);};
 for(const i of [0,1]){
  const tracks=Array.from({length:7},()=>[]);for(let s=0;s<16;s++){tracks[0].push([s,61+s%4,100,1]);tracks[1].push([s,68+s%4,100,1]);if(s%4===0)for(const sample of [4,10])tracks[6].push([s,sample,127,4]);}
  let offset=0;for(let c=0;c<7;c++){writeWord(i,S['_seqeventoffsets']+c*2,offset);writeWord(i,S['_seqeventcounts']+c*2,tracks[c].length);writeWord(i,S['_seqlength']+c*2,16);for(const e of tracks[c]){for(let j=0;j<4;j++)sw(i,S['_seqevents_lo']+offset*4+j,e[j]);offset++;}}
  sw(i,S['_seqeventcache'],0);sw(i,S['_pattern_dirty'],1);writeWord(i,S['_seqbpm'],bpm);writeWord(i,S['_seqglobalbpm'],bpm);writeWord(i,S['_seqcachedbpm'],0);sw(i,0xACCF,0x43);
  const name=Buffer.from('PAIRED LIVE TEST\0');for(let j=0;j<17;j++)setm(i,26+j,name[j]||0);
  choose(i,20);setm(i,6,0);press(i,'b');
  for(let slot=1;slot<8;slot++){choose(i,18);setm(i,4,30+slot);press(i,'a');choose(i,19);setm(i,6,0);press(i,'a');}
  choose(i,18);assert.equal(m(i,1),7);
 }
 if(process.argv.includes('--storage')){choose(1,25);setm(1,6,0);press(1,'b',1800);choose(1,18);}
 choose(0,27);press(0,'a');until(()=>v(1,'seqplaying'),600);
 until(()=>v(0,'linkstate')===2&&v(1,'linkstate')===2,1800);
 until(()=>st(0,S['_linkmirror']+150)===255,Math.max(1800,Math.ceil(240000/bpm)));
 choose(0,18);put(0,'linkpair',!v(0,'linkpair'));assert(v(0,'linkpair'));
 setm(0,4,30);press(0,'a');assert(v(0,'link_pair_phase'));
 const tx=S['_linktx'];let corrupted=0;
 function crc(c,b){for(let bit=0;bit<7;bit++){const top=(c^b)&64;c=(c<<1)&127;if(top)c^=9;b<<=1;}return c;}
 for(let n=0;n<2100&&v(0,'link_pair_phase');n++){
  const size=v(1,'linktxsize');if(st(1,tx+2)===9&&v(1,'linktxread')<size-1){let c=0;for(let j=1;j<size-1;j++)c=crc(c,st(1,tx+j));sw(1,tx+size-1,c^1);corrupted++;}
  run(1);
 }
 assert(corrupted,'No READY packet was faulted');assert(!v(0,'link_pair_phase'),'Pair did not time out');
 assert.equal(m(0,1),7);assert.equal(m(1,1),7);assert(v(1,'link_pair_hold'),'No abandoned prepared-pair window was exercised');
 // Real timeout cancels the master; the peer expires later, since PREPARE
 // took time to arrive. An ordinary F2 during this window must not commit it.
 put(0,'linkpair',0);setm(0,3,0);setm(0,4,37);const markers=core._link_rx_count(0xF2);press(0,'a');
 until(()=>core._link_rx_count(0xF2)>markers,180);assert(v(1,'link_pair_hold'),'Marker missed the abandoned-pair window');
 run(180);assert.equal(m(1,1),7,'Unpaired marker committed an abandoned pair');
 assert(v(0,'seqplaying')&&v(1,'seqplaying'));assert(!v(0,'overflow')&&!v(1,'overflow'));
 assert.equal(core._link_wire_aborts(),0);
 console.log('PASS lost READY timeout and unrelated later marker cannot commit abandoned pair');
})().catch(e=>{console.error(e);process.exitCode=1;});
