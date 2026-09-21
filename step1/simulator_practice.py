# -*- coding: utf-8 -*-
"""교과서의 전류 식으로 MOSFET 특성을 계산하는 1단계 예제다.

SimpleMosfet은 주어진 문턱 전압과 이득 계수로 드레인 전류를 구한다.
계산 결과를 표로 정리하고 그래프로 그리는 흐름은 2단계와 3단계에서도 사용한다.
STEP1_PRACTICE.bat으로 실행할 수 있다.
"""

import numpy as np
import pandas as pd
import plotly.express as px

# 끝값에 작은 수를 더해 2 V도 배열에 들어가도록 한다.
# 이 배열 연산 예제는 main 블록 밖에 있으므로 다른 파일에서 불러올 때도 출력된다.
voltages = np.arange(0.0, 2.0 + 1e-9, 0.25)   # 0 V부터 2 V까지 0.25 V 간격
print("전압 배열   :", voltages)
print("배열 연산   :", voltages * 2)           # 반복문 없이 모든 원소에 한 번에 적용
print("일부만 선택 :", voltages[voltages > 1.0])  # 조건이 참인 원소만 고른다.


class SimpleMosfet:
    """긴 채널 nMOS의 square-law 모델로 전류를 계산한다.

    소자 폭을 1 um로 두고 전류를 구하므로 결과를 폭당 전류인 A/um로 표시한다.
    문턱 전압 아래의 누설 전류와 채널 길이 변조는 이 모델에 포함하지 않는다.
    """

    def __init__(self, vth=0.6, k=1.4e-4):
        self.vth = vth  # 채널이 형성되기 시작하는 문턱 전압이며 단위는 V다.
        self.k = k      # 이동도, 산화막 용량, 폭과 길이의 비를 묶은 이득 계수다.
        # k의 단위는 A/V^2이며, 폭 1 um를 기준으로 한다.
        # 기본값은 산화막 두께 10 nm, 게이트 길이 1 um, 전자 이동도 400에 대응한다.

    def current(self, vg, vd):
        """게이트 전압과 드레인 전압 한 쌍에 대한 전류를 A/um로 구한다."""
        # 문턱 전압을 넘는 만큼의 게이트 전압이 채널 전하를 결정한다.
        vov = vg - self.vth
        if vov <= 0:
            return 0.0                            # 문턱 전압 이하는 차단으로 취급한다.
        if vd < vov:
            return self.k * (vov - vd / 2) * vd   # 드레인 전압이 작은 선형 영역이다.
        return 0.5 * self.k * vov * vov           # 포화 영역에서는 전류가 Vd와 무관하다.

    def sweep_idvg(self, vd, voltages):
        """드레인 전압을 고정하고 게이트 전압별 전류를 표로 반환한다."""
        ids = [self.current(vg, vd) for vg in voltages]
        return pd.DataFrame({"Vg_V": voltages, "Id_A_per_um": ids})

    def sweep_idvd(self, vg, voltages):
        """게이트 전압을 고정하고 드레인 전압별 전류를 표로 반환한다."""
        # Id-Vg와 달리 current의 첫 인자는 그대로 두고 두 번째 인자를 바꾼다.
        # 입력 전압과 같은 순서로 전류를 모아야 각 행의 전압과 전류가 짝을 이룬다.
        ids = [self.current(vg, vd) for vd in voltages]
        # 비교 스크립트가 이 열 이름으로 가로축과 세로축을 찾는다.
        return pd.DataFrame({"Vd_V": voltages, "Id_A_per_um": ids})



if __name__ == "__main__":   # 직접 실행할 때만 파일 저장과 그래프 출력을 한다.
    mosfet = SimpleMosfet(vth=0.6, k=1.4e-4)
    print(f"\n단일 점: Vg=1.0 V, Vd=2.0 V  ->  Id = {mosfet.current(1.0, 2.0):.3e} A/um")

    # 전압별 결과를 표로 모으고, 그중 전류 열에서 최댓값을 확인한다.
    curve = mosfet.sweep_idvg(vd=2.0, voltages=voltages)
    print("\n== Id-Vg (Vd = 2.0 V) ==")
    print(curve.to_string(index=False))
    print("\n최대 전류  :", curve["Id_A_per_um"].max(), "A/um")
    curve.to_csv("practice_idvg.csv", index=False)  # 표의 행 번호는 저장하지 않는다.
    print("saved: practice_idvg.csv")

    # 표의 열 이름을 축에 연결하고 실제 계산 지점에는 점을 표시한다.
    fig = px.line(curve, x="Vg_V", y="Id_A_per_um", markers=True,
                  title="Id-Vg (square-law model, Vd = 2 V)",
                  labels={"Vg_V": "Vg (V)", "Id_A_per_um": "Id (A/µm)"})
    fig.show()   # 기본 브라우저에 열린다
