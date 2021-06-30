call _get_env.bat
call conda activate %env%
call conda env update --file environment.yml
timeout /t 90