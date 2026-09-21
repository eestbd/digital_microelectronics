@echo off
REM 설정 파일을 읽고 결과를 저장할 기준 폴더를 step2로 맞춘다.
cd /d "%~dp0"
REM DEVSIM이 필요한 라이브러리를 프로젝트의 Conda 환경에서 찾게 한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 기본 실행은 Id-Vg다. 마지막 인자를 idvd나 cv로 바꾸면 해당 해석을 실행한다.
"%~dp0..\.conda\python.exe" mosfet.py idvg
REM 계산 결과나 수렴 오류 메시지를 확인할 수 있도록 기다린다.
pause
