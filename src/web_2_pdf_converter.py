"""
Web to Clean PDF Converter & Merger
共通設定ファイル (config.json) と URLリストファイル (urls.txt) を読み込み、
指定された順序でHTMLから不要なヘッダー・サイドバー・フッターなどをDOMから「物理的に削除」した上で
A4サイズの美しいPDFを生成し、最後に1つに結合するスクリプト。

License: MIT License
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from urllib.parse import urlparse
import requests
from pypdf import PdfWriter

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_pdf_url(url):
    """URLが直接PDFを指しているか判定"""
    parsed = urlparse(url)
    if parsed.path.lower().endswith('.pdf'):
        return True
    try:
        response = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            return True
    except Exception:
        pass
    return False


def download_pdf(url, save_path):
    """直接PDFファイルをダウンロード"""
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"\n  [エラー] PDFダウンロード失敗: {e}")
        return False


def clean_web_page_dom(page):
    """不要な要素をDOMから物理的に削除し、メインレイアウトをA4全幅に引き伸ばす"""
    page.evaluate("""() => {
        const noiseSelectors = [
            'header', 'footer', 'aside', 'nav', 'form', 'iframe', 'audio', 'object', 'embed',
            '#header', '#footer', '#global-header', '#menu', '#sidebar', '.sidebar',
            '#submenu', '#sub', '.sub', '.print-btn', '.survey-area', '.anket',
            '#topic-path', '.topic-path', '#topicpath', '.breadcrumb',
            '#player-container', '.audio-player', '.back-to-top', '.utility-nav',
            '#search', '.search', '.sitemap', '.contact', '.association', '.guide-member',
            '.anket-area', '#right-box', '.right-box', '#left-box', '.left-box',
            'script', 'noscript', 'style'
        ];
        
        noiseSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                try { el.remove(); } catch(e) {}
            });
        });
        
        // テーブルレイアウトおよびコンテナの全幅化調整
        const mainSelectors = [
            '#main-content', '.main-content', 'main', '#contents', '.contents', '#container', '.container', 'body'
        ];
        
        for (const sel of mainSelectors) {
            const el = document.querySelector(sel);
            if (el) {
                el.style.margin = '0 auto';
                el.style.padding = '15px';
                el.style.width = '100%';
                el.style.maxWidth = '100%';
                el.style.backgroundColor = '#ffffff';
                break;
            }
        }
    }""")


def convert_html_to_clean_pdf(url, save_path, pdf_options):
    """Playwrightでアクセスし、ノイズ除去後にA4 PDFへ書き出す"""
    if not PLAYWRIGHT_AVAILABLE:
        print("\n  [警告] Playwrightがインストールされていません。")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=HEADERS["User-Agent"]
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 通常画面表示(screen)をシミュレート
            page.emulate_media(media="screen")
            # 遅延要素（数式レンダリングなど）のために少し待機
            page.wait_for_timeout(2000)
            
            # 物理削除処理
            clean_web_page_dom(page)
            
            margin = {
                "top": pdf_options.get("margin_top", "10mm"),
                "bottom": pdf_options.get("margin_bottom", "10mm"),
                "left": pdf_options.get("margin_left", "15mm"),
                "right": pdf_options.get("margin_right", "15mm")
            }
            
            page.pdf(
                path=save_path,
                format="A4",
                print_background=pdf_options.get("print_background", True),
                margin=margin
            )
            browser.close()
        return True
    except Exception as e:
        print(f"\n  [エラー] クリーンPDF変換失敗: {url} -> {e}")
        return False


def read_urls_from_file(filepath):
    if not os.path.exists(filepath):
        return []
    urls = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 設定ファイル読み込みエラー: {e}")
    
    # フォールバック
    return {
        "url_list_file": "urls.txt",
        "pdf_output_pattern": "electrical_math_optimized_{date}.pdf",
        "pdf_options": {
            "margin_top": "10mm",
            "margin_bottom": "10mm",
            "margin_left": "15mm",
            "margin_right": "15mm",
            "print_background": True
        }
    }


def main():
    config = load_config()
    url_file = config.get("url_list_file", "urls.txt")
    output_pattern = config.get("pdf_output_pattern", "electrical_math_optimized_{date}.pdf")
    pdf_options = config.get("pdf_options", {})

    today_str = datetime.now().strftime("%Y%m%d")
    output_filename = output_pattern.replace("{date}", today_str)

    if not os.path.exists(url_file):
        print(f"[エラー] URLリストファイル '{url_file}' が存在しません。")
        sys.exit(1)

    target_urls = read_urls_from_file(url_file)
    if not target_urls:
        print("[エラー] 処理対象のURLが空です。")
        sys.exit(1)

    print("==================================================")
    print(" 1. クリーンPDF 抽出・一括マージツール")
    print("==================================================")
    print(f"URLリスト: {url_file} (計 {len(target_urls)} 件)")
    print(f"出力PDF : {output_filename}")
    print("==================================================")

    merger = PdfWriter()
    temp_dir = tempfile.TemporaryDirectory()
    temp_files = []

    try:
        for idx, url in enumerate(target_urls, 1):
            filename = f"temp_{idx:03d}.pdf"
            temp_path = os.path.join(temp_dir.name, filename)
            
            print(f"[{idx}/{len(target_urls)}] クリーンPDF生成中: {url} ... ", end="", flush=True)

            success = False
            if is_pdf_url(url):
                success = download_pdf(url, temp_path)
            else:
                success = convert_html_to_clean_pdf(url, temp_path, pdf_options)

            if success:
                print("完了")
                merger.append(temp_path)
                temp_files.append(temp_path)
            else:
                print("スキップ（エラー）")

        if temp_files:
            print(f"\n[*] 全てのクリーンPDFを1つに統合中...")
            merger.write(output_filename)
            print(f"==================================================")
            print(f"【成功】印刷制限・ノイズをクリアしたPDFが完成しました！")
            print(f"保存先: {os.path.abspath(output_filename)}")
            print(f"==================================================")
        else:
            print("\n[エラー] 有効なPDFが1つも生成されませんでした。")

    finally:
        merger.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    main()