"""32 KiB projects expose no pattern/song file dialogs or stale shortcuts."""
from pathlib import Path
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
blocked={19,20,24,25}

def protected():
    return [bytes(p.memory[1+i//4,0xa000+(i%4)*2048+480:0xa000+(i%4)*2048+1792]) for i in range(5)]

try:
    enter_app(p,symbols);put('sticky_start',1);before=protected()
    # Old save files may have pinned these actions. Reject and remove those
    # shortcuts without migrating or reformatting the user's pattern records.
    for i,v in enumerate([19,20,24,25]):put('pool_root',v,100+i)
    put('pool_root',ord('P'),108);put('pool_root',1,109)
    tap('start')
    for category in range(5):
        assert get('navcategory')==category
        for _ in range(36):
            assert get('navchoice') not in blocked,(category,get('navchoice'))
            tap('down')
        tap('right')
    assert all(get('pool_root',100+i)==255 for i in range(4))
    for _ in range(32):
        if get('navchoice')==54:break
        tap('down')
    assert get('navchoice')==54;tap('a');assert get('page')==29
    tap('start')
    for _ in range(4):tap('right')
    for _ in range(12):
        assert get('navchoice') not in blocked
        tap('down')
    tap('select');assert get('page')==29
    assert protected()==before,'Menu changes touched resident notes or arrangement'
    assert rom.read_bytes()[0x149]==3
    print('PASS five-pad/one-song 32 KiB project, removed dialogs and stale shortcuts, song/notes intact')
finally:p.stop(save=False)
