"""analyze.py 파이프라인 구조를 다이어그램(PNG)으로 그려주는 스크립트.

exchange_rates.db -> load_long_df -> to_wide -> clean
    -> moving_average       -> 01_trend_moving_average.png
    -> rolling_volatility   -> 02_rolling_volatility.png
    -> decompose(USD)       -> 03_usd_decomposition.png
"""

import os

# Windows: Graphviz가 PATH에 등록 안 된 경우를 대비해 dot.exe 경로를 직접 추가
_graphviz_bin = r"C:\Program Files\Graphviz\bin"
if os.name == "nt" and os.path.isdir(_graphviz_bin) and _graphviz_bin not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + _graphviz_bin

import graphviz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 루트
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

g = graphviz.Digraph("pipeline", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica", nodesep="0.4", ranksep="0.6")
g.attr("node", fontname="Helvetica", fontsize="11")
g.attr("edge", fontname="Helvetica", fontsize="9", color="#555555")

# ---- 원본 데이터 ----
g.node("db", "exchange_rates.db\n(USD/JPY/CNY)", shape="cylinder",
       style="filled", fillcolor="#e2e8f0", color="#334155")

# ---- 전처리 단계 ----
with g.subgraph(name="cluster_prep") as c:
    c.attr(label="전처리", style="rounded,dashed", color="#94a3b8", fontsize="11")
    c.node("load", "load_long_df()", shape="box", style="filled,rounded", fillcolor="#dbeafe", color="#1d4ed8")
    c.node("wide", "to_wide()", shape="box", style="filled,rounded", fillcolor="#dbeafe", color="#1d4ed8")
    c.node("clean", "clean()\n(결측치·이상치 처리)", shape="box", style="filled,rounded", fillcolor="#dbeafe", color="#1d4ed8")

# ---- 분석 함수 ----
with g.subgraph(name="cluster_analysis") as c:
    c.attr(label="분석 함수", style="rounded,dashed", color="#94a3b8", fontsize="11")
    c.node("ma", "moving_average()\nwindow=20", shape="box", style="filled,rounded", fillcolor="#dcfce7", color="#15803d")
    c.node("vol", "rolling_volatility()\nwindow=20", shape="box", style="filled,rounded", fillcolor="#dcfce7", color="#15803d")
    c.node("decomp", "decompose()\nUSD, period=21", shape="box", style="filled,rounded", fillcolor="#dcfce7", color="#15803d")

# ---- 출력 PNG ----
with g.subgraph(name="cluster_output") as c:
    c.attr(label="출력물", style="rounded,dashed", color="#94a3b8", fontsize="11")
    c.node("png1", "01_trend_\nmoving_average.png", shape="note",
           style="filled", fillcolor="#fef3c7", color="#b45309")
    c.node("png2", "02_rolling_\nvolatility.png", shape="note",
           style="filled", fillcolor="#fef3c7", color="#b45309")
    c.node("png3", "03_usd_\ndecomposition.png", shape="note",
           style="filled", fillcolor="#fef3c7", color="#b45309")

# ---- 흐름 연결 ----
g.edge("db", "load")
g.edge("load", "wide")
g.edge("wide", "clean")

g.edge("clean", "ma")
g.edge("clean", "vol")
g.edge("clean", "decomp")

g.edge("ma", "png1")
g.edge("vol", "png2")
g.edge("decomp", "png3")

g.render(filename="pipeline_diagram", directory=OUT_DIR, cleanup=True)
print(f"saved: {OUT_DIR}/pipeline_diagram.png")
