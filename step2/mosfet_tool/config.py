# -*- coding: utf-8 -*-
"""소자 설정을 담는 자료형과 YAML 설정 파일을 읽는 함수를 정의한다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Device:
    """한 소자의 치수와 물성값을 보관하며, 생략한 항목에는 기본값을 쓴다."""

    # 길이는 설정 단계에서 읽기 쉬운 단위를 쓰고 메시를 만들 때 cm로 환산한다.
    gate_length_um: float = 1.0       # 소스와 드레인 사이의 게이트 길이
    source_length_um: float = 0.5     # 게이트 왼쪽 소스 영역의 길이
    drain_length_um: float = 0.5      # 게이트 오른쪽 드레인 영역의 길이
    oxide_thickness_nm: float = 10.0  # 게이트 아래 산화막 두께이며 이 항목만 nm다.
    silicon_thickness_um: float = 0.5 # 실리콘 표면에서 바디 접점까지의 깊이
    junction_depth_um: float = 0.1    # 소스와 드레인 도핑 영역의 접합 깊이
    body_doping_cm3: float = 1.0e16   # p형 바디의 억셉터 농도이며 단위는 cm^-3이다.
    sd_doping_cm3: float = 1.0e19     # n형 소스와 드레인의 도너 농도
    temperature_k: float = 300.0     # 물성값 설정에 전달하는 절대온도

    # 원래 시뮬레이터에 고정되어 있던 이동도를 소자별로 바꿀 수 있도록 옮겼다.
    # 기본값은 기존 계산과 같게 유지하고, GUI나 YAML에서 지정하면 그 값을 쓴다.
    # 두 값 모두 공간이나 전계에 따라 변하지 않는 상수이며 단위는 cm^2/(V s)다.
    mu_n: float = 400.0  # 전자 이동도로 전자 전류 계산에 사용한다.
    mu_p: float = 200.0  # 정공 이동도로 정공 전류 계산에 사용한다.


def load_config(path: str | Path) -> tuple[Device, dict]:
    """설정 파일에서 소자 설정과 해석별 전압 조건을 읽어 반환한다."""
    with Path(path).open("r", encoding="utf-8") as handle:
        # 빈 파일은 빈 사전으로 처리해 아래에서 기본 소자를 만들 수 있게 한다.
        data = yaml.safe_load(handle) or {}
    # device에 적힌 항목만 생성자에 전달하고 나머지는 Device의 기본값을 쓴다.
    device = Device(**data.get("device", {}))
    # 스윕 조건은 해석 함수에 전달한다. compare 항목은 compare_tcad.py가 따로 읽는다.
    sweeps = data.get("sweeps", {})
    return device, sweeps
