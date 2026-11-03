"""대한민국 출생아수·합계출산율·자연증가 데이터 클렌징 및 다각도 분석 (KOSIS INH_1B8000F_01)

사용법: python birth_analysis.py [엑셀파일경로]
"""
import sys
from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path.home() / "Downloads" / "출생아수__합계출산율__자연증가_등.xlsx"
OUT_DIR = Path(__file__).parent / "birth_output"

# 원본 항목명(부분 문자열) → 분석용 컬럼명
COLUMN_MAP = {
    "출생아수": "출생아수",
    "자연증가건수": "자연증가건수",
    "조출생률": "조출생률",
    "자연증가율": "자연증가율",
    "합계출산율": "합계출산율",
    "출생성비": "출생성비",
}
INT_COLS = ["출생아수", "자연증가건수"]


def load_and_clean(path=DEFAULT_PATH) -> pd.DataFrame:
    """KOSIS 가로형(항목×연도) 시트를 연도별 세로형 DataFrame으로 정리한다."""
    raw = pd.read_excel(path, sheet_name=0, header=None)

    # 1) 첫 행 = 연도 헤더, 첫 열 = 항목명 → 전치
    raw = raw.set_index(0)
    raw.columns = raw.iloc[0]
    df = raw.iloc[1:].T

    # 2) 항목명 정리: 공백 제거 후 '(단위)' 떼고 표준 이름으로 매핑
    rename = {}
    for col in df.columns:
        name = str(col).strip()
        for key, std in COLUMN_MAP.items():
            if name.startswith(key):
                rename[col] = std
    df = df.rename(columns=rename)[list(COLUMN_MAP.values())]
    df.columns.name = None

    # 3) 연도 인덱스 정수화, 값은 숫자로 강제 변환 ('-', '…' 등 결측 기호 → NaN)
    df.index = pd.to_numeric(df.index, errors="coerce")
    df = df[df.index.notna()]
    df.index = df.index.astype(int)
    df.index.name = "연도"
    df = df.apply(pd.to_numeric, errors="coerce")

    # 4) 중복 연도 제거, 정렬
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # 5) 결측치: 연속 시계열이므로 선형 보간(양 끝은 남김)
    df = df.interpolate(method="linear", limit_area="inside")

    # 6) 인원 수는 정수형(결측 허용 Int64)
    for col in INT_COLS:
        df[col] = df[col].round().astype("Int64")

    # 7) 값 범위 검증 — 비정상 값은 NaN 처리
    valid = {
        "출생아수": (0, 2_000_000),
        "합계출산율": (0, 10),
        "출생성비": (90, 130),
        "조출생률": (0, 60),
    }
    for col, (lo, hi) in valid.items():
        bad = ~df[col].between(lo, hi) & df[col].notna()
        if bad.any():
            print(f"[경고] {col} 범위 이탈 {bad.sum()}건 → NaN 처리: {df.index[bad].tolist()}")
            df.loc[bad, col] = pd.NA
    return df


def quality_report(df: pd.DataFrame) -> None:
    print("=" * 70, "\n[1] 데이터 품질 점검\n" + "=" * 70)
    print(f"기간: {df.index.min()}~{df.index.max()} ({len(df)}개 연도)")
    missing_years = sorted(set(range(df.index.min(), df.index.max() + 1)) - set(df.index))
    print(f"누락 연도: {missing_years or '없음'}")
    print("컬럼별 결측치:", df.isna().sum().to_dict())
    print("\n자료형:\n", df.dtypes.to_string(), sep="")
    print("\n※ 1970~2014년은 2016.12 출생통계 작성방식 변경에 따라 소급 보정된 값")


def analyze(df: pd.DataFrame) -> dict:
    b = df["출생아수"].astype(float)
    tfr = df["합계출산율"]
    results = {}

    print("\n" + "=" * 70, "\n[2] 기술통계\n" + "=" * 70)
    desc = df.describe().T
    print(desc.round(2).to_string())
    results["기술통계"] = desc

    print("\n" + "=" * 70, "\n[3] 정점·저점 및 장기 변화\n" + "=" * 70)
    first, last = df.index.min(), df.index.max()
    print(f"출생아수 최대: {b.idxmax()}년 {b.max():,.0f}명 / 최소: {b.idxmin()}년 {b.min():,.0f}명")
    print(f"합계출산율 최대: {tfr.idxmax()}년 {tfr.max():.2f}명 / 최소: {tfr.idxmin()}년 {tfr.min():.3f}명")
    total_change = b[last] / b[first] - 1
    cagr = (b[last] / b[first]) ** (1 / (last - first)) - 1
    print(f"{first}→{last} 출생아수 변화율: {total_change:+.1%}  (연평균 {cagr:+.2%})")

    print("\n" + "=" * 70, "\n[4] 전년 대비 증감\n" + "=" * 70)
    yoy = pd.DataFrame({
        "출생아수": b,
        "증감(명)": b.diff(),
        "증감률(%)": b.pct_change() * 100,
    })
    print("감소폭 상위 5개 연도:")
    print(yoy.nsmallest(5, "증감(명)").round(1).to_string())
    print("\n증가폭 상위 5개 연도:")
    print(yoy.nlargest(5, "증감(명)").round(1).to_string())
    # 최장 연속 감소 구간
    dec = (yoy["증감(명)"] < 0).astype(int)
    run = dec.groupby((dec != dec.shift()).cumsum()).cumsum()
    end = run.idxmax()
    print(f"\n최장 연속 감소: {end - run.max() + 1}~{end}년 ({run.max()}년 연속)")
    results["전년대비"] = yoy

    print("\n" + "=" * 70, "\n[5] 연대별 평균\n" + "=" * 70)
    decade = df.groupby(df.index // 10 * 10).mean()
    decade.index = [f"{d}년대" for d in decade.index]
    print(decade.round(2).to_string())
    results["연대별"] = decade

    print("\n" + "=" * 70, "\n[6] 저출산 임계점 진입 시점 (합계출산율)\n" + "=" * 70)
    for label, th in [("인구대체수준 2.1 미만", 2.1), ("저출산 1.5 미만", 1.5),
                      ("초저출산 1.3 미만", 1.3), ("1.0 미만", 1.0)]:
        below = tfr[tfr < th]
        print(f"{label:<18}: {below.index.min() if len(below) else '해당 없음'}년부터")

    print("\n" + "=" * 70, "\n[7] 인구 자연감소 (자연증가건수 < 0)\n" + "=" * 70)
    neg = df[df["자연증가건수"] < 0]
    print(f"자연감소 시작: {neg.index.min()}년, 이후 누적 자연감소: {-neg['자연증가건수'].sum():,}명")
    print(neg[["출생아수", "자연증가건수", "자연증가율"]].to_string())

    print("\n" + "=" * 70, "\n[8] 출생성비 (정상범위 103~107)\n" + "=" * 70)
    sr = df["출생성비"]
    high = sr[sr > 107]
    print(f"정상범위 초과 연도 {len(high)}개: {high.index.min()}~{high.index.max()}")
    print(f"최고: {sr.idxmax()}년 {sr.max():.1f}")
    print(f"최근 5년 평균: {sr.tail(5).mean():.1f}")

    print("\n" + "=" * 70, "\n[9] 상관관계\n" + "=" * 70)
    corr = df.astype(float).corr()
    print(corr.round(3).to_string())
    results["상관관계"] = corr

    print("\n" + "=" * 70, "\n[10] 최근 동향 (2015년 이후)\n" + "=" * 70)
    recent = yoy.loc[2015:].copy()
    recent["합계출산율"] = tfr.loc[2015:]
    print(recent.round(2).to_string())
    rebound = recent[recent["증감(명)"] > 0].index.tolist()
    print(f"→ 2015년 이후 출생아수가 반등한 연도: {rebound}")
    return results


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    df = load_and_clean(path)
    quality_report(df)
    results = analyze(df)

    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "births_clean.csv", encoding="utf-8-sig")
    with pd.ExcelWriter(OUT_DIR / "births_analysis.xlsx") as writer:
        df.to_excel(writer, sheet_name="정제데이터")
        for name, table in results.items():
            table.to_excel(writer, sheet_name=name)
    print(f"\n결과 저장: {OUT_DIR}")


if __name__ == "__main__":
    main()
