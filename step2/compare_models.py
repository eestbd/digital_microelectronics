# -*- coding: utf-8 -*-
"""1단계의 간이 모델과 DEVSIM의 Id-Vg를 같은 전압 조건으로 비교한다.

모델 사이의 차이를 확인하려고 추가한 비교 스크립트다.
DEVSIM은 config.yaml의 기본 device를 쓰고 compare의 길이별 설정은 사용하지 않는다.
간이 모델의 문턱 전압과 이득 계수는 기본값으로 두며 DEVSIM 결과에 맞춰 보정하지 않는다.
STEP2_COMPARE_MODELS.bat으로 실행할 수 있다.
"""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent
# 간이 모델을 복사하지 않고 1단계 클래스를 그대로 불러와 같은 계산 식을 사용한다.
sys.path.insert(0, str(ROOT.parent / "step1"))

from simulator_practice import SimpleMosfet
from mosfet_tool.config import load_config
from mosfet_tool.workflows import run_idvg


device, sweeps = load_config(ROOT / "config.yaml")
vd = 0.05
# 원래 설정 사전을 보존한 채 이번 비교에 사용할 드레인 전압만 바꾼다.
# 두 모델의 바이어스가 다르면 전류 차이에 전압 조건의 영향까지 섞이게 된다.
settings = sweeps.get("idvg", {}).copy()
settings["drain_v"] = vd

print(f"DEVSIM: L={device.gate_length_um:g} um, tox={device.oxide_thickness_nm:g} nm, Vd={vd:g} V",
      flush=True)
tcad_curve = run_idvg(device, **settings)
mosfet = SimpleMosfet(vth=0.6, k=1.4e-4)
# DEVSIM이 실제로 계산한 전압 배열을 재사용해 같은 행끼리 바로 비교할 수 있게 한다.
# 전압 범위를 따로 만들면 끝점 포함 여부나 소수 오차 때문에 비교 지점이 어긋날 수 있다.
simple_curve = mosfet.sweep_idvg(vd=vd, voltages=tcad_curve["Vg_V"].to_numpy())

curves = []
# 모델 이름을 결과에 붙이면 CSV 하나로 저장하면서 그래프에서는 곡선을 나눌 수 있다.
for name, curve in (("Simple model", simple_curve), ("DEVSIM", tcad_curve)):
    curve["model"] = name
    curves.append(curve)

result = pd.concat(curves)
result.to_csv(ROOT / "compare_models.csv", index=False)
# 화면에서는 같은 전압의 두 전류를 나란히 읽을 수 있도록 열을 모델별로 펼친다.
print(result.pivot(index="Vg_V", columns="model", values="Id_A_per_um").to_string())
print("saved: compare_models.csv")

labels = {"Vg_V": "Vg (V)", "Id_A_per_um": "Id (A/µm)", "model": "모델"}
# 일반 축 그래프는 전류의 절대적인 크기를 비교할 때 사용한다.
# HTML로 저장해 두면 시뮬레이션을 다시 돌리지 않고도 그래프를 열 수 있다.
fig = px.line(result, x="Vg_V", y="Id_A_per_um", color="model", markers=True,
              title=f"Simple model / DEVSIM Id-Vg 비교 (Vd = {vd:g} V)", labels=labels)
fig.write_html(ROOT / "compare_models.html")
fig.show()

# 로그 축은 작은 전류의 차이를 보기 위한 것으로 0이나 음수 전류를 표시할 수 없다.
# 간이 모델은 문턱 전압 아래에서 정확히 0을 반환하므로 해당 점이 생긴다.
# 표시용 복사본에서만 양수가 아닌 값을 결측값으로 바꾸고 CSV의 원래 결과는 유지한다.
log_result = result.copy()
log_result["Id_A_per_um"] = log_result["Id_A_per_um"].where(log_result["Id_A_per_um"] > 0)
log_fig = px.line(log_result, x="Vg_V", y="Id_A_per_um", color="model", markers=True,
                  log_y=True, labels=labels,
                  title=f"Simple model / DEVSIM Id-Vg 로그축 (Vd = {vd:g} V; 0 전류는 표시 제외)")
# 표시에서 빠진 구간을 선으로 이어 실제 계산값이 있는 것처럼 보이지 않게 한다.
log_fig.update_traces(connectgaps=False)
log_fig.write_html(ROOT / "compare_models_log.html")
log_fig.show()
print("saved: compare_models.html / compare_models_log.html")
