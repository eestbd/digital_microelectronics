# -*- coding: utf-8 -*-
"""DEVSIM으로 2차원 nMOSFET을 구성하고 전류와 게이트 전하를 계산한다.

메시, 도핑, 접점 조건을 이 파일에서 정하고 물리 방정식은 DEVSIM의 보조 함수로 등록한다.
Id-Vg와 Id-Vd는 전류를 계산하고, C-V는 전압별 게이트 전하를 미분해 구한다.
"""

from __future__ import annotations

import math

import devsim
import numpy as np
import pandas as pd
from devsim.python_packages.model_create import CreateSolution
from devsim.python_packages.simple_physics import (
    CreateOxideContact,
    CreateOxidePotentialOnly,
    CreateSiliconDriftDiffusion,
    CreateSiliconDriftDiffusionAtContact,
    CreateSiliconOxideInterface,
    CreateSiliconPotentialOnly,
    CreateSiliconPotentialOnlyContact,
    GetContactBiasName,
    SetOxideParameters,
    SetSiliconParameters,
)

from .config import Device

# DEVSIM의 길이 단위는 cm이므로 입력 치수와 폭당 결과를 이 값으로 환산한다.
UM = 1.0e-4  # 1 um를 cm로 나타낸 값
NM = 1.0e-7  # 1 nm를 cm로 나타낸 값


def voltage_points(start: float, stop: float, step: float) -> np.ndarray:
    """양수인 step을 기준으로 시작 전압부터 증가하거나 감소하는 배열을 만든다."""
    # 범위를 간격으로 나눈 값을 반올림해 이동 횟수를 정하고 시작점까지 포함한다.
    # 범위가 간격의 정수배가 아니면 마지막 전압이 stop과 정확히 일치하지 않을 수 있다.
    count = round(abs(stop - start) / step)
    signed_step = step if stop >= start else -step
    # 소수 계산 오차가 CSV의 전압 값에 길게 남지 않도록 소수점 아래 9자리로 맞춘다.
    return np.round(start + signed_step * np.arange(count + 1), 9)


class MosfetSimulator:
    """평면 nMOS의 전위와 캐리어 수송을 계산하는 시뮬레이터다.

    build로 구조를 만들고 solve_equilibrium으로 초기 평형 해를 구한다.
    전류 해석은 enable_transport를 호출한 뒤 스윕하고, C-V는 그 과정 없이 스윕한다.
    """

    # 산화막과 접합 부근은 변화가 빠르므로 깊은 바디보다 촘촘한 메시를 사용한다.
    DX_CHANNEL = 25.0 * NM
    DY_OXIDE = 2.5 * NM
    DY_JUNCTION = 10.0 * NM
    DY_BULK = 50.0 * NM
    RAMP_STEP_V = 0.1  # 접점 전압을 바꿀 때 한 번에 이동하는 전압의 기준 상한

    def __init__(self, device: Device, name: str = "mos_light"):
        """설정을 보관하고 메시 생성에 필요한 경계 좌표를 cm로 계산한다."""
        self.dev = device
        self.name = name
        self.mesh = f"{name}_mesh"
        # 가로 방향은 왼쪽부터 소스, 게이트 아래 채널, 드레인 순서다.
        self.x_gate_left = device.source_length_um * UM
        self.x_gate_right = self.x_gate_left + device.gate_length_um * UM
        self.x_right = self.x_gate_right + device.drain_length_um * UM
        # 실리콘 표면을 y가 0인 면으로 두고 바디 쪽은 양수, 산화막 쪽은 음수로 둔다.
        self.y_oxide_top = -device.oxide_thickness_nm * NM
        self.y_junction = device.junction_depth_um * UM
        self.y_bottom = device.silicon_thickness_um * UM
        # 마지막으로 계산한 전압을 기억해 다음 전압까지 조금씩 이동할 때 사용한다.
        self.bias = {"gate": 0.0, "source": 0.0, "drain": 0.0, "body": 0.0}

    def build(self) -> None:
        """이전 소자를 지운 뒤 메시, 도핑, 전위 방정식을 차례로 준비한다."""
        self._clear_session()
        self._build_mesh()
        self._build_doping()
        self._build_physics()

    def _clear_session(self) -> None:
        """같은 프로세스에 남아 있는 소자와 메시를 제거한다."""
        # DEVSIM은 등록된 소자들을 함께 풀기 때문에 이전 비교 대상이 남으면 안 된다.
        # 소자가 메시를 참조하므로 소자를 먼저 지우고, 목록은 tuple로 복사해 순회한다.
        for device in tuple(devsim.get_device_list()):
            devsim.delete_device(device=device)
        for mesh in tuple(devsim.get_mesh_list()):
            devsim.delete_mesh(mesh=mesh)

    def _build_mesh(self) -> None:
        """실리콘과 산화막 영역, 네 접점, 두 물질 사이의 경계를 만든다."""
        # 소자 바깥에 작은 여유를 두어 최외곽 경계와 접점 범위를 잡는다.
        pad = 1.0e-8
        x_min, x_max = -pad, self.x_right + pad
        y_min, y_max = self.y_oxide_top - pad, self.y_bottom + pad

        devsim.create_2d_mesh(mesh=self.mesh)
        # 재료와 접점의 경계 위치에 메시 선을 두고 주변 간격을 지정한다.
        for pos in (x_min, 0.0, self.x_gate_left, self.x_gate_right, self.x_right, x_max):
            devsim.add_2d_mesh_line(mesh=self.mesh, dir="x", pos=pos, ps=self.DX_CHANNEL)
        for pos, spacing in (
            (y_min, self.DY_BULK),
            (self.y_oxide_top, self.DY_OXIDE),
            (0.0, min(self.DY_OXIDE, self.DY_JUNCTION)),
            (self.y_junction, self.DY_JUNCTION),
            (self.y_bottom, self.DY_BULK),
            (y_max, self.DY_BULK),
        ):
            devsim.add_2d_mesh_line(mesh=self.mesh, dir="y", pos=pos, ps=spacing)

        # 전체 배경을 공기로 둔 뒤 실리콘과 게이트 아래 산화막의 범위를 지정한다.
        devsim.add_2d_region(mesh=self.mesh, material="Air", region="air")
        devsim.add_2d_region(mesh=self.mesh, material="Silicon", region="bulk",
                             xl=0.0, xh=self.x_right, yl=self.y_bottom, yh=0.0)
        devsim.add_2d_region(mesh=self.mesh, material="Oxide", region="oxide",
                             xl=self.x_gate_left, xh=self.x_gate_right,
                             yl=0.0, yh=self.y_oxide_top)

        # 게이트는 산화막 윗면, 소스와 드레인은 실리콘 윗면, 바디는 실리콘 아랫면이다.
        devsim.add_2d_contact(mesh=self.mesh, name="gate", region="oxide", material="metal",
                              xl=self.x_gate_left, xh=self.x_gate_right,
                              yl=self.y_oxide_top, yh=self.y_oxide_top)
        devsim.add_2d_contact(mesh=self.mesh, name="source", region="bulk", material="metal",
                              xl=x_min, xh=self.x_gate_left, yl=0.0, yh=0.0)
        devsim.add_2d_contact(mesh=self.mesh, name="drain", region="bulk", material="metal",
                              xl=self.x_gate_right, xh=x_max, yl=0.0, yh=0.0)
        devsim.add_2d_contact(mesh=self.mesh, name="body", region="bulk", material="metal",
                              xl=x_min, xh=x_max, yl=self.y_bottom, yh=self.y_bottom)
        # 물질 경계의 이름은 뒤에서 전위 연결 조건을 등록할 때 다시 사용한다.
        devsim.add_2d_interface(mesh=self.mesh, name="bulk_oxide",
                                region0="bulk", region1="oxide")
        # 메시 정의를 확정한 뒤 방정식을 등록할 수 있는 소자로 생성한다.
        devsim.finalize_mesh(mesh=self.mesh)
        devsim.create_device(mesh=self.mesh, device=self.name)

    def _build_doping(self) -> None:
        """소스와 드레인의 도너 분포에서 바디의 억셉터 농도를 빼 순 도핑을 만든다."""
        # 접합에서 농도가 갑자기 끊기지 않도록 erfc 함수로 부드럽게 줄인다.
        nd, na = self.dev.sd_doping_cm3, self.dev.body_doping_cm3
        decay_x = 0.5 * self.DX_CHANNEL
        decay_y = 0.5 * self.DY_JUNCTION
        # 두 방향의 erfc가 각각 최대 2에 가까워지므로 0.25를 곱해 농도 크기를 맞춘다.
        # 소스는 게이트 왼쪽과 접합 깊이 위쪽에서 농도가 높다.
        devsim.node_model(
            device=self.name, region="bulk", name="SourceDoping",
            equation=(f"0.25*{nd:.6e}*erfc((x-{self.x_gate_left:.6e})/{decay_x:.6e})"
                      f"*erfc((y-{self.y_junction:.6e})/{decay_y:.6e})"),
        )
        # 드레인은 x방향 부호를 뒤집어 게이트 오른쪽에서 농도가 높아지게 한다.
        devsim.node_model(
            device=self.name, region="bulk", name="DrainDoping",
            equation=(f"0.25*{nd:.6e}*erfc(-(x-{self.x_gate_right:.6e})/{decay_x:.6e})"
                      f"*erfc((y-{self.y_junction:.6e})/{decay_y:.6e})"),
        )
        # 도너가 많으면 양수, 억셉터가 많으면 음수가 되도록 부호를 정한다.
        devsim.node_model(
            device=self.name, region="bulk", name="NetDoping",
            equation=f"SourceDoping + DrainDoping - {na:.6e}",
        )

    def _build_physics(self) -> None:
        """두 물질의 전위 방정식과 접점 바이어스, 계면 조건을 등록한다."""
        for region in ("bulk", "oxide"):
            CreateSolution(self.name, region, "Potential")
        SetSiliconParameters(self.name, "bulk", self.dev.temperature_k)
        # 기본 물성값을 등록한 다음 소자에 지정된 이동도로 덮어쓴다.
        # 이전의 클래스 상수 대신 Device 값을 읽어 GUI의 소자별 입력을 반영한다.
        # 이 이름들은 enable_transport에서 전류 모델을 만들 때 그대로 참조한다.
        devsim.set_parameter(device=self.name, region="bulk", name="mu_n", value=self.dev.mu_n)
        devsim.set_parameter(device=self.name, region="bulk", name="mu_p", value=self.dev.mu_p)
        # 처음에는 전위를 미지수로 두고 평형 캐리어 분포를 사용해 해를 구한다.
        CreateSiliconPotentialOnly(self.name, "bulk")
        SetOxideParameters(self.name, "oxide", self.dev.temperature_k)
        CreateOxidePotentialOnly(self.name, "oxide", "log_damp")
        # 모든 접점을 0 V에서 시작하며, 실제 스윕 전압은 set_bias에서 적용한다.
        CreateOxideContact(self.name, "oxide", "gate")
        devsim.set_parameter(device=self.name, name=GetContactBiasName("gate"), value=0.0)
        for contact in ("source", "drain", "body"):
            CreateSiliconPotentialOnlyContact(self.name, "bulk", contact)
            devsim.set_parameter(device=self.name, name=GetContactBiasName(contact), value=0.0)
        # 실리콘과 산화막의 경계에서 전위가 연결되도록 조건을 추가한다.
        CreateSiliconOxideInterface(self.name, "bulk_oxide")

    def solve_equilibrium(self) -> None:
        """초기 상태인 모든 접점 0 V에서 Poisson 방정식의 평형 해를 구한다."""
        # 이 해의 전위와 캐리어 분포가 이후 전압 스윕의 출발점이 된다.
        devsim.solve(type="dc", absolute_error=1.0e-13, relative_error=1.0e-10,
                     maximum_iterations=80)

    def enable_transport(self) -> None:
        """전자와 정공 농도를 미지수로 추가하고 드리프트 확산 전류를 계산하게 한다."""
        CreateSolution(self.name, "bulk", "Electrons")
        CreateSolution(self.name, "bulk", "Holes")
        # 임의의 농도 대신 앞에서 구한 평형 농도를 초기값으로 사용해 수렴을 돕는다.
        devsim.set_node_values(device=self.name, region="bulk", name="Electrons",
                               init_from="IntrinsicElectrons")
        devsim.set_node_values(device=self.name, region="bulk", name="Holes",
                               init_from="IntrinsicHoles")
        # bulk에 저장한 전자와 정공 이동도를 각각의 전류 식에 연결한다.
        CreateSiliconDriftDiffusion(self.name, "bulk", "mu_n", "mu_p")
        for contact in ("source", "drain", "body"):
            CreateSiliconDriftDiffusionAtContact(self.name, "bulk", contact)
        self._solve()  # 방정식이 추가된 상태에서도 해를 먼저 수렴시킨다.

    def _solve(self) -> None:
        """현재 등록된 방정식과 접점 전압으로 정상 상태 해를 구한다."""
        # 수송 해석에서는 절대 오차 한도를 크게 두고 상대 오차를 기준으로 수렴시킨다.
        devsim.solve(type="dc", absolute_error=1.0e30, relative_error=1.0e-6,
                     maximum_iterations=80)

    def set_bias(self, contact: str, volts: float) -> None:
        """목표 전압까지 작은 단계로 이동하면서 각 단계의 해를 구한다."""
        start = self.bias[contact]
        # 전압을 갑자기 크게 바꾸면 수렴이 어려워져 필요한 단계 수를 올림으로 구한다.
        # 작은 보정값은 0.1 V의 정수배에서 계산 오차로 단계가 하나 늘어나는 것을 막는다.
        steps = max(1, math.ceil(abs(volts - start) / self.RAMP_STEP_V - 1.0e-9))
        for i in range(1, steps + 1):
            value = start + (volts - start) * i / steps
            devsim.set_parameter(device=self.name,
                                 name=GetContactBiasName(contact), value=value)
            self._solve()
        self.bias[contact] = volts  # 모든 중간 계산이 성공한 뒤 목표 전압을 기록한다.

    def drain_current(self) -> float:
        """드레인 접점의 전자 전류와 정공 전류를 더해 A/um로 반환한다."""
        electron = devsim.get_contact_current(device=self.name, contact="drain",
                                              equation="ElectronContinuityEquation")
        hole = devsim.get_contact_current(device=self.name, contact="drain",
                                          equation="HoleContinuityEquation")
        # 2차원 해석의 전류는 폭 1 cm 기준이므로 1 um에 해당하는 비율을 곱한다.
        return (electron + hole) * UM

    def gate_charge(self) -> float:
        """전위 방정식에서 얻은 게이트 접점 전하를 폭당 전하인 C/cm로 반환한다."""
        return devsim.get_contact_charge(device=self.name, contact="gate",
                                         equation="PotentialEquation")

    def sweep_idvg(self, vd: float, start: float, stop: float, step: float) -> pd.DataFrame:
        """드레인 전압을 고정하고 게이트 전압별 드레인 전류를 표로 반환한다."""
        self.set_bias("drain", vd)
        vgs = voltage_points(start, stop, step)
        ids = []
        for vg in vgs:
            # set_bias가 해당 전압의 해를 구한 뒤에 전류를 읽어야 한다.
            self.set_bias("gate", float(vg))
            ids.append(self.drain_current())
        return pd.DataFrame({"Vg_V": vgs, "Id_A_per_um": ids})

    def sweep_idvd(self, vg: float, start: float, stop: float, step: float) -> pd.DataFrame:
        """게이트 전압을 고정하고 드레인 전압별 드레인 전류를 표로 반환한다."""
        # 비어 있던 Id-Vd 계산 부분이다. Id-Vg와 고정 접점, 변화 접점을 서로 바꿨다.
        # 게이트를 먼저 목표 전압으로 맞춘 뒤 드레인 전압만 바꿔 출력 특성을 구한다.
        self.set_bias("gate", vg)
        vds = voltage_points(start, stop, step)
        ids = []
        for vd in vds:
            # 전압 변경과 재계산은 set_bias가 맡으며 이전 전압의 해를 이어서 사용한다.
            self.set_bias("drain", float(vd))
            # 전자와 정공 전류를 합친 값은 drain_current에서 이미 A/um로 환산된다.
            ids.append(self.drain_current())
        # 다른 해석과 전류 열 이름을 맞춰 CLI와 GUI에서 같은 방식으로 읽게 한다.
        return pd.DataFrame({"Vd_V": vds, "Id_A_per_um": ids})

    def sweep_cv(self, start: float, stop: float, step: float) -> pd.DataFrame:
        """게이트 전압별 전하를 구하고 그 기울기로 게이트 정전용량을 계산한다.

        run_cv가 수송 방정식 없이 준비한 소자에서 사용하는 준정적 계산이다.
        전압이 바뀔 때마다 평형 전하를 구하므로 주파수에 따른 AC 응답은 계산하지 않는다.
        """
        vgs = voltage_points(start, stop, step)
        charges = []
        for vg in vgs:
            self.set_bias("gate", float(vg))
            # 각 전압에서 해가 수렴한 뒤 전하를 저장한다. 전류는 이 계산에 쓰지 않는다.
            charges.append(self.gate_charge())
        # 정전용량은 게이트 전하를 게이트 전압으로 미분한 값이다.
        # np.gradient에 실제 전압 배열을 넘겨 전압 간격을 반영한다.
        # 내부 점은 중앙 차분, 양 끝점은 한쪽 차분으로 계산하므로 전압점이 두 개 이상 필요하다.
        # 전하가 C/cm이므로 미분 결과는 F/cm이고, UM을 곱하면 F/um가 된다.
        cggs = np.gradient(charges, vgs) * UM
        return pd.DataFrame({"Vg_V": vgs, "Cgg_F_per_um": cggs})
