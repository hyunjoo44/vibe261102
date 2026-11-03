"""
네이버 증권 코스피200 크롤러

https://stock.naver.com/market/stock/kr/stocklist/priceTop (거래대금 상위) 은
Next.js 기반 페이지라 HTML 소스에는 종목 데이터가 없고, 브라우저가 JavaScript로
아래 JSON API를 호출해 표를 그린다. 그래서 BeautifulSoup으로 HTML을 파싱하면
빈 결과가 나오므로 같은 API를 직접 호출해 데이터를 가져온다.

  priceTop 목록  : https://stock.naver.com/api/domestic/market/stock/default
                   (marketType=KOSPI, orderType=priceTop, startIdx=페이지번호(0부터), pageSize)
  코스피200 구성 : https://m.stock.naver.com/api/index/KPI200/enrollStocks

priceTop API에는 코스피200만 거르는 옵션이 없어서(KOSPI/KOSDAQ/KONEX/ALL 뿐),
코스피 전체 priceTop 목록을 페이지 단위로 넘기며 코스피200 구성 종목만 골라 200개를 모은다.

수집 항목
  1) 코스피200 지수 현재 시세
  2) 코스피200 일별 시세
  3) 코스피200 종목 200개 (priceTop 페이지 기준, 거래대금 순)

실행:  python kospi200_crawler.py
결과:  kospi200_index_daily.csv, kospi200_stocks.csv, kospi200.xlsx (엑셀 저장에 openpyxl 필요)
"""

import csv
import time

import requests

INDEX_API = "https://m.stock.naver.com/api/index/KPI200"
PRICE_TOP_API = "https://stock.naver.com/api/domestic/market/stock/default"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/market/stock/kr/stocklist/priceTop",
}
INDEX_PAGE_SIZE = 50  # m.stock API는 100 이상을 거부함
PRICE_TOP_PAGE_SIZE = 100  # priceTop 페이지가 쓰는 값
TARGET_COUNT = 200  # 코스피200 구성 종목 수


def get_json(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_index_summary():
    """코스피200 지수 현재가/등락"""
    d = get_json(f"{INDEX_API}/basic")
    return {
        "name": d["stockName"],
        "price": d["closePrice"],
        "change": d["compareToPreviousClosePrice"],
        "rate": d["fluctuationsRatio"],
        "status": d["marketStatus"],
        "time": d["localTradedAt"],
    }


def fetch_index_daily(pages=1):
    """코스피200 일별 시세 (페이지당 INDEX_PAGE_SIZE일)"""
    rows = []
    for page in range(1, pages + 1):
        data = get_json(f"{INDEX_API}/price", {"page": page, "pageSize": INDEX_PAGE_SIZE})
        if not data:
            break
        for d in data:
            rows.append({
                "날짜": d["localTradedAt"],
                "종가": d["closePrice"],
                "전일비": d["compareToPreviousClosePrice"],
                "등락률(%)": d["fluctuationsRatio"],
                "시가": d["openPrice"],
                "고가": d["highPrice"],
                "저가": d["lowPrice"],
            })
        time.sleep(0.3)
    return rows


def fetch_kospi200_codes():
    """코스피200 구성 종목코드 집합 (시가총액 상위 TARGET_COUNT개)"""
    codes = []
    page = 1
    while len(codes) < TARGET_COUNT:
        data = get_json(f"{INDEX_API}/enrollStocks", {"page": page, "pageSize": INDEX_PAGE_SIZE})
        if not data:
            break
        codes.extend(d["itemCode"] for d in data)
        page += 1
        time.sleep(0.3)
    return set(codes[:TARGET_COUNT])


def to_unit(value, unit):
    """원 단위 문자열을 백만/억 단위 정수로"""
    # API가 "4359497000000.0"처럼 소수점 붙은 값을 줄 때도 있음
    return int(float(value)) // unit if value else ""


def fetch_constituents(log=print):
    """priceTop 목록을 페이지별로 넘기며 코스피200 종목만 수집

    log: 진행 메시지를 받을 함수 (GUI에서는 로그 창에 출력)
    """
    kospi200 = fetch_kospi200_codes()
    log(f"  코스피200 구성 종목코드 {len(kospi200)}개 확인")

    rows = []
    seen = set()
    page = 0  # startIdx는 행 번호가 아니라 0부터 시작하는 페이지 번호
    while len(rows) < len(kospi200):
        data = get_json(PRICE_TOP_API, {
            "tradeType": "KRX",
            "marketType": "KOSPI",
            "orderType": "priceTop",
            "startIdx": page,
            "pageSize": PRICE_TOP_PAGE_SIZE,
        })
        if not data:  # 마지막 페이지를 지나면 빈 리스트가 옴
            break
        before = len(rows)
        for d in data:
            code = d["itemcode"]
            # 페이지가 넘어가는 사이 순위가 바뀌어 같은 종목이 다시 나올 수 있음
            if code not in kospi200 or code in seen:
                continue
            seen.add(code)
            rows.append({
                "순위": len(rows) + 1,
                "종목코드": code,
                "종목명": d["itemname"],
                "현재가": d["nowPrice"],
                "전일비": d["prevChangePrice"],
                "등락률(%)": d["prevChangeRate"],
                "거래량": d["tradeVolume"],
                "거래대금(백만)": to_unit(d["tradeAmount"], 1_000_000),
                "시가총액(억)": to_unit(d["marketSum"], 100_000_000),
                "PER": d["per"],
                "PBR": d["pbr"],
                "외국인비율(%)": d["frgnHoldRate"],
            })
        log(f"  page {page}: {len(data)}건 중 코스피200 {len(rows) - before}건 (누적 {len(rows)})")
        page += 1
        time.sleep(0.3)

    missing = kospi200 - seen
    if missing:
        log(f"  priceTop 목록에 없는 종목 {len(missing)}개: {sorted(missing)}")
    return rows


def save_csv(path, rows):
    if not rows:
        return
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않음
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _excel_value(value, as_text=False):
    """'1,234' 같은 문자열은 엑셀에서 계산할 수 있게 숫자로 변환"""
    if as_text or value in ("", None):
        return value
    try:
        num = float(str(value).replace(",", ""))
    except ValueError:
        return value
    return int(num) if num.is_integer() and "." not in str(value) else num


def _write_sheet(ws, rows, title):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    columns = list(rows[0].keys())
    text_columns = {"종목코드", "날짜", "종목명"}
    signed_columns = {"전일비", "등락률(%)"}

    # 1행: 제목, 3행: 머리글, 4행부터 데이터
    ws["A1"] = title
    ws["A1"].font = Font(size=16, bold=True, color="1F2A44")
    ws.row_dimensions[1].height = 28

    header_fill = PatternFill("solid", fgColor="1F2A44")
    stripe_fill = PatternFill("solid", fgColor="F3F6FB")
    thin = Side(style="thin", color="D5DCE8")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    for c, col in enumerate(columns, 1):
        cell = ws.cell(row=3, column=c, value=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    ws.row_dimensions[3].height = 22

    for r, row in enumerate(rows, 4):
        for c, col in enumerate(columns, 1):
            value = _excel_value(row[col], as_text=col in text_columns)
            cell = ws.cell(row=r, column=c, value=value)
            cell.border = border
            if r % 2 == 1:
                cell.fill = stripe_fill
            if isinstance(value, (int, float)):
                cell.number_format = "#,##0" if isinstance(value, int) else "#,##0.00"
                if col in signed_columns and value:
                    # 국내 증시 관례: 상승 빨강, 하락 파랑
                    cell.font = Font(bold=True, color="D60000" if value > 0 else "0051C7")
            else:
                cell.alignment = Alignment(horizontal="center" if col != "종목명" else "left")

    for c, col in enumerate(columns, 1):
        longest = max([len(str(col)) * 2] + [len(str(row[col])) for row in rows])
        ws.column_dimensions[get_column_letter(c)].width = min(max(longest + 3, 8), 24)

    ws.freeze_panes = "A4"  # 머리글 고정
    ws.auto_filter.ref = f"A3:{get_column_letter(len(columns))}{len(rows) + 3}"


def save_excel(path, stocks, daily, summary=None):
    """종목/일별 시세를 시트별로 나눠 서식을 입힌 엑셀(.xlsx) 파일로 저장"""
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    stamp = f" ({summary['time'].replace('T', ' ')[:16]} 기준)" if summary else ""
    if stocks:
        _write_sheet(wb.create_sheet("코스피200 종목"), stocks, f"코스피200 종목 - 거래대금 순{stamp}")
    if daily:
        _write_sheet(wb.create_sheet("지수 일별 시세"), daily, "코스피200 지수 일별 시세")
    wb.save(path)


def main():
    s = fetch_index_summary()
    print(f"[{s['name']}] {s['price']}  {s['change']} ({s['rate']}%)  {s['status']} {s['time']}")

    daily = fetch_index_daily(pages=1)
    save_csv("kospi200_index_daily.csv", daily)
    print(f"\n일별 시세 {len(daily)}건 -> kospi200_index_daily.csv")
    for r in daily[:5]:
        print(f"  {r['날짜']}  종가 {r['종가']:>8}  {r['등락률(%)']:>6}%")

    print("\n편입종목 수집 (priceTop)")
    stocks = fetch_constituents()
    save_csv("kospi200_stocks.csv", stocks)
    print(f"\n편입종목 {len(stocks)}개 -> kospi200_stocks.csv")
    for r in stocks[:10]:
        print(f"  {r['순위']:>3}. {r['종목명']:<10} {r['현재가']:>9}  {r['등락률(%)']:>6}%  거래대금 {r['거래대금(백만)']:,}백만")

    save_excel("kospi200.xlsx", stocks, daily, s)
    print("\n엑셀 저장 -> kospi200.xlsx")


if __name__ == "__main__":
    main()
