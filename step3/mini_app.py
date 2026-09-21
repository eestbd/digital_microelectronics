# -*- coding: utf-8 -*-
"""1단계 간이 모델의 두 소자를 화면에서 설정하고 Id-Vg를 비교한다.

Streamlit은 입력을 바꿀 때 스크립트를 다시 실행한다.
계산은 실행 버튼을 눌렀을 때만 하고, 결과를 session_state에 보관해 재실행 후에도 보여 준다.
STEP3_MINIAPP.bat으로 실행할 수 있다.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# step1을 모듈 검색 경로에 넣어 1단계에서 사용한 계산 클래스를 그대로 불러온다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "step1"))
from simulator_practice import SimpleMosfet

# 두 소자의 입력 패널을 나란히 놓을 수 있도록 넓은 화면을 사용한다.
st.set_page_config(page_title="Mini MOSFET Compare", page_icon="🔬", layout="wide")
st.title("Mini MOSFET Compare")
st.caption("square-law 간이 모델 · 값을 설정한 뒤 Run simulation을 누르세요")

col1, col2 = st.columns(2)


def device_panel(column, label, default_vth):
    """한쪽 열에 입력 패널을 만들고 입력값을 담은 간이 소자를 반환한다."""
    with column:
        st.subheader(label)
        # 같은 이름의 입력이 두 번 생기므로 소자 이름을 key에 넣어 구분한다.
        vth = st.slider("Vth (V)", 0.2, 1.0, default_vth, 0.05, key=f"{label}-vth")
        k_ua = st.slider("k (µA/V²)", 50, 500, 200, 10, key=f"{label}-k")
    # 화면에서는 읽기 쉬운 마이크로암페어 단위를 쓰고 계산에는 암페어 단위로 넘긴다.
    return SimpleMosfet(vth=vth, k=k_ua * 1.0e-6)


# 처음부터 문턱 전압 차이에 따른 곡선 변화를 볼 수 있도록 두 기본값을 다르게 둔다.
device1 = device_panel(col1, "Device 1", 0.4)
device2 = device_panel(col2, "Device 2", 0.8)

# 입력 조작으로 화면이 다시 실행되어도 버튼을 누르기 전에는 새로 계산하지 않는다.
run_clicked = st.button("Run simulation", type="primary")

if run_clicked:
    # 드레인 전압과 게이트 전압 배열은 두 소자에 공통으로 적용한다.
    voltages = np.arange(0.0, 2.0 + 1e-9, 0.05)
    curves = []
    for name, mosfet in {"Device 1": device1, "Device 2": device2}.items():
        curve = mosfet.sweep_idvg(vd=2.0, voltages=voltages)
        curve["device"] = name
        curves.append(curve)
    # 다음 화면 재실행에서도 마지막 계산 결과를 읽을 수 있도록 세션에 보관한다.
    st.session_state["result"] = pd.concat(curves)

result = st.session_state.get("result")
# 첫 실행에는 결과가 없으므로 그래프를 생략한다. 입력을 바꿔도 이전 결과는 남아 있다.
if result is not None:
    fig = px.line(result, x="Vg_V", y="Id_A_per_um", color="device",
                  labels={"Vg_V": "Vg (V)", "Id_A_per_um": "Id (A/µm)", "device": ""})
    # 그래프의 높이와 여백은 고정하고 너비는 현재 화면에 맞춘다.
    fig.update_layout(height=420, margin=dict(l=30, r=20, t=20, b=30))
    st.plotly_chart(fig, width="stretch")
