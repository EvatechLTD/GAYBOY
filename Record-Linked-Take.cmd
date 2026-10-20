@echo off
setlocal
pushd "%~dp0"
python tools\start_linked_take.py
if errorlevel 1 (
  echo.
  pause
)
popd
endlocal
