# -*- coding: utf-8 -*-
"""[3단계 연습] DEVSIM의 Id-Vg / Id-Vd / C-V를 GUI에서 비교한다.

Device 1 / Device 2 를 나란히 설정하고 Run 버튼을 누르면 두 곡선이 비교된다.
DEMO와 같은 방식이다: 버튼을 눌렀을 때만 계산하고, 결과는 st.session_state에
저장해 두어 재실행(슬라이더 조작 등) 후에도 그래프가 사라지지 않는다.
실행: MY_APP.bat 더블클릭
"""

import sys
from dataclasses import asdict
from pathlib import Path
from threading import Lock

import pandas as pd
import plotly.express as px
import streamlit as st

# 2단계 소자 설정과 완성된 workflow를 재사용한다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "step2"))
from mosfet_tool.config import Device
from mosfet_tool.workflows import run_cv, run_idvd, run_idvg

st.set_page_config(page_title="DEVSIM MOSFET Compare", page_icon="🔬", layout="wide")
st.title("DEVSIM MOSFET Compare")
st.caption("소자와 해석 조건을 설정한 뒤 Run simulation을 누르세요")


@st.cache_resource
def simulation_lock():
    """DEVSIM의 공유 소자 상태를 여러 세션이 동시에 바꾸지 않도록 한다."""
    return Lock()

col1, col2 = st.columns(2)


def device_panel(column, label):
    """한쪽 컬럼의 입력값으로 Device를 만들고 나머지는 기본값을 유지한다."""
    defaults = Device()
    with column:
        st.subheader(label)
        length = st.slider("Gate length (µm)", 0.5, 2.0, defaults.gate_length_um, 0.1,
                           key=f"{label}-length")
        tox = st.slider("Oxide thickness (nm)", 5.0, 20.0, defaults.oxide_thickness_nm, 1.0,
                        key=f"{label}-tox")
        body_log = st.slider("Body doping (log₁₀ cm⁻³)", 15.0, 17.0, 16.0, 0.5,
                             key=f"{label}-body")
        sd_log = st.slider("Source/drain doping (log₁₀ cm⁻³)", 18.0, 20.0, 19.0, 0.5,
                           key=f"{label}-sd")
        st.caption(f"기판: {10.0 ** body_log:.2e} cm⁻³ · 소스/드레인: {10.0 ** sd_log:.2e} cm⁻³")
        with st.expander("Advanced device parameters"):
            mu_n = st.number_input("Electron mobility μn (cm²/(V·s))", 1.0, 2000.0,
                                    defaults.mu_n, 50.0, key=f"{label}-mu-n")
            mu_p = st.number_input("Hole mobility μp (cm²/(V·s))", 1.0, 1000.0,
                                    defaults.mu_p, 25.0, key=f"{label}-mu-p")
            st.caption("상수 이동도 설정 · I–V 전류에 영향을 주며, 이 모델의 평형 C–V에는 영향을 주지 않습니다.")
    return Device(gate_length_um=length, oxide_thickness_nm=tox,
                  body_doping_cm3=10.0 ** body_log, sd_doping_cm3=10.0 ** sd_log,
                  mu_n=mu_n, mu_p=mu_p)


device1 = device_panel(col1, "Device 1")
device2 = device_panel(col2, "Device 2")
devices = {"Device 1": device1, "Device 2": device2}
device_settings = {name: asdict(device) for name, device in devices.items()}

analysis = st.selectbox("Analysis", ["Id-Vg", "Id-Vd", "C-V"], key="analysis")
bias_settings = {}
if analysis == "Id-Vg":
    workflow = run_idvg
    bias_settings["drain_v"] = st.number_input("Drain voltage Vd (V)", 0.0, 3.0, 0.05, 0.05,
                                                key="idvg-drain")
elif analysis == "Id-Vd":
    workflow = run_idvd
    bias_settings["gate_v"] = st.number_input("Gate voltage Vg (V)", 0.0, 3.0, 2.0, 0.1,
                                               key="idvd-gate")
else:
    workflow = run_cv
    st.caption("Quasi-static C-V · 소스/드레인/바디 = 0 V")

sweep_axis = "Vd" if analysis == "Id-Vd" else "Vg"
default_range = (-1.0, 2.0) if analysis == "C-V" else (0.0, 2.0)
start_v, stop_v = st.slider(f"{sweep_axis} sweep range (V)",
                            0.0 if analysis == "Id-Vd" else -1.0, 3.0,
                            default_range, 0.1, key=f"{analysis}-range")
bias_settings.update(start_v=start_v, stop_v=stop_v, step_v=0.1)
st.caption("스윕 간격: 0.1 V · 두 소자에 동일한 해석 조건을 적용합니다")

# 버튼을 눌렀을 때만 계산한다 — TCAD처럼 계산이 느려도 쓸 수 있는 방식(DEMO와 동일).
run_clicked = st.button("Run simulation", type="primary")

if run_clicked and start_v >= stop_v:
    st.error("스윕 끝 전압은 시작 전압보다 커야 합니다. 전압 범위를 넓힌 뒤 다시 실행하세요.")
elif run_clicked:
    curves = []
    name = "소자"
    try:
        with st.spinner(f"Device 1 / Device 2의 {analysis}를 계산하고 있습니다..."):
            with simulation_lock():
                for name, device in devices.items():
                    curve = workflow(device, **bias_settings)
                    curve["device"] = name
                    curves.append(curve)
        # 두 소자가 모두 성공한 경우에만 결과와 계산 당시 설정을 함께 저장한다.
        st.session_state["result"] = pd.concat(curves)
        st.session_state["result_devices"] = device_settings
        st.session_state["result_analysis"] = analysis
        st.session_state["result_bias"] = bias_settings.copy()
    except Exception as exc:
        st.error(f"{name}의 {analysis} 계산에 실패했습니다. 입력값을 확인하거나 기본값으로 되돌린 뒤 다시 실행하세요.")
        with st.expander("오류 상세"):
            st.code(str(exc))
        if "result" in st.session_state:
            st.info("아래 그래프는 이전에 성공한 계산 결과입니다.")

result = st.session_state.get("result")
if result is not None:
    # 실행 중인 이전 Id-Vg 전용 앱의 결과도 기본 조건으로 계속 표시한다.
    result_analysis = st.session_state.get("result_analysis", "Id-Vg")
    result_bias = st.session_state.get("result_bias", dict(drain_v=0.05, start_v=0.0, stop_v=2.0, step_v=0.1))
    if (st.session_state["result_devices"] != device_settings
            or result_analysis != analysis or result_bias != bias_settings):
        st.info("입력값이 변경되었습니다. 아래는 이전 결과이며, 새 조건은 Run simulation을 눌러 계산하세요.")
    st.subheader(f"{result_analysis} 결과")
    if result_analysis == "Id-Vg":
        fixed_bias = f"Vd = {result_bias['drain_v']:g} V"
    elif result_analysis == "Id-Vd":
        fixed_bias = f"Vg = {result_bias['gate_v']:g} V"
    else:
        fixed_bias = "소스/드레인/바디 = 0 V"
    result_axis = "Vd" if result_analysis == "Id-Vd" else "Vg"
    st.caption(f"{fixed_bias} · {result_axis} = {result_bias['start_v']:g}~{result_bias['stop_v']:g} V "
               f"({result_bias['step_v']:g} V 간격)")
    for name, settings in st.session_state["result_devices"].items():
        st.caption(f"{name} 계산 조건: L={settings['gate_length_um']:g} µm, "
                   f"tox={settings['oxide_thickness_nm']:g} nm, "
                   f"기판={settings['body_doping_cm3']:.2e}, 소스/드레인={settings['sd_doping_cm3']:.2e} cm⁻³ · "
                   f"μn={settings.get('mu_n', 400.0):g}, μp={settings.get('mu_p', 200.0):g} cm²/(V·s)")
    x_column = "Vd_V" if result_analysis == "Id-Vd" else "Vg_V"
    y_column = "Cgg_F_per_um" if result_analysis == "C-V" else "Id_A_per_um"
    fig = px.line(result, x=x_column, y=y_column, color="device",
                  labels={"Vg_V": "Vg (V)", "Vd_V": "Vd (V)", "Id_A_per_um": "Id (A/µm)",
                          "Cgg_F_per_um": "Cgg (F/µm)", "device": ""})
    fig.update_layout(height=420, margin=dict(l=30, r=20, t=20, b=30))
    st.plotly_chart(fig, width="stretch")
