# -*- coding: utf-8 -*-
"""시뮬레이터 클래스를 직접 사용해 Id-Vg를 계산하는 예제다.

mosfet.py나 workflows를 거치지 않아 소자 준비부터 스윕까지의 호출 순서를 볼 수 있다.
"""

from mosfet_tool.config import Device
from mosfet_tool.simulator import MosfetSimulator

device = Device()  # 예를 들어 gate_length_um=0.5를 전달하면 게이트 길이만 바뀐다.

sim = MosfetSimulator(device, name="example")
sim.build()              # 메시, 도핑, 접점 조건과 전위 방정식을 등록한다.
sim.solve_equilibrium()  # 모든 접점이 0 V인 평형 해를 먼저 구한다.
sim.enable_transport()   # 전자와 정공의 전류 방정식을 추가하고 초기 해를 구한다.

# 드레인은 0.05 V로 고정하고 게이트를 0 V부터 2 V까지 0.1 V 간격으로 바꾼다.
curve = sim.sweep_idvg(vd=0.05, start=0.0, stop=2.0, step=0.1)

# 이 예제는 저장이나 그래프 출력 없이 전압과 전류 표만 터미널에 보여 준다.
print("\n== Id-Vg (Vd = 0.05 V) ==")
print(curve.to_string(index=False))
