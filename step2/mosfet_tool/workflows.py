# -*- coding: utf-8 -*-
"""소자 준비부터 전압 스윕까지의 순서를 해석 종류별 함수로 묶는다.

CLI와 GUI가 같은 함수를 사용하므로 계산 순서와 결과 열 이름을 공통으로 유지한다.
각 함수는 새 소자를 만들며, 소자를 준비하는 과정에서 이전 DEVSIM 상태가 지워진다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import Device
from .simulator import MosfetSimulator


def run_idvg(device: Device, drain_v: float = 0.05, start_v: float = 0.0,
             stop_v: float = 2.0, step_v: float = 0.1) -> pd.DataFrame:
    """드레인 전압을 고정한 상태에서 게이트 전압별 전류를 구한다."""
    sim = MosfetSimulator(device, name="idvg")
    # 구조를 만든 뒤 평형 해를 먼저 구해 전류 계산의 초기값으로 사용한다.
    sim.build()
    sim.solve_equilibrium()
    # 전류를 구하려면 전위뿐 아니라 전자와 정공의 연속 방정식도 필요하다.
    sim.enable_transport()
    return sim.sweep_idvg(drain_v, start_v, stop_v, step_v)


def run_idvd(device: Device, gate_v: float = 2.0, start_v: float = 0.0,
             stop_v: float = 2.0, step_v: float = 0.1) -> pd.DataFrame:
    """게이트 전압을 고정한 상태에서 드레인 전압별 전류를 구한다."""
    # 비어 있던 Id-Vd 실행 과정을 Id-Vg와 같은 준비 순서로 채웠다.
    # 여기서는 계산에 필요한 상태를 준비하고, 전압을 바꾸는 반복은 sweep_idvd가 맡는다.
    sim = MosfetSimulator(device, name="idvd")
    sim.build()
    sim.solve_equilibrium()
    # Poisson 방정식만으로는 드레인 전류를 얻을 수 없어 수송 방정식을 추가한다.
    sim.enable_transport()
    # gate_v는 고정값이고 나머지 세 값은 드레인 전압의 범위와 간격이다.
    return sim.sweep_idvd(gate_v, start_v, stop_v, step_v)


def run_cv(device: Device, start_v: float = -1.0, stop_v: float = 2.0,
           step_v: float = 0.1) -> pd.DataFrame:
    """게이트 전압에 따른 평형 전하의 변화로 준정적 C-V를 구한다."""
    sim = MosfetSimulator(device, name="cv")
    sim.build()
    sim.solve_equilibrium()
    # 이 해석은 전류가 아니라 게이트 전하의 기울기를 사용한다.
    # enable_transport를 호출하지 않고 각 전압에서 전위와 평형 캐리어 분포를 구한다.
    # 소스, 드레인, 바디 전압은 초기값인 0 V로 유지되며 AC 주파수는 사용하지 않는다.
    return sim.sweep_cv(start_v, stop_v, step_v)


def save_csv(path: str | Path, curve: pd.DataFrame) -> None:
    """결과 표를 CSV로 저장하고 계산과 관계없는 행 번호는 제외한다."""
    curve.to_csv(path, index=False)
