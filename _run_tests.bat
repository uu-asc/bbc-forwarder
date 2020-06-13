@echo off
call _get_env.bat
call conda activate %env%
python -m unittest
pause
