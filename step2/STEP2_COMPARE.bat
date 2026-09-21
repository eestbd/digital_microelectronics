@echo off
REM 비교 결과를 step2 폴더에 저장하도록 작업 폴더를 맞춘다.
cd /d "%~dp0"
REM 프로젝트의 파이썬 환경과 DEVSIM에 필요한 라이브러리 경로를 사용한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM config.yaml의 compare 항목에 적힌 소자들을 같은 Id-Vg 조건으로 비교한다.
"%~dp0..\.conda\python.exe" compare_tcad.py
REM 소자별 전류 요약과 오류 메시지를 읽을 수 있도록 창을 유지한다.
pause
