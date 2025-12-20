@echo off
REM commit_and_push.bat
REM Usage: commit_and_push.bat "commit message" [branch]

SETLOCAL EnableDelayedExpansion

IF "%~1"=="" (
  SET /P MSG=Commit message: 
) ELSE (
  SET MSG=%~1
)

IF "%~2"=="" (
  SET BRANCH=main
) ELSE (
  SET BRANCH=%~2
)

echo Staging changes...
git add -A

echo Committing with message: "%MSG%"
git commit -m "%MSG%"
IF ERRORLEVEL 1 (
  echo No changes to commit or commit failed.
  goto :END
)

echo Pushing to origin/%BRANCH%...
git push origin %BRANCH%

:END
ENDLOCAL
pause