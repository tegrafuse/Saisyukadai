@echo off
REM set_remote.bat
REM Usage: set_remote.bat REMOTE_URL

IF "%~1"=="" (
  echo Usage: set_remote.bat REMOTE_URL
  goto :EOF
)

git remote remove origin 2>nul
git remote add origin %~1
echo Remote "origin" set to %~1
pause