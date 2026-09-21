@echo off
REM 추가한 모델 비교 스크립트를 step2 폴더에서 실행한다.
cd /d "%~dp0"
REM 간이 모델과 DEVSIM을 같은 파이썬 환경에서 불러오도록 경로를 맞춘다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 같은 전압 조건의 두 모델을 계산하고 CSV와 일반 축 및 로그 축 그래프를 저장한다.
"%~dp0..\.conda\python.exe" compare_models.py
REM 계산이 끝난 뒤에도 터미널의 비교 표나 오류 내용을 확인할 수 있게 한다.
pause
