# -*- coding: utf-8 -*-
"""문턱 전압이 다른 간이 MOSFET 세 개의 Id-Vd를 비교한다.

LVT, RVT, HVT는 각각 낮은 문턱 전압, 기준 문턱 전압, 높은 문턱 전압을 뜻한다.
STEP1_COMPARE.bat으로 실행하면 결과 표를 저장하고 그래프를 연다.
"""

import numpy as np
import pandas as pd
import plotly.express as px

from simulator_practice import SimpleMosfet   # 1단계 클래스를 import해서 재사용

# 세 소자에 같은 게이트 전압과 드레인 전압 배열을 적용한다.
# 게이트 전압이 같아도 문턱 전압이 낮은 소자는 채널 전하가 많아 전류가 커진다.
vg = 1.0  # 고정할 게이트 전압이며 단위는 V다.
voltages = np.arange(0.0, 2.0 + 1e-9, 0.05)  # 끝값 2 V를 포함하는 드레인 전압 배열

# 문턱 전압만 바꾸고 이득 계수는 SimpleMosfet의 기본값을 공통으로 사용한다.
devices = {
    "LVT (Vth 0.4 V)": SimpleMosfet(vth=0.4),
    "RVT (Vth 0.6 V)": SimpleMosfet(vth=0.6),
    "HVT (Vth 0.8 V)": SimpleMosfet(vth=0.8),
}

curves = []
for name, mosfet in devices.items():          # 각 소자를 같은 조건으로 계산한다.
    curve = mosfet.sweep_idvd(vg=vg, voltages=voltages)
    curve["device"] = name                    # 어느 소자의 결과인지 열로 표시
    curves.append(curve)

# 소자 이름을 붙인 뒤 합쳐야 CSV와 그래프에서 각 결과를 구분할 수 있다.
result = pd.concat(curves)
result.to_csv("compare_step1.csv", index=False)
print(result.groupby("device")["Id_A_per_um"].max())  # 소자별 최대 전류 요약
print("saved: compare_step1.csv")

# Id-Vd 결과이므로 드레인 전압을 가로축에 놓고 소자별로 색을 나눈다.
fig = px.line(result, x="Vd_V", y="Id_A_per_um", color="device", markers=True,
              title=f"LVT / RVT / HVT Id-Vd 비교 (Vg = {vg:g} V)",
              labels={"Vd_V": "Vd (V)", "Id_A_per_um": "Id (A/µm)", "device": "소자"})
fig.show()   # 곡선 3개가 색깔별로 한 그래프에 겹쳐 나온다
