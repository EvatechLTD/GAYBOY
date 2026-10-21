"""Package the current ROM and matching tutorial map for both sites."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('package_web_rom.py')),run_name='__main__')
