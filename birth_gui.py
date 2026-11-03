"""대한민국 출생아수 분석 GUI (PyQt6)

사용법: python birth_gui.py [엑셀파일경로]
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.ticker as mticker
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from birth_analysis import DEFAULT_PATH, OUT_DIR, analyze, load_and_clean, quality_report
from birth_line_chart import plot_births

BLUE, ORANGE, GREEN, RED = "#2a6fdb", "#d9480f", "#2f9e44", "#c92a2a"


class ChartWidget(QWidget):
    """matplotlib Figure + 툴바(확대/이동/저장)를 담은 위젯."""

    def __init__(self):
        super().__init__()
        self.figure = Figure(figsize=(10, 5), layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)

    def new_axes(self):
        self.figure.clear()
        return self.figure.add_subplot()


def style_axes(ax, title, ylabel):
    ax.set_title(title, fontsize=13, pad=10)
    ax.set_xlabel("연도")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


class MainWindow(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.df = None
        self.results = {}
        self.setWindowTitle("대한민국 출생아수 분석")
        self.resize(1250, 800)

        self._build_menu()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_summary_tab(), "요약")
        self.tabs.addTab(self._build_births_tab(), "출생아수 추이")
        self.tabs.addTab(self._build_indicator_tab(), "지표별 그래프")
        self.tabs.addTab(self._build_table_tab(), "정제 데이터")
        self.tabs.addTab(self._build_report_tab(), "분석 리포트")

        self.statusBar().showMessage("엑셀 파일을 열어주세요 (파일 → 열기)")
        path = Path(path) if path else DEFAULT_PATH
        if path.exists():
            self.load_file(path)

    # ---------- UI 구성 ----------
    def _build_menu(self):
        menu = self.menuBar().addMenu("파일")
        for text, slot, shortcut in [
            ("열기...", self.open_file, "Ctrl+O"),
            ("결과 내보내기...", self.export_results, "Ctrl+S"),
            ("종료", self.close, "Ctrl+Q"),
        ]:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            menu.addAction(action)

    def _build_summary_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        top = QHBoxLayout()
        self.file_label = QLabel("파일: -")
        open_btn = QPushButton("엑셀 파일 열기")
        open_btn.clicked.connect(self.open_file)
        export_btn = QPushButton("결과 내보내기")
        export_btn.clicked.connect(self.export_results)
        top.addWidget(self.file_label, 1)
        top.addWidget(open_btn)
        top.addWidget(export_btn)
        layout.addLayout(top)

        box = QGroupBox("핵심 지표")
        self.cards = QGridLayout(box)
        layout.addWidget(box)

        self.summary_chart = ChartWidget()
        layout.addWidget(self.summary_chart, 1)
        return w

    def _build_births_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        ctrl = QHBoxLayout()
        self.start_spin, self.end_spin = QSpinBox(), QSpinBox()
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(1970, 1970)
            spin.valueChanged.connect(self.draw_births)
        ctrl.addWidget(QLabel("시작 연도"))
        ctrl.addWidget(self.start_spin)
        ctrl.addWidget(QLabel("종료 연도"))
        ctrl.addWidget(self.end_spin)
        reset_btn = QPushButton("전체 기간")
        reset_btn.clicked.connect(self.reset_range)
        ctrl.addWidget(reset_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)
        self.births_chart = ChartWidget()
        layout.addWidget(self.births_chart, 1)
        return w

    def _build_indicator_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        ctrl = QHBoxLayout()
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems([
            "합계출산율", "출생아수 전년 대비 증감률", "자연증가건수",
            "조출생률 vs 자연증가율", "출생성비", "연대별 평균 출생아수",
        ])
        self.indicator_combo.currentIndexChanged.connect(self.draw_indicator)
        ctrl.addWidget(QLabel("지표 선택"))
        ctrl.addWidget(self.indicator_combo)
        ctrl.addStretch()
        layout.addLayout(ctrl)
        self.indicator_chart = ChartWidget()
        layout.addWidget(self.indicator_chart, 1)
        return w

    def _build_table_tab(self):
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return self.table

    def _build_report_tab(self):
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setFont(QFont("D2Coding, Consolas, Malgun Gothic", 10))
        self.report.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return self.report

    # ---------- 데이터 처리 ----------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "출생아수 엑셀 파일 열기", str(DEFAULT_PATH.parent), "Excel (*.xlsx *.xls)")
        if path:
            self.load_file(Path(path))

    def load_file(self, path):
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):  # 기존 분석 함수의 콘솔 출력을 리포트로 사용
                df = load_and_clean(path)
                quality_report(df)
                results = analyze(df)
        except Exception as e:
            QMessageBox.critical(self, "불러오기 실패", f"파일을 처리할 수 없습니다.\n\n{e}")
            return

        self.df, self.results = df, results
        self.file_label.setText(f"파일: {path}")
        self.report.setPlainText(buf.getvalue())
        self.fill_table()
        self.fill_cards()
        self.draw_summary()

        lo, hi = int(df.index.min()), int(df.index.max())
        for spin in (self.start_spin, self.end_spin):
            spin.blockSignals(True)
            spin.setRange(lo, hi)
            spin.blockSignals(False)
        self.reset_range()
        self.draw_indicator()
        self.statusBar().showMessage(f"{lo}~{hi}년 {len(df)}개 연도 데이터 로드 완료")

    def fill_table(self):
        df = self.df
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns) + 1)
        self.table.setHorizontalHeaderLabels(["연도", *df.columns])
        for r, (year, row) in enumerate(df.iterrows()):
            cells = [str(year)] + [
                f"{v:,}" if col in ("출생아수", "자연증가건수") else f"{v:g}"
                for col, v in row.items()
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 2 and row["자연증가건수"] < 0:
                    item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, c, item)

    def fill_cards(self):
        while self.cards.count():
            self.cards.takeAt(0).widget().deleteLater()
        df = self.df
        b, tfr = df["출생아수"].astype(float), df["합계출산율"]
        first, last = df.index.min(), df.index.max()
        neg = df[df["자연증가건수"] < 0]
        items = [
            (f"{last}년 출생아수", f"{b[last]:,.0f}명", f"전년 대비 {b.pct_change()[last]:+.1%}"),
            (f"{last}년 합계출산율", f"{tfr[last]:.3f}명", f"최저 {tfr.min():.3f} ({tfr.idxmin()}년)"),
            ("최대 출생아수", f"{b.max():,.0f}명", f"{b.idxmax()}년"),
            ("최소 출생아수", f"{b.min():,.0f}명", f"{b.idxmin()}년"),
            (f"{first}→{last} 변화", f"{b[last] / b[first] - 1:+.1%}", "출생아수 누적 변화율"),
            ("인구 자연감소", f"{neg.index.min()}년~" if len(neg) else "없음",
             f"누적 {-neg['자연증가건수'].sum():,}명" if len(neg) else ""),
        ]
        for i, (title, value, sub) in enumerate(items):
            card = QLabel(
                f"<div style='color:#666;font-size:11px'>{title}</div>"
                f"<div style='font-size:20px;font-weight:600'>{value}</div>"
                f"<div style='color:#888;font-size:11px'>{sub}</div>")
            card.setStyleSheet("QLabel{border:1px solid #ddd;border-radius:6px;padding:8px;}")
            self.cards.addWidget(card, 0, i)

    # ---------- 그래프 ----------
    def reset_range(self):
        if self.df is None:
            return
        self.start_spin.blockSignals(True)
        self.start_spin.setValue(self.start_spin.minimum())
        self.start_spin.blockSignals(False)
        self.end_spin.setValue(self.end_spin.maximum())
        self.draw_births()

    def draw_births(self):
        if self.df is None:
            return
        start, end = self.start_spin.value(), self.end_spin.value()
        if start >= end:
            self.statusBar().showMessage("시작 연도는 종료 연도보다 작아야 합니다")
            return
        ax = self.births_chart.new_axes()
        plot_births(self.df, start, end, ax=ax)
        self.births_chart.canvas.draw()

    def draw_summary(self):
        """요약 탭: 출생아수(막대) + 합계출산율(선) 이중축."""
        df = self.df
        ax = self.summary_chart.new_axes()
        ax.bar(df.index, df["출생아수"].astype(float), color=BLUE, alpha=0.35, label="출생아수")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 10000:,.0f}만"))
        style_axes(ax, "출생아수와 합계출산율", "출생아수 (명)")
        ax2 = ax.twinx()
        ax2.plot(df.index, df["합계출산율"], color=ORANGE, linewidth=2, label="합계출산율")
        ax2.axhline(2.1, color="gray", linestyle="--", linewidth=1)
        ax2.text(df.index.max(), 2.15, "인구대체수준 2.1", ha="right", fontsize=8, color="gray")
        ax2.set_ylabel("합계출산율 (명)")
        ax2.spines[["top"]].set_visible(False)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="upper right")
        self.summary_chart.canvas.draw()

    def draw_indicator(self):
        if self.df is None:
            return
        df, name = self.df, self.indicator_combo.currentText()
        ax = self.indicator_chart.new_axes()
        x = df.index

        if name == "합계출산율":
            ax.plot(x, df["합계출산율"], color=ORANGE, linewidth=2, marker="o", markersize=3)
            for th, label in [(2.1, "인구대체수준 2.1"), (1.3, "초저출산 1.3"), (1.0, "1.0")]:
                ax.axhline(th, color="gray", linestyle="--", linewidth=1)
                ax.text(x.max(), th + 0.05, label, ha="right", fontsize=8, color="gray")
            style_axes(ax, "합계출산율 추이", "합계출산율 (명)")
        elif name == "출생아수 전년 대비 증감률":
            pct = df["출생아수"].astype(float).pct_change() * 100
            ax.bar(x, pct, color=[GREEN if v >= 0 else RED for v in pct.fillna(0)])
            ax.axhline(0, color="black", linewidth=0.8)
            style_axes(ax, "출생아수 전년 대비 증감률", "증감률 (%)")
        elif name == "자연증가건수":
            v = df["자연증가건수"].astype(float)
            ax.bar(x, v, color=[BLUE if n >= 0 else RED for n in v])
            ax.axhline(0, color="black", linewidth=0.8)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda n, _: f"{n / 10000:,.0f}만"))
            style_axes(ax, "자연증가건수 (출생 - 사망)", "명")
        elif name == "조출생률 vs 자연증가율":
            ax.plot(x, df["조출생률"], color=BLUE, linewidth=2, label="조출생률")
            ax.plot(x, df["자연증가율"], color=GREEN, linewidth=2, label="자연증가율")
            ax.axhline(0, color="black", linewidth=0.8)
            ax.legend()
            style_axes(ax, "조출생률과 자연증가율 (인구 천 명당)", "천 명당")
        elif name == "출생성비":
            ax.plot(x, df["출생성비"], color=BLUE, linewidth=2, marker="o", markersize=3)
            ax.axhspan(103, 107, color=GREEN, alpha=0.12, label="정상범위 103~107")
            ax.legend()
            style_axes(ax, "출생성비 (여아 100명당 남아 수)", "명")
        elif name == "연대별 평균 출생아수":
            decade = self.results["연대별"]["출생아수"]
            bars = ax.bar(decade.index, decade.values, color=BLUE)
            ax.bar_label(bars, labels=[f"{v / 10000:,.1f}만" for v in decade.values])
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda n, _: f"{n / 10000:,.0f}만"))
            style_axes(ax, "연대별 평균 출생아수", "출생아수 (명)")
            ax.set_xlabel("연대")
        self.indicator_chart.canvas.draw()

    # ---------- 내보내기 ----------
    def export_results(self):
        if self.df is None:
            QMessageBox.information(self, "알림", "먼저 데이터를 불러오세요.")
            return
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", str(OUT_DIR))
        if not folder:
            return
        import pandas as pd

        out = Path(folder)
        self.df.to_csv(out / "births_clean.csv", encoding="utf-8-sig")
        with pd.ExcelWriter(out / "births_analysis.xlsx") as writer:
            self.df.to_excel(writer, sheet_name="정제데이터")
            for name, table in self.results.items():
                table.to_excel(writer, sheet_name=name)
        self.births_chart.figure.savefig(out / "births_line_chart.png", dpi=150)
        (out / "analysis_report.txt").write_text(self.report.toPlainText(), encoding="utf-8")
        QMessageBox.information(self, "저장 완료", f"결과를 저장했습니다.\n{out}")


def main():
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
    matplotlib.rcParams["axes.unicode_minus"] = False
    app = QApplication(sys.argv)
    app.setFont(QFont("Malgun Gothic", 10))
    win = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
