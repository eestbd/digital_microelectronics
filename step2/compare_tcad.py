# -*- coding: utf-8 -*-
"""config.yaml의 compare 항목에 적힌 소자들의 Id-Vg를 비교한다.

기본 소자에서 일부 설정만 바꾼 소자들을 같은 전압 조건으로 계산한다.
STEP2_COMPARE.bat으로 실행하면 결과를 CSV로 저장하고 비교 그래프를 연다.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml

from mosfet_tool.config import load_config
from mosfet_tool.workflows import run_idvg

# 설정 파일은 실행 위치와 관계없이 이 스크립트가 있는 폴더에서 읽는다.
ROOT = Path(__file__).resolve().parent

base_device, sweeps = load_config(ROOT / "config.yaml")
# 공통 로더는 device와 sweeps만 반환하므로 비교용 변경 항목은 별도로 읽는다.
with (ROOT / "config.yaml").open("r", encoding="utf-8") as handle:
    variants = yaml.safe_load(handle).get("compare", {})

curves = []
for name, overrides in variants.items():
    # 기본 소자를 직접 바꾸지 않고 해당 항목만 덮어쓴 새 설정을 만든다.
    # 그래야 앞서 계산한 소자의 변경값이 다음 소자에 섞이지 않는다.
    device = dataclasses.replace(base_device, **overrides)
    print(f"\n===== {name} 시뮬레이션 =====", flush=True)
    curve = run_idvg(device, **sweeps.get("idvg", {}))
    curve["device"] = name  # 합친 표에서도 어떤 소자의 결과인지 구분한다.
    curves.append(curve)

# CSV는 현재 작업 폴더에 저장된다. 배치 파일로 실행하면 step2 폴더가 된다.
result = pd.concat(curves)
result.to_csv("compare_tcad.csv", index=False)
print("\n소자별 최대 전류 [A/um]:")
print(result.groupby("device")["Id_A_per_um"].max())
print("saved: compare_tcad.csv")

# 한 표에서 소자 이름을 기준으로 곡선을 나눠 같은 축에 표시한다.
fig = px.line(result, x="Vg_V", y="Id_A_per_um", color="device", markers=True,
              title="TCAD Id-Vg 비교 (config.yaml의 compare: 항목)",
              labels={"Vg_V": "Vg (V)", "Id_A_per_um": "Id (A/µm)", "device": "소자"})
fig.show()
