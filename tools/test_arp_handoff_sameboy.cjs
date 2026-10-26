/* SameBoy 1.0.4: actual saved project, real buttons, APU writes, graphics running. */
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const opt=(n,d)=>{const i=process.argv.indexOf(n);return i<0?d:process.argv[i+1];};
 const romPath=opt('--rom','build/GAYBOY.gb'),savePath=opt('--save','assets/demo/KILLING.srm');
 const core=await require(path.resolve(opt('--core','build/sync_link_core.cjs')))();
 const S=Object.fromEntries(fs.readFileSync(romPath.replace(/\.gb$/,'.noi'),'utf8').split(/\r?\n/).filter(l=>l.startsWith('DEF ')).map(l=>{const a=l.split(/\s+/);return[a[1],parseInt(a[2],16)];}));
 const rom=fs.readFileSync(romPath),rp=core._malloc(rom.length);core.HEAPU8.set(rom,rp);core._link_init(rp,rom.length);core._free(rp);core._link_set_connected(0);
 const save=Buffer.from(fs.readFileSync(savePath));save[32647]=Number(opt('--pad','5'))-1;
 for(let side=0;side<2;side++){const p=core._malloc(save.length);core.HEAPU8.set(save,p);core._link_battery_load(side,p,save.length);core._free(p);}
 const v=(n,i=0)=>core._link_state_read(0,S['_'+n]+i),word=(n,i=0)=>v(n,i)|(v(n,i+1)<<8),run=n=>core._link_run(n);
 function until(f){for(let j=0;j<3000;j++){if(f())return;run(1);}throw Error('input/boot timeout');}
 const keys={right:0,left:1,up:2,down:3,a:4,b:5,select:6,start:7};
 function key(k,d){core._link_key(0,keys[k],+d);until(()=>!!(v('lastpad')&(1<<keys[k]))===d);}
 until(()=>v('introready'));key('start',true);until(()=>!v('introactive')&&v('page')===8);key('start',false);run(60);
 const config={bpm:word('seqbpm'),counts:Array.from({length:7},(_,i)=>word('seqeventcounts',i*2)),length:word('seqlength',2)};
 core._link_watch_events(0,0,S._seqposition,S._seqticks,S._seqclock);
 key('select',true);key('a',true);key('a',false);key('select',false);assert(v('seqplaying'));run(Number(opt('--frames','3000')));
 const raw=new Uint32Array(core.HEAPU8.buffer,core._link_events(),core._link_event_count()*7),lanes=[[],[],[],[]];
 for(let i=0;i<raw.length;i+=7)if(raw[i+1]===0&&raw[i+2]>=0x740&&raw[i+2]<=0x743)lanes[raw[i+2]-0x740].push({cycle:raw[i],position:(raw[i+4]>>8)&255});
 const ideal=15000/config.bpm,channels=lanes.map(hits=>{const gaps=hits.slice(1).map((h,i)=>(h.cycle-hits[i].cycle)/8388.608);return{hits:hits.length,minMs:Math.min(...gaps),maxMs:Math.max(...gaps),startupErrorMs:gaps[0]-ideal,steadyMaxGridErrorMs:Math.max(0,...gaps.slice(1).map(g=>Math.abs(g-Math.round(g/ideal)*ideal))),gaps};});
 const report={core:'SameBoy 1.0.4',rom:romPath,save:savePath,config,idealMs:ideal,channels};
 fs.writeFileSync(opt('--output','build/arp-handoff-sameboy.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({...report,channels:channels.map(({gaps,...c})=>c)},null,2));
 assert(channels[1].hits>100);if(process.argv.includes('--verify')){assert(channels[1].maxMs<ideal+3);assert(channels[1].steadyMaxGridErrorMs<3);}
 key('select',true);key('a',true);key('a',false);key('select',false);assert(!v('seqplaying'));console.log('PASS real transport stop');
})().catch(e=>{console.error(e);process.exitCode=1;});
