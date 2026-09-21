@echo off
REM 실행 위치와 관계없이 step3 폴더의 앱 파일을 사용한다.
cd /d "%~dp0"
REM 앱 파일이 없으면 서버를 시작하지 않고 오류 메시지를 보여 준다.
if not exist "%~dp0my_app.py" (
  echo [MY_APP] my_app.py not found. Copy mini_app.py to my_app.py first.
  pause
  exit /b 1
)
REM 프로젝트의 Conda 환경과 DEVSIM에 필요한 라이브러리 경로를 등록한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 두 DEVSIM 소자의 전류와 정전용량을 비교하는 앱을 실행한다.
"%~dp0..\.conda\python.exe" -m streamlit run "%~dp0my_app.py"
REM 서버가 오류로 종료되면 창을 남겨 오류 내용을 확인할 수 있게 한다.
if errorlevel 1 pause
