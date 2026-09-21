@echo off
REM 결과 파일의 저장 위치를 이 배치 파일이 있는 step1 폴더로 맞춘다.
cd /d "%~dp0"
REM 프로젝트 전용 환경의 파이썬과 수치 계산용 라이브러리를 사용한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 문턱 전압이 다른 세 소자의 Id-Vd 비교를 실행한다.
"%~dp0..\.conda\python.exe" compare.py
REM 결과나 오류 메시지를 확인할 수 있도록 창을 유지한다.
pause
