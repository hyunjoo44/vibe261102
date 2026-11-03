@echo off
REM 오마이뉴스 크롤러 실행파일(exe) 빌드 스크립트
REM 결과물: dist\OhmyNewsCrawler.exe
chcp 65001 > nul
cd /d "%~dp0"

python -m pip install --upgrade pyinstaller PyQt6 requests beautifulsoup4 openpyxl

python -m PyInstaller --noconfirm --clean ^
    --onefile ^
    --windowed ^
    --name OhmyNewsCrawler ^
    --exclude-module numpy ^
    --exclude-module PIL ^
    --exclude-module tkinter ^
    ohmynews_crawler.py

echo.
echo 빌드 완료: dist\OhmyNewsCrawler.exe
pause
