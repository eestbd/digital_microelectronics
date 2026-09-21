@echo off
REM 결과 CSV가 step1 폴더에 저장되도록 작업 폴더를 맞춘다.
cd /d "%~dp0"
REM 상위 폴더에 있는 프로젝트 전용 Conda 환경의 프로그램과 라이브러리를 사용한다.
set "PATH=%~dp0..\.conda;%~dp0..\.conda\Scripts;%~dp0..\.conda\Library\bin;%PATH%"
REM 간이 모델의 배열 연산 예제와 Id-Vg 계산을 실행한다.
"%~dp0..\.conda\python.exe" simulator_practice.py
REM 출력된 계산 결과를 읽을 수 있도록 키 입력을 기다린다.
pause
