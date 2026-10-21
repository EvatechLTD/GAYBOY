"""Ensure navigating does not invalidate sound data, while edits still persist."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output');ap.add_argument('--baseline',action='store_true');args=ap.parse_args()
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
prefix=prefix.replace("Path('build/GAYBOY.noi')","Path(args.rom).with_suffix('.noi')").replace("'build/GAYBOY.gb',",'args.rom,')
exec(prefix)
try:
 enter_app(p,S);menu(28);put('seqhead',0);p.tick(100)
 changes=[];saves=[]
 for sym,dst in (('mixer_pattern_changed',changes),('sparse_snapshot',saves)):
  ptr=S['_'+sym];p.hook_register(ptr>>16,ptr&65535,lambda dst:dst.append(p._cycles()),dst)
 before=v('pattern_generation')|v('pattern_generation',1)<<8
 for key in ('right','up','left','down','right','left'):press(key)
 p.tick(80)
 report={'navigation_sound_invalidations':len(changes),'navigation_saves':len(saves),'navigation_generation_delta':((v('pattern_generation')|v('pattern_generation',1)<<8)-before)&65535}
 if not args.baseline:assert not changes and not saves,report
 changes.clear();saves.clear();press('b');p.tick(100)
 assert sum(v('seqeventcounts',i) for i in range(14))>0
 assert changes and saves,'Note edit must still be saved'
 report['note_edit_saved']=True
 menu(11);row(0,4);put('eval_col',0);adjust('up');assert v('finepitch')==1
 assert changes and saves
 print(json.dumps(report,indent=2))
 if args.output:Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
finally:p.stop(save=False)
