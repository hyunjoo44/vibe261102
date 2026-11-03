"""오마이뉴스 기사 크롤러 GUI (PyQt6 + requests + BeautifulSoup4)

사용법:
    pip install PyQt6 requests beautifulsoup4 openpyxl
    python ohmynews_crawler.py
"""
import os
import sys

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

DEFAULT_URL = (
    "https://www.ohmynews.com/NWS_Web/View/at_pg.aspx"
    "?CNTN_CD=A0003281206&CMPT_CD=P0010"
    "&utm_source=naver&utm_medium=newsearch&utm_campaign=naver_news"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def text_of(soup, selector):
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def crawl_article(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    title = text_of(soup, "h1.article_tit")
    subtitle = text_of(soup, "h2.article_subtit")
    reporter = text_of(soup, ".info-list .lk_my strong")
    dates = [d.get_text(strip=True) for d in soup.select(".atc_intro_header span.date")]
    tags = [t.get_text(strip=True) for t in soup.select(".tag_area a")]

    body = soup.select_one("div.at_contents")
    paragraphs = []
    if body:
        # 광고, 스크립트, 사진/캡션 영역 제거
        for junk in body.select("script, style, iframe, figure, .pho-center, [class^='V0'], .atc_tis_ad"):
            junk.decompose()
        # <br> 기준으로 문단 분리
        for br in body.find_all("br"):
            br.replace_with("\n")
        text = body.get_text()
        paragraphs = [line.strip() for line in text.split("\n") if line.strip()]

    return {
        "url": url,
        "title": title,
        "subtitle": subtitle,
        "reporter": reporter,
        "published": dates[0] if dates else "",
        "updated": dates[1] if len(dates) > 1 else "",
        "tags": tags,
        "content": "\n\n".join(paragraphs),
    }


EXCEL_COLUMNS = [
    ("제목", "title", 40),
    ("부제", "subtitle", 40),
    ("기자", "reporter", 10),
    ("입력", "published", 16),
    ("수정", "updated", 22),
    ("태그", "tags", 25),
    ("URL", "url", 40),
    ("본문", "content", 80),
]


def save_to_excel(article, path):
    """기사를 엑셀 파일의 한 행으로 저장. 파일이 이미 있으면 마지막 행 아래에 추가"""
    if os.path.exists(path):
        wb = load_workbook(path)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "기사"
        ws.append([name for name, _, _ in EXCEL_COLUMNS])
        header_fill = PatternFill("solid", fgColor="DDEBF7")
        for i, (_, _, width) in enumerate(EXCEL_COLUMNS, start=1):
            cell = ws.cell(row=1, column=i)
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[cell.column_letter].width = width
        ws.freeze_panes = "A2"

    row = []
    for _, key, _ in EXCEL_COLUMNS:
        value = article[key]
        row.append(", ".join(value) if isinstance(value, list) else value)
    ws.append(row)
    for cell in ws[ws.max_row]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(path)
    return ws.max_row - 1  # 헤더를 제외한 기사 수


class CrawlWorker(QThread):
    """네트워크 요청 중에도 화면이 멈추지 않도록 별도 스레드에서 크롤링"""

    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.finished_ok.emit(crawl_article(self.url))
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("오마이뉴스 기사 크롤러")
        self.resize(900, 700)
        self.article = None
        self.worker = None

        # URL 입력 영역
        self.url_edit = QLineEdit(DEFAULT_URL)
        self.url_edit.setPlaceholderText("기사 URL을 입력하세요")
        self.url_edit.returnPressed.connect(self.start_crawl)
        self.crawl_btn = QPushButton("크롤링")
        self.crawl_btn.clicked.connect(self.start_crawl)
        self.save_btn = QPushButton("TXT 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_article)
        self.excel_btn = QPushButton("엑셀 저장")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL"))
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.crawl_btn)
        url_row.addWidget(self.save_btn)
        url_row.addWidget(self.excel_btn)

        # 기사 정보 영역
        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.subtitle_label = QLabel()
        self.reporter_label = QLabel()
        self.date_label = QLabel()
        self.tags_label = QLabel()
        for label in (self.title_label, self.subtitle_label, self.tags_label):
            label.setWordWrap(True)
        for label in (self.title_label, self.subtitle_label, self.reporter_label,
                      self.date_label, self.tags_label):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        info = QFormLayout()
        info.addRow("제목", self.title_label)
        info.addRow("부제", self.subtitle_label)
        info.addRow("기자", self.reporter_label)
        info.addRow("날짜", self.date_label)
        info.addRow("태그", self.tags_label)

        # 본문 영역
        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        body_font = QFont()
        body_font.setPointSize(11)
        self.content_edit.setFont(body_font)

        layout = QVBoxLayout()
        layout.addLayout(url_row)
        layout.addLayout(info)
        layout.addWidget(self.content_edit, 1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.statusBar().showMessage("URL을 입력하고 [크롤링] 버튼을 누르세요.")

    def start_crawl(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "알림", "URL을 입력하세요.")
            return
        self.crawl_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.excel_btn.setEnabled(False)
        self.statusBar().showMessage("기사를 가져오는 중...")

        self.worker = CrawlWorker(url)
        self.worker.finished_ok.connect(self.show_article)
        self.worker.failed.connect(self.show_error)
        self.worker.start()

    def show_article(self, article):
        self.article = article
        self.title_label.setText(article["title"])
        self.subtitle_label.setText(article["subtitle"])
        self.reporter_label.setText(article["reporter"])
        date_text = f"입력 {article['published']}"
        if article["updated"]:
            date_text += f"  |  {article['updated']}"
        self.date_label.setText(date_text)
        self.tags_label.setText(", ".join(article["tags"]))
        self.content_edit.setPlainText(article["content"])

        self.crawl_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.excel_btn.setEnabled(True)
        self.statusBar().showMessage(f"완료: 본문 {len(article['content']):,}자")

    def show_error(self, message):
        self.crawl_btn.setEnabled(True)
        self.statusBar().showMessage("크롤링 실패")
        QMessageBox.critical(self, "오류", f"기사를 가져오지 못했습니다.\n\n{message}")

    def save_article(self):
        if not self.article:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "기사 저장", "article.txt", "텍스트 파일 (*.txt)"
        )
        if not path:
            return
        a = self.article
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{a['title']}\n{a['subtitle']}\n")
            f.write(f"기자: {a['reporter']} / 입력: {a['published']}\n")
            f.write(f"URL: {a['url']}\n\n{a['content']}\n")
        self.statusBar().showMessage(f"저장 완료: {path}")

    def save_excel(self):
        if not self.article:
            return
        # 기존 파일을 고르면 덮어쓰지 않고 행을 추가하므로 덮어쓰기 확인창은 끔
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", "articles.xlsx", "엑셀 파일 (*.xlsx)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            count = save_to_excel(self.article, path)
        except PermissionError:
            QMessageBox.critical(self, "오류", "파일이 엑셀에서 열려 있습니다.\n닫은 뒤 다시 시도하세요.")
            return
        except Exception as e:
            QMessageBox.critical(self, "오류", f"엑셀 저장에 실패했습니다.\n\n{e}")
            return
        self.statusBar().showMessage(f"엑셀 저장 완료: {path} (총 {count}건)")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
