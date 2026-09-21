# 제공된 데모의 컴파일된 코드를 Streamlit에서 실행하는 로더다.
# 실제 데모 구현은 같은 폴더의 pyc 파일에 들어 있다.
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 데모가 같은 폴더의 모듈을 불러올 수 있도록 경로를 등록한다.
# Streamlit 재실행 때 이미 등록된 경로가 중복해서 쌓이지 않게 확인한다.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# 일반 import는 이미 불러온 모듈을 재사용하므로 화면 구성 코드가 매번 실행되지 않는다.
# runpy로 주 프로그램처럼 실행하면 Streamlit 재실행 때도 화면을 다시 만들 수 있다.
runpy.run_path(str(HERE / "demo_app.pyc"), run_name="__main__")
