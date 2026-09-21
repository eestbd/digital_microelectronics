# -*- coding: utf-8 -*-
"""두 DEVSIM 소자의 설정을 바꾸며 Id-Vg, Id-Vd, C-V를 비교하는 앱이다.

간이 모델을 쓰는 mini_app과 달리 2단계에서 구현한 DEVSIM 해석 함수를 호출한다.
계산은 실행 버튼을 눌렀을 때만 하고, 결과와 그때의 입력 조건을 함께 보관한다.
MY_APP.bat으로 실행할 수 있다.
"""

import sys
from dataclasses import asdict
from pathlib import Path
from threading import Lock

import pandas as pd
import plotly.express as px
import streamlit as st

# 2단계의 소자 설정과 해석 함수를 불러와 CLI에서 사용하는 계산 과정을 그대로 쓴다.
# 이 앱에서는 YAML을 읽지 않고 화면 입력과 Device의 기본값으로 소자를 만든다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "step2"))
from mosfet_tool.config import Device
from mosfet_tool.workflows import run_cv, run_idvd, run_idvg

# 두 소자의 설정과 비교 그래프를 함께 볼 수 있도록 화면을 넓게 사용한다.
st.set_page_config(page_title="DEVSIM MOSFET Compare", page_icon="🔬", layout="wide")
st.title("DEVSIM MOSFET Compare")
st.caption("소자와 해석 조건을 설정한 뒤 Run simulation을 누르세요")


@st.cache_resource
def simulation_lock():
    """DEVSIM의 공유 소자 상태를 여러 세션이 동시에 바꾸지 않도록 한다."""
    # 새 소자를 만들 때 프로세스에 등록된 이전 소자를 지우므로 동시 해석은 충돌할 수 있다.
    # cache_resource로 같은 잠금을 공유해야 화면 재실행이나 다른 세션에도 잠금이 적용된다.
    return Lock()

col1, col2 = st.columns(2)


def device_panel(column, label):
    """한쪽 열의 입력값으로 소자 설정을 만들고 나머지는 기본값을 유지한다."""
    # 치수와 이동도의 초기값을 Device에서 가져와 계산 코드와 화면의 기본값을 맞춘다.
    defaults = Device()
    with column:
        st.subheader(label)
        # 소자 이름을 key에 넣어 두 패널의 입력값이 서로 독립적으로 저장되게 한다.
        length = st.slider("Gate length (µm)", 0.5, 2.0, defaults.gate_length_um, 0.1,
                           key=f"{label}-length")
        tox = st.slider("Oxide thickness (nm)", 5.0, 20.0, defaults.oxide_thickness_nm, 1.0,
                        key=f"{label}-tox")
        # 도핑 농도는 범위가 넓어 농도 자체 대신 10을 밑으로 하는 지수를 조절한다.
        # 예를 들어 16을 고르면 실제 소자에는 10의 16승에 해당하는 농도를 전달한다.
        body_log = st.slider("Body doping (log₁₀ cm⁻³)", 15.0, 17.0, 16.0, 0.5,
                             key=f"{label}-body")
        sd_log = st.slider("Source/drain doping (log₁₀ cm⁻³)", 18.0, 20.0, 19.0, 0.5,
                           key=f"{label}-sd")
        st.caption(f"기판: {10.0 ** body_log:.2e} cm⁻³ · 소스/드레인: {10.0 ** sd_log:.2e} cm⁻³")
        # 이동도는 자주 바꾸는 치수와 분리해 접을 수 있는 설정 안에 둔다.
        # 입력한 값은 소자별 상수 이동도로 쓰며, 전계 의존 이동도 모델은 아니다.
        with st.expander("Advanced device parameters"):
            mu_n = st.number_input("Electron mobility μn (cm²/(V·s))", 1.0, 2000.0,
                                    defaults.mu_n, 50.0, key=f"{label}-mu-n")
            mu_p = st.number_input("Hole mobility μp (cm²/(V·s))", 1.0, 1000.0,
                                    defaults.mu_p, 25.0, key=f"{label}-mu-p")
            st.caption("상수 이동도 설정 · I–V 전류에 영향을 주며, 이 모델의 평형 C–V에는 영향을 주지 않습니다.")
    # 지수로 입력한 도핑을 실제 농도로 바꾸고 전자와 정공 이동도도 소자에 전달한다.
    # 화면에 없는 소스 길이, 드레인 길이, 접합 깊이 등은 Device의 기본값을 유지한다.
    return Device(gate_length_um=length, oxide_thickness_nm=tox,
                  body_doping_cm3=10.0 ** body_log, sd_doping_cm3=10.0 ** sd_log,
                  mu_n=mu_n, mu_p=mu_p)


device1 = device_panel(col1, "Device 1")
device2 = device_panel(col2, "Device 2")
devices = {"Device 1": device1, "Device 2": device2}
# 설정 전체를 사전으로 남겨 두면 계산 당시 조건을 표시하고 이후 입력 변경도 비교할 수 있다.
device_settings = {name: asdict(device) for name, device in devices.items()}

# 선택한 해석에 맞는 함수와 고정 전압을 정한다.
# bias_settings의 키 이름은 workflows 함수의 인자 이름과 맞춰 그대로 전달한다.
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
    # C-V는 전류 해석 없이 게이트 전압에 따른 평형 전하를 구한다.
    # 게이트를 제외한 접점은 소자를 생성할 때의 0 V를 그대로 사용한다.
    workflow = run_cv
    st.caption("Quasi-static C-V · 소스/드레인/바디 = 0 V")

# Id-Vd만 드레인을 스윕하며 나머지 해석은 게이트를 스윕한다.
# C-V의 기본 범위는 음의 게이트 전압도 포함해 축적 상태부터 볼 수 있게 한다.
sweep_axis = "Vd" if analysis == "Id-Vd" else "Vg"
default_range = (-1.0, 2.0) if analysis == "C-V" else (0.0, 2.0)
start_v, stop_v = st.slider(f"{sweep_axis} sweep range (V)",
                            0.0 if analysis == "Id-Vd" else -1.0, 3.0,
                            default_range, 0.1, key=f"{analysis}-range")
# 화면에서 고른 범위를 두 소자에 똑같이 적용하고 스윕 간격은 0.1 V로 고정한다.
bias_settings.update(start_v=start_v, stop_v=stop_v, step_v=0.1)
st.caption("스윕 간격: 0.1 V · 두 소자에 동일한 해석 조건을 적용합니다")

# Streamlit은 입력을 바꿀 때마다 전체 코드를 실행하므로 계산 시작은 버튼으로 제한한다.
# 화면만 조절할 때 시간이 걸리는 DEVSIM 해석이 반복되지 않게 하기 위한 것이다.
run_clicked = st.button("Run simulation", type="primary")

if run_clicked and start_v >= stop_v:
    # 같은 전압 한 점으로는 C-V의 수치 미분이 불가능하므로 유효한 범위를 먼저 확인한다.
    st.error("스윕 끝 전압은 시작 전압보다 커야 합니다. 전압 범위를 넓힌 뒤 다시 실행하세요.")
elif run_clicked:
    curves = []
    name = "소자"
    try:
        with st.spinner(f"Device 1 / Device 2의 {analysis}를 계산하고 있습니다..."):
            # 두 소자를 차례로 계산하는 동안 다른 세션이 DEVSIM 상태를 바꾸지 못하게 한다.
            with simulation_lock():
                for name, device in devices.items():
                    curve = workflow(device, **bias_settings)
                    # 두 번째 소자를 만들면 첫 소자의 DEVSIM 상태는 지워지지만 결과 표는 남는다.
                    curve["device"] = name
                    curves.append(curve)
        # 두 계산이 모두 끝난 뒤에만 저장해 한쪽 결과와 다른 시점의 결과가 섞이지 않게 한다.
        # 그래프뿐 아니라 소자 설정, 해석 종류, 전압 조건도 같은 시점의 값으로 보관한다.
        st.session_state["result"] = pd.concat(curves)
        st.session_state["result_devices"] = device_settings
        st.session_state["result_analysis"] = analysis
        st.session_state["result_bias"] = bias_settings.copy()
    except Exception as exc:
        # 수렴 실패 등이 발생하면 실패한 소자를 알리고 마지막으로 성공한 결과를 유지한다.
        st.error(f"{name}의 {analysis} 계산에 실패했습니다. 입력값을 확인하거나 기본값으로 되돌린 뒤 다시 실행하세요.")
        with st.expander("오류 상세"):
            st.code(str(exc))
        if "result" in st.session_state:
            st.info("아래 그래프는 이전에 성공한 계산 결과입니다.")

result = st.session_state.get("result")
if result is not None:
    # 이전 Id-Vg 전용 버전에서 남은 세션에는 해석 종류와 전압 조건이 없을 수 있다.
    # 그런 경우에는 당시의 기본값을 사용해 기존 결과를 계속 표시한다.
    result_analysis = st.session_state.get("result_analysis", "Id-Vg")
    result_bias = st.session_state.get("result_bias", dict(drain_v=0.05, start_v=0.0, stop_v=2.0, step_v=0.1))
    # 화면의 현재 입력과 계산 당시 입력을 비교해 그래프가 이전 조건의 결과인지 알린다.
    # 슬라이더를 움직였다는 이유만으로 기존 그래프의 조건 표시를 바꾸지는 않는다.
    if (st.session_state["result_devices"] != device_settings
            or result_analysis != analysis or result_bias != bias_settings):
        st.info("입력값이 변경되었습니다. 아래는 이전 결과이며, 새 조건은 Run simulation을 눌러 계산하세요.")
    st.subheader(f"{result_analysis} 결과")
    # 결과를 만들 때의 해석 종류로 고정 전압과 축을 정한다.
    # 현재 선택한 해석을 사용하면 이전 결과의 열 이름과 맞지 않을 수 있다.
    if result_analysis == "Id-Vg":
        fixed_bias = f"Vd = {result_bias['drain_v']:g} V"
    elif result_analysis == "Id-Vd":
        fixed_bias = f"Vg = {result_bias['gate_v']:g} V"
    else:
        fixed_bias = "소스/드레인/바디 = 0 V"
    result_axis = "Vd" if result_analysis == "Id-Vd" else "Vg"
    st.caption(f"{fixed_bias} · {result_axis} = {result_bias['start_v']:g}~{result_bias['stop_v']:g} V "
               f"({result_bias['step_v']:g} V 간격)")
    # 이동도 입력이 없던 버전의 결과는 기존 상수값으로 표시한다.
    for name, settings in st.session_state["result_devices"].items():
        st.caption(f"{name} 계산 조건: L={settings['gate_length_um']:g} µm, "
                   f"tox={settings['oxide_thickness_nm']:g} nm, "
                   f"기판={settings['body_doping_cm3']:.2e}, 소스/드레인={settings['sd_doping_cm3']:.2e} cm⁻³ · "
                   f"μn={settings.get('mu_n', 400.0):g}, μp={settings.get('mu_p', 200.0):g} cm²/(V·s)")
    # C-V만 세로축이 정전용량이고 두 전류 해석은 같은 전류 열을 사용한다.
    x_column = "Vd_V" if result_analysis == "Id-Vd" else "Vg_V"
    y_column = "Cgg_F_per_um" if result_analysis == "C-V" else "Id_A_per_um"
    fig = px.line(result, x=x_column, y=y_column, color="device",
                  labels={"Vg_V": "Vg (V)", "Vd_V": "Vd (V)", "Id_A_per_um": "Id (A/µm)",
                          "Cgg_F_per_um": "Cgg (F/µm)", "device": ""})
    # 소자별 곡선을 같은 축에 그리고 너비를 현재 화면에 맞춘다.
    fig.update_layout(height=420, margin=dict(l=30, r=20, t=20, b=30))
    st.plotly_chart(fig, width="stretch")
