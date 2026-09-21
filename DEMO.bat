@echo off
REM 배치 파일이 있는 프로젝트 폴더를 기준으로 데모를 실행한다.
cd /d "%~dp0"
REM 프로젝트의 Conda 환경에서 실행 파일과 수치 계산용 라이브러리를 찾게 한다.
set "PATH=%~dp0.conda;%~dp0.conda\Scripts;%~dp0.conda\Library\bin;%PATH%"
REM 같은 환경의 파이썬으로 Streamlit을 실행하고 데모 로더를 연다.
"%~dp0.conda\python.exe" -m streamlit run "%~dp0demo\_launcher.py"
REM 오류가 발생했을 때만 창을 남겨 메시지를 확인할 수 있게 한다.
if errorlevel 1 pause
