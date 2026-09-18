# -*- coding: utf-8 -*-
"""Step 1과 DEVSIM의 Id-Vg를 같은 Vd=0.05 V, 같은 Vg 배열로 비교한다.

config.yaml의 기본 device를 사용한다 (compare:의 길이별 소자는 사용하지 않음).
SimpleMosfet은 기본 Vth=0.6 V, k=1.4e-4를 사용하며 결과에 맞춰 보정하지 않는다.
실행: STEP2_COMPARE_MODELS.bat 더블클릭
"""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "step1"))

from simulator_practice import SimpleMosfet
from mosfet_tool.config import load_config
from mosfet_tool.workflows import run_idvg


device, sweeps = load_config(ROOT / "config.yaml")
vd = 0.05
settings = sweeps.get("idvg", {}).copy()
settings["drain_v"] = vd  # 두 모델의 드레인 전압을 동일하게 고정

print(f"DEVSIM: L={device.gate_length_um:g} um, tox={device.oxide_thickness_nm:g} nm, Vd={vd:g} V",
      flush=True)
tcad_curve = run_idvg(device, **settings)
mosfet = SimpleMosfet(vth=0.6, k=1.4e-4)
simple_curve = mosfet.sweep_idvg(vd=vd, voltages=tcad_curve["Vg_V"].to_numpy())

curves = []
for name, curve in (("Simple model", simple_curve), ("DEVSIM", tcad_curve)):
    curve["model"] = name
    curves.append(curve)

result = pd.concat(curves)
result.to_csv(ROOT / "compare_models.csv", index=False)
print(result.pivot(index="Vg_V", columns="model", values="Id_A_per_um").to_string())
print("saved: compare_models.csv")

labels = {"Vg_V": "Vg (V)", "Id_A_per_um": "Id (A/µm)", "model": "모델"}
fig = px.line(result, x="Vg_V", y="Id_A_per_um", color="model", markers=True,
              title=f"Simple model / DEVSIM Id-Vg 비교 (Vd = {vd:g} V)", labels=labels)
fig.write_html(ROOT / "compare_models.html")
fig.show()

# 로그축은 0을 표시할 수 없다. 원본 결과는 유지하고 표시용 표에서만 제외한다.
log_result = result.copy()
log_result["Id_A_per_um"] = log_result["Id_A_per_um"].where(log_result["Id_A_per_um"] > 0)
log_fig = px.line(log_result, x="Vg_V", y="Id_A_per_um", color="model", markers=True,
                  log_y=True, labels=labels,
                  title=f"Simple model / DEVSIM Id-Vg 로그축 (Vd = {vd:g} V; 0 전류는 표시 제외)")
log_fig.update_traces(connectgaps=False)
log_fig.write_html(ROOT / "compare_models_log.html")
log_fig.show()
print("saved: compare_models.html / compare_models_log.html")
