"""PK settings follow saved patterns and survive battery reboot."""
from pathlib import Path
source=Path('tools/test_pattern_tones.py').read_text()
source=source.replace("'noisepatch':10,", "'noisepatch':10,'pulsekickpatch':8,")
source=source.replace('expected=read();save(0);', "setbytes('pulsekickpatch',[8,35,1,4,2,3,12,0]);expected=read();save(0);")
source=source.replace("setbytes('param',[0]*104);setbytes('customwave'", "setbytes('pulsekickpatch',[0]*8);setbytes('param',[0]*104);setbytes('customwave'")
exec(source)
print('PASS: all eight PK settings persist across pattern save/load and battery reboot')
