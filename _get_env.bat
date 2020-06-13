@echo off
for /F "tokens=2 delims=:" %%a in ('findstr "name" environment.yml') do set env=%%a
set env=%env: =%
echo Setting environment variable to "%env%"