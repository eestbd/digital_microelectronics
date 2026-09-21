# -*- coding: utf-8 -*-
"""명령줄에서 해석 종류와 설정 파일을 받아 DEVSIM 계산을 실행한다.

python mosfet.py 뒤에 idvg, idvd, cv 중 하나를 적으면 해당 해석을 실행한다.
해석 종류를 생략하거나 STEP2_RUN.bat으로 실행하면 Id-Vg를 계산한다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mosfet_tool.config import Device, load_config
from mosfet_tool.workflows import run_cv, run_idvd, run_idvg, save_csv

# 실행한 폴더가 달라도 기본 설정 파일은 이 스크립트와 같은 폴더에서 찾는다.
ROOT = Path(__file__).resolve().parent


def main() -> None:
    """입력 인자를 읽고 선택한 해석 결과를 현재 작업 폴더에 CSV로 저장한다."""
    parser = argparse.ArgumentParser(description="2-D nMOS TCAD simulator (project)")
    # mode는 생략할 수 있고, config 옵션으로 다른 소자 설정 파일을 지정할 수 있다.
    parser.add_argument("mode", choices=("idvg", "idvd", "cv"), nargs="?", default="idvg")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    args = parser.parse_args()

    device, sweeps = load_config(args.config)

    # 해당 해석의 설정이 없으면 빈 사전을 넘겨 해석 함수의 기본 전압 조건을 사용한다.
    # 각 함수가 같은 형태의 결과 표를 반환하므로 저장 방식은 공통이다.
    if args.mode == "idvg":
        curve = run_idvg(device, **sweeps.get("idvg", {}))
        save_csv("idvg.csv", curve)
        print(f"idvg: {len(curve)} points -> idvg.csv")
    elif args.mode == "idvd":
        curve = run_idvd(device, **sweeps.get("idvd", {}))
        save_csv("idvd.csv", curve)
        print(f"idvd: {len(curve)} points -> idvd.csv")
    else:
        curve = run_cv(device, **sweeps.get("cv", {}))
        save_csv("cv.csv", curve)
        print(f"cv: {len(curve)} points -> cv.csv")


if __name__ == "__main__":
    # 다른 코드에서 이 모듈을 불러올 때는 명령줄 인자를 해석하지 않는다.
    main()
