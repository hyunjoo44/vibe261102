"""대한민국 출생아수 1970~2025년 라인 그래프

사용법: python birth_line_chart.py [엑셀파일경로]
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from birth_analysis import DEFAULT_PATH, OUT_DIR, load_and_clean

plt.rcParams["font.family"] = "Malgun Gothic"  # Windows 한글 폰트
plt.rcParams["axes.unicode_minus"] = False


def plot_births(df, start=1970, end=2025, ax=None):
    """ax를 넘기면 그 위에 그린다(GUI 임베딩용). 없으면 새 Figure 생성."""
    s = df.loc[start:end, "출생아수"].astype(float)

    if ax is None:
        fig, ax = plt.subplots(figsize=(13, 6))
    else:
        fig = ax.figure
    ax.plot(s.index, s.values, color="#2a6fdb", linewidth=2.2, marker="o", markersize=3.5)
    ax.fill_between(s.index, s.values, color="#2a6fdb", alpha=0.08)

    # 주요 시점 주석: 최대, 최소, 시작, 끝
    marks = {s.index[0]: "", s.index[-1]: "", s.idxmax(): "최대", s.idxmin(): "최소"}
    for year, label in marks.items():
        val = s[year]
        text = f"{year}년{' ' + label if label else ''}\n{val / 10000:,.1f}만 명"
        if label == "최소":
            offset = (0, -32)
        elif year == s.index[0] and year != s.idxmax():  # 시작점은 최대값과 겹치지 않게 아래쪽
            offset = (14, -30)
        else:
            offset = (0, 12)
        ax.annotate(text, (year, val), textcoords="offset points",
                    xytext=offset, ha="center", fontsize=9, color="#333")
        ax.plot(year, val, "o", color="#d9480f", markersize=6, zorder=3)

    ax.set_title(f"대한민국 연간 출생아수 추이 ({start}~{end})", fontsize=15, pad=14)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수 (명)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 10000:,.0f}만"))
    step = 5 if end - start > 15 else 1
    ax.set_xticks(range(start, end + 1, step))
    ax.set_xlim(start - 1, end + 1)
    ax.set_ylim(0, s.max() * 1.12)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(1, -0.12, "자료: 통계청 「인구동향조사」(KOSIS)", transform=ax.transAxes,
            ha="right", fontsize=8, color="gray")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    df = load_and_clean(path)
    fig = plot_births(df)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "births_1970_2025.png"
    fig.savefig(out, dpi=150)
    print(f"그래프 저장: {out}")
    plt.show()
