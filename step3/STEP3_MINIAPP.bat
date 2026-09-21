@echo off
REM 배치 파일이 있는 step3 폴더에서 앱을 시작한다.
cd /d "%~dp0"
REM 프로젝트 전용 파이썬과 화면 구성 패키지가 설치된 환경을 사용한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 간이 MOSFET 모델을 사용하는 비교 화면을 Streamlit 서버로 실행한다.
"%~dp0..\.conda\python.exe" -m streamlit run "%~dp0mini_app.py"
REM 정상 종료 때는 닫고 오류가 있을 때만 메시지를 확인하도록 기다린다.
if errorlevel 1 pause
