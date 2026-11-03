"""
코스피200 크롤러 GUI (PyQt6)

kospi200_crawler.py 의 수집 함수를 백그라운드 스레드에서 실행하고
결과를 대시보드 형태로 보여준다.

  - 상단 카드: 코스피200 지수 현재가 / 등락 / 최근 50일 추이 그래프
  - 요약 카드: 상승·하락·보합 종목 수, 거래대금 합계
  - [데이터 수집]: 지수 시세 + 일별 시세 + 코스피200 종목 200개 수집
  - [엑셀 저장]: 종목/일별 시세를 시트별로 나눈 .xlsx 저장 (openpyxl 필요)
  - [CSV 저장]: 현재 탭의 표를 CSV로 저장
  - 검색창: 종목명/종목코드로 표 필터링, 열 머리글 클릭으로 정렬

실행:  python kospi200_gui.py
"""

import csv
import sys
from datetime import datetime

from PyQt6.QtCore import QPointF, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import kospi200_crawler as crawler

# 국내 증시 관례: 상승 빨강, 하락 파랑 (어두운 배경에서 잘 보이도록 밝은 톤)
RISE = "#ff4d6a"
FALL = "#4d9bff"
FLAT = "#a7b0c8"
RISE_COLOR = QColor(RISE)
FALL_COLOR = QColor(FALL)

# 등락에 따라 색을 입힐 열
SIGNED_COLUMNS = {"전일비", "등락률(%)"}

STYLE = f"""
* {{
    font-family: "Malgun Gothic", "Segoe UI";
    color: #e6e9f5;
}}
QMainWindow, #root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b1020, stop:1 #141a33);
}}
#card {{
    background: #1a2140;
    border: 1px solid #262f57;
    border-radius: 14px;
}}
#hero {{
    border-radius: 18px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #4f46e5, stop:0.55 #7c3aed, stop:1 #db2777);
}}
#hero QLabel {{ background: transparent; color: white; }}
#heroTitle {{ font-size: 15px; font-weight: 700; color: rgba(255,255,255,0.85); }}
#heroPrice {{ font-size: 44px; font-weight: 800; }}
#heroTime {{ font-size: 12px; color: rgba(255,255,255,0.75); }}
#changePill {{
    font-size: 15px; font-weight: 700;
    padding: 4px 14px; border-radius: 13px;
    background: rgba(255,255,255,0.22);
}}
#statusBadge {{
    font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 10px;
    background: rgba(0,0,0,0.25);
}}
#statTitle {{ font-size: 12px; color: #8f99bd; }}
#statValue {{ font-size: 24px; font-weight: 800; }}
#statSub {{ font-size: 11px; color: #6f7aa3; }}

QPushButton {{
    border: none; border-radius: 10px;
    padding: 10px 20px; font-size: 13px; font-weight: 700; color: white;
}}
QPushButton:disabled {{ background: #2a3156; color: #6b7499; }}
#crawlButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
}}
#crawlButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818cf8, stop:1 #c084fc);
}}
#excelButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
}}
#excelButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #34d399);
}}
#csvButton {{ background: transparent; border: 1px solid #3b4578; color: #c7cdea; }}
#csvButton:hover {{ background: #232b52; }}
#csvButton:disabled {{ border-color: #2a3156; background: transparent; }}

QLineEdit {{
    background: #1a2140; border: 1px solid #2b3560; border-radius: 10px;
    padding: 9px 14px; font-size: 13px; selection-background-color: #6366f1;
}}
QLineEdit:focus {{ border: 1px solid #818cf8; }}

QProgressBar {{
    background: #1a2140; border: none; border-radius: 4px; max-height: 8px;
}}
QProgressBar::chunk {{
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #ec4899);
}}

QTabWidget::pane {{
    border: 1px solid #262f57; border-radius: 14px; background: #151b36; top: -1px;
}}
QTabBar::tab {{
    background: transparent; color: #8f99bd;
    padding: 9px 22px; margin-right: 6px; border-radius: 10px;
    font-size: 13px; font-weight: 700;
}}
QTabBar::tab:selected {{ background: #2a3270; color: white; }}
QTabBar::tab:hover:!selected {{ background: #1d2448; color: #c7cdea; }}

QTableWidget {{
    background: #151b36; alternate-background-color: #19203f;
    border: none; border-radius: 14px; gridline-color: transparent;
    font-size: 13px; selection-background-color: #34407f; selection-color: white;
}}
QHeaderView::section {{
    background: #1d2448; color: #aab3d6; border: none;
    border-bottom: 2px solid #6366f1;
    padding: 9px 8px; font-size: 12px; font-weight: 700;
}}
QTableCornerButton::section {{ background: #1d2448; border: none; }}
QPlainTextEdit {{
    background: #0f1430; border: none; border-radius: 14px; padding: 10px;
    font-family: Consolas; font-size: 12px; color: #9fe6b8;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #333d6e; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #4a5596; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
QScrollBar::handle:horizontal {{ background: #333d6e; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
#statusText {{ color: #8f99bd; font-size: 12px; }}
QMessageBox {{ background: #1a2140; }}
"""


def to_number(text):
    """'1,234' / '-5.43' / '' 같은 문자열을 정렬용 숫자로"""
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return None


def format_number(value):
    """정수는 천 단위 쉼표, 소수는 그대로"""
    num = to_number(value)
    if num is None:
        return str(value)
    if num.is_integer() and "." not in str(value):
        return f"{int(num):,}"
    return str(value)


def add_shadow(widget, blur=30, alpha=120):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


class SortableItem(QTableWidgetItem):
    """숫자 열은 숫자 크기로 정렬되는 셀"""

    def __init__(self, text, number=None):
        super().__init__(text)
        self.number = number

    def __lt__(self, other):
        if isinstance(other, SortableItem) and self.number is not None and other.number is not None:
            return self.number < other.number
        return super().__lt__(other)


class Sparkline(QWidget):
    """최근 일별 종가 추이를 그리는 작은 선 그래프"""

    def __init__(self):
        super().__init__()
        self.values = []
        self.setMinimumSize(320, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_values(self, values):
        self.values = values
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, pad = self.width(), self.height(), 8

        if len(self.values) < 2:
            p.setPen(QColor(255, 255, 255, 140))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "수집하면 최근 추이가 표시됩니다")
            return

        lo, hi = min(self.values), max(self.values)
        span = (hi - lo) or 1
        step = (w - pad * 2) / (len(self.values) - 1)
        points = [
            QPointF(pad + i * step, pad + (h - pad * 2) * (1 - (v - lo) / span))
            for i, v in enumerate(self.values)
        ]

        line = QPainterPath(points[0])
        for pt in points[1:]:
            line.lineTo(pt)

        # 선 아래를 반투명 그라데이션으로 채움
        area = QPainterPath(line)
        area.lineTo(points[-1].x(), h)
        area.lineTo(points[0].x(), h)
        area.closeSubpath()
        fill = QLinearGradient(0, 0, 0, h)
        fill.setColorAt(0, QColor(255, 255, 255, 110))
        fill.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(area, QBrush(fill))

        p.setPen(QPen(QColor("white"), 2.4))
        p.drawPath(line)

        # 마지막 지점 강조
        p.setBrush(QColor("white"))
        p.setPen(QPen(QColor(255, 255, 255, 90), 6))
        p.drawEllipse(points[-1], 4, 4)

        p.setPen(QColor(255, 255, 255, 170))
        p.setFont(QFont("Malgun Gothic", 8))
        p.drawText(pad, 12, f"최고 {hi:,.2f}")
        p.drawText(pad, h - 2, f"최저 {lo:,.2f}")


class StatCard(QFrame):
    """요약 수치 카드 (왼쪽에 색 띠)"""

    def __init__(self, title, accent):
        super().__init__()
        self.setObjectName("card")
        self.setStyleSheet(f"#card {{ border-left: 4px solid {accent}; }}")
        add_shadow(self, blur=24, alpha=90)

        self.title = QLabel(title)
        self.title.setObjectName("statTitle")
        self.value = QLabel("-")
        self.value.setObjectName("statValue")
        self.value.setStyleSheet(f"color: {accent};")
        self.sub = QLabel("")
        self.sub.setObjectName("statSub")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.sub)

    def set(self, value, sub=""):
        self.value.setText(value)
        self.sub.setText(sub)


class CrawlWorker(QThread):
    """네트워크 요청이 UI를 멈추지 않도록 별도 스레드에서 수집"""

    # dict/list로 선언하면 Qt가 QVariantMap으로 바꾸면서 키 순서가 정렬돼 열 순서가 섞이므로
    # object로 넘겨 파이썬 객체를 그대로 전달한다
    log = pyqtSignal(str)
    summary_ready = pyqtSignal(object)
    daily_ready = pyqtSignal(object)
    stocks_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.log.emit("코스피200 지수 시세 조회")
            self.summary_ready.emit(crawler.fetch_index_summary())

            self.log.emit("코스피200 일별 시세 조회")
            daily = crawler.fetch_index_daily(pages=1)
            self.log.emit(f"  일별 시세 {len(daily)}건")
            self.daily_ready.emit(daily)

            self.log.emit("코스피200 종목 수집 (priceTop)")
            stocks = crawler.fetch_constituents(log=self.log.emit)
            self.log.emit(f"  종목 {len(stocks)}개 수집 완료")
            self.stocks_ready.emit(stocks)
        except Exception as e:  # 네트워크 오류, API 형식 변경 등
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KOSPI 200 Dashboard")
        self.resize(1320, 880)
        self.worker = None
        self.data = {"stocks": [], "daily": [], "summary": None}

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 20, 22, 14)
        layout.setSpacing(16)

        layout.addWidget(self.build_hero())
        layout.addLayout(self.build_stats())
        layout.addLayout(self.build_toolbar())
        layout.addWidget(self.build_tabs(), 1)

        self.status = QLabel("상단의 [데이터 수집] 버튼을 눌러 시작하세요.")
        self.status.setObjectName("statusText")
        layout.addWidget(self.status)

    # ---------- 레이아웃 ----------

    def build_hero(self):
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setMinimumHeight(170)
        add_shadow(hero, blur=40, alpha=150)

        self.index_name = QLabel("KOSPI 200 · 코스피 200")
        self.index_name.setObjectName("heroTitle")
        self.market_badge = QLabel("● 대기")
        self.market_badge.setObjectName("statusBadge")
        self.index_price = QLabel("—")
        self.index_price.setObjectName("heroPrice")
        self.change_pill = QLabel("수집 전")
        self.change_pill.setObjectName("changePill")
        self.index_time = QLabel("")
        self.index_time.setObjectName("heroTime")

        title_row = QHBoxLayout()
        title_row.addWidget(self.index_name)
        title_row.addWidget(self.market_badge)
        title_row.addStretch()

        change_row = QHBoxLayout()
        change_row.addWidget(self.change_pill)
        change_row.addSpacing(10)
        change_row.addWidget(self.index_time)
        change_row.addStretch()

        left = QVBoxLayout()
        left.addLayout(title_row)
        left.addWidget(self.index_price)
        left.addLayout(change_row)
        left.addStretch()

        self.crawl_button = QPushButton("⟳  데이터 수집")
        self.crawl_button.setObjectName("crawlButton")
        self.crawl_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crawl_button.clicked.connect(self.start_crawl)
        # 히어로 카드 위에서도 버튼이 묻히지 않도록 흰 테두리
        self.crawl_button.setStyleSheet("border: 1px solid rgba(255,255,255,0.55);")

        chart_caption = QLabel("최근 50거래일 종가 추이")
        chart_caption.setObjectName("heroTime")
        self.sparkline = Sparkline()

        right = QVBoxLayout()
        top_right = QHBoxLayout()
        top_right.addWidget(chart_caption)
        top_right.addStretch()
        top_right.addWidget(self.crawl_button)
        right.addLayout(top_right)
        right.addWidget(self.sparkline, 1)

        box = QHBoxLayout(hero)
        box.setContentsMargins(28, 22, 28, 22)
        box.setSpacing(30)
        box.addLayout(left, 1)
        box.addLayout(right, 1)
        return hero

    def build_stats(self):
        self.stat_rise = StatCard("상승 종목", RISE)
        self.stat_fall = StatCard("하락 종목", FALL)
        self.stat_flat = StatCard("보합 종목", FLAT)
        self.stat_amount = StatCard("거래대금 합계", "#c084fc")
        self.stat_top = StatCard("거래대금 1위", "#34d399")

        grid = QGridLayout()
        grid.setSpacing(14)
        for i, card in enumerate(
            [self.stat_rise, self.stat_fall, self.stat_flat, self.stat_amount, self.stat_top]
        ):
            grid.addWidget(card, 0, i)
        return grid

    def build_toolbar(self):
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  종목명 또는 종목코드 검색")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(180)
        self.progress.setTextVisible(False)
        self.progress.hide()

        self.excel_button = QPushButton("▦  엑셀 저장")
        self.excel_button.setObjectName("excelButton")
        self.excel_button.setEnabled(False)
        self.excel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.excel_button.clicked.connect(self.save_excel)

        self.csv_button = QPushButton("CSV 저장")
        self.csv_button.setObjectName("csvButton")
        self.csv_button.setEnabled(False)
        self.csv_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.csv_button.clicked.connect(self.save_csv)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.progress)
        bar.addWidget(self.excel_button)
        bar.addWidget(self.csv_button)
        return bar

    def build_tabs(self):
        self.stock_table = self.make_table()
        self.daily_table = self.make_table()
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.stock_table, "📈  코스피200 종목")
        self.tabs.addTab(self.daily_table, "📅  지수 일별 시세")
        self.tabs.addTab(self.log_view, "📝  로그")
        return self.tabs

    @staticmethod
    def make_table():
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(34)
        return table

    # ---------- 수집 ----------

    def start_crawl(self):
        self.crawl_button.setEnabled(False)
        self.crawl_button.setText("수집 중...")
        self.excel_button.setEnabled(False)
        self.csv_button.setEnabled(False)
        self.progress.setRange(0, 0)  # 진행률을 알 수 없으므로 움직이는 바 표시
        self.progress.show()
        self.status.setText("네이버 증권에서 데이터를 가져오는 중...")
        self.append_log(f"=== 수집 시작 {datetime.now():%Y-%m-%d %H:%M:%S} ===")

        self.worker = CrawlWorker()
        self.worker.log.connect(self.append_log)
        self.worker.summary_ready.connect(self.show_summary)
        self.worker.daily_ready.connect(self.show_daily)
        self.worker.stocks_ready.connect(self.show_stocks)
        self.worker.failed.connect(self.crawl_failed)
        self.worker.finished.connect(self.crawl_finished)
        self.worker.start()

    def crawl_finished(self):
        self.crawl_button.setEnabled(True)
        self.crawl_button.setText("⟳  다시 수집")
        has_data = bool(self.data["stocks"] or self.data["daily"])
        self.excel_button.setEnabled(has_data)
        self.csv_button.setEnabled(has_data)
        self.progress.hide()

    def crawl_failed(self, message):
        self.append_log(f"오류: {message}")
        self.status.setText("수집 실패")
        QMessageBox.critical(self, "수집 실패", f"데이터를 가져오지 못했습니다.\n\n{message}")

    def append_log(self, text):
        self.log_view.appendPlainText(text)

    # ---------- 화면 갱신 ----------

    def show_summary(self, s):
        self.data["summary"] = s
        self.index_name.setText(f"KOSPI 200 · {s['name']}")
        self.index_price.setText(s["price"])
        change = to_number(s["change"]) or 0
        arrow = "▲" if change > 0 else "▼" if change < 0 else "―"
        sign = "+" if change > 0 else ""
        self.change_pill.setText(f"{arrow} {sign}{s['change']}  ({sign}{s['rate']}%)")
        tint = "rgba(255,77,106,0.45)" if change > 0 else "rgba(77,155,255,0.45)" if change < 0 else "rgba(255,255,255,0.22)"
        self.change_pill.setStyleSheet(f"background: {tint};")
        self.index_time.setText(s["time"].replace("T", " ")[:16] + " 기준")
        is_open = s["status"] == "OPEN"
        self.market_badge.setText("● 장중" if is_open else "● 장마감")
        self.market_badge.setStyleSheet(f"color: {'#6ee7b7' if is_open else '#e2e8f0'};")

    def show_daily(self, rows):
        self.data["daily"] = rows
        self.fill_table(self.daily_table, rows)
        closes = [to_number(r["종가"]) for r in reversed(rows)]  # 오래된 날 → 최근 순
        self.sparkline.set_values([v for v in closes if v is not None])

    def show_stocks(self, rows):
        self.data["stocks"] = rows
        self.fill_table(self.stock_table, rows)
        self.update_stats(rows)
        self.apply_filter(self.search.text())

    def update_stats(self, rows):
        rates = [to_number(r["등락률(%)"]) or 0 for r in rows]
        total = len(rows) or 1
        rise = sum(r > 0 for r in rates)
        fall = sum(r < 0 for r in rates)
        flat = len(rows) - rise - fall
        self.stat_rise.set(f"{rise}", f"전체의 {rise / total:.0%}")
        self.stat_fall.set(f"{fall}", f"전체의 {fall / total:.0%}")
        self.stat_flat.set(f"{flat}", f"전체의 {flat / total:.0%}")

        amount = sum(r["거래대금(백만)"] or 0 for r in rows)  # 백만 원
        self.stat_amount.set(f"{amount / 1_000_000:,.1f}조", f"{amount:,} 백만원")
        if rows:
            top = rows[0]
            self.stat_top.set(top["종목명"], f"{top['거래대금(백만)'] / 1_000_000:,.2f}조 · {top['등락률(%)']}%")

    def fill_table(self, table, rows):
        table.setSortingEnabled(False)  # 채우는 도중 정렬되면 행이 섞임
        table.clear()
        if not rows:
            table.setRowCount(0)
            return
        columns = list(rows[0].keys())
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(rows))
        bold = QFont("Malgun Gothic", 10, QFont.Weight.Bold)

        for r, row in enumerate(rows):
            for c, col in enumerate(columns):
                value = "" if row[col] is None else row[col]  # PER 등 값이 없는 항목
                number = to_number(value)
                if col in ("종목코드", "날짜"):  # 숫자처럼 보여도 문자열로 취급
                    number = None
                text = format_number(value) if number is not None else str(value)
                if col == "등락률(%)" and number is not None:
                    text = f"{'+' if number > 0 else ''}{number:.2f}%"
                item = SortableItem(text, number)
                if col in ("순위", "종목코드", "날짜"):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif number is not None:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == "종목명":
                    item.setFont(bold)
                if col in SIGNED_COLUMNS and number:
                    color = RISE_COLOR if number > 0 else FALL_COLOR
                    item.setForeground(color)
                    if col == "등락률(%)":
                        # 등락 폭이 클수록 진한 배경
                        tint = QColor(color)
                        tint.setAlpha(min(40 + int(abs(number) * 18), 150))
                        item.setBackground(tint)
                        item.setFont(bold)
                table.setItem(r, c, item)

        table.setSortingEnabled(True)
        header = table.horizontalHeader()
        header.setMinimumSectionSize(78)  # 셀 여백 대신 최소 폭으로 숨 쉴 공간 확보
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)

    def apply_filter(self, text):
        """종목명/종목코드에 검색어가 포함된 행만 표시"""
        text = text.strip().lower()
        table = self.stock_table
        columns = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        targets = [columns.index(c) for c in ("종목명", "종목코드") if c in columns]
        shown = 0
        for r in range(table.rowCount()):
            match = not text or any(
                text in table.item(r, c).text().lower() for c in targets if table.item(r, c)
            )
            table.setRowHidden(r, not match)
            shown += match
        if text and self.data["stocks"]:
            self.status.setText(f"검색 결과 {shown}개 / 전체 {len(self.data['stocks'])}개")
        elif self.data["stocks"]:
            self.status.setText(f"코스피200 종목 {len(self.data['stocks'])}개 · 거래대금 순 · 열 머리글을 눌러 정렬")

    # ---------- 저장 ----------

    def save_excel(self):
        default = f"kospi200_{datetime.now():%Y%m%d_%H%M}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", default, "Excel 파일 (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            crawler.save_excel(path, self.data["stocks"], self.data["daily"], self.data["summary"])
        except ImportError:
            QMessageBox.warning(self, "엑셀 저장", "openpyxl 이 필요합니다.\n\npip install openpyxl")
            return
        except PermissionError:
            QMessageBox.warning(self, "엑셀 저장", "파일이 엑셀에서 열려 있으면 닫고 다시 시도하세요.")
            return
        self.append_log(f"엑셀 저장: {path}")
        self.status.setText(f"✔ 엑셀 저장 완료: {path}")

    def save_csv(self):
        if self.tabs.currentWidget() is self.daily_table:
            rows, default = self.data["daily"], "kospi200_index_daily.csv"
        else:
            rows, default = self.data["stocks"], "kospi200_stocks.csv"
        if not rows:
            QMessageBox.information(self, "CSV 저장", "저장할 데이터가 없습니다.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", default, "CSV 파일 (*.csv)")
        if not path:
            return
        # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않음
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        self.append_log(f"CSV 저장: {path} ({len(rows)}행)")
        self.status.setText(f"✔ CSV 저장 완료: {path}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 플랫폼 기본 스타일보다 스타일시트가 일관되게 적용됨
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
