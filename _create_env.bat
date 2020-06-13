@echo off
call _get_env.bat
echo Creating conda environment "%env%" from yaml
call conda env create -f environment.yml
call conda activate %env%
call python -m ipykernel install --user --name %env% --display-name "%env%"
pause
