"""
Universal Web & PDF Merger
外部設定ファイル (config.json) と URLリストファイル (urls.txt) を読み込み、
指定された順序で取得・PDF化して1つのPDFファイルに結合する汎用スクリプト。

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

# Webページの高精度PDF化のためにPlaywrightを使用
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 403 Forbiddenなどを回避するためのUser-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_pdf_url(url):
    """URLが直接PDFを指しているか簡易判定する"""
    parsed = urlparse(url)
    if parsed.path.lower().endswith('.pdf'):
        return True
    
    # 拡張子で判定できない場合は、ヘッドリクエストを送ってContent-Typeを確認
    try:
        response = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            return True
    except Exception:
        pass
    return False


def download_pdf(url, save_path):
    """直接PDFのURLからダウンロードする"""
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


def convert_html_to_pdf(url, save_path, pdf_options):
    """Playwrightを使用してWebページ(HTML)をレンダリングし、PDFとして保存する"""
    if not PLAYWRIGHT_AVAILABLE:
        print("\n  [警告] Playwrightがインストールされていないため、HTMLのPDF化をスキップします。")
        print("  インストール方法: pip install playwright && playwright install chromium")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=HEADERS["User-Agent"]
            )
            page = context.new_page()
            
            # ページ遷移し、すべてのリソースが読み込まれるまで待機
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # 設定ファイルからマージンなどのオプションを読み込む
            margin = {
                "top": pdf_options.get("margin_top", "10mm"),
                "bottom": pdf_options.get("margin_bottom", "10mm"),
                "left": pdf_options.get("margin_left", "10mm"),
                "right": pdf_options.get("margin_right", "10mm")
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
        print(f"\n  [エラー] WebページのPDF化に失敗しました: {e}")
        return False


def read_urls_from_file(filepath):
    """外部テキストファイルからURLリストを読み込む"""
    if not os.path.exists(filepath):
        return []
    urls = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 空行やコメント行(#)を除外
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def load_config():
    """config.jsonから設定をロードする。存在しない場合はデフォルト値を返す"""
    config_path = "config.json"
    default_config = {
        "output_pattern": "pdf_merge_{date}.pdf",
        "url_list_file": "urls.txt",
        "pdf_options": {
            "margin_top": "10mm",
            "margin_bottom": "10mm",
            "margin_left": "10mm",
            "margin_right": "10mm",
            "print_background": True
        }
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # デフォルト値をベースに、ユーザー設定で上書き
                default_config.update(user_config)
                print(f"[*] 設定ファイル '{config_path}' を読み込みました。")
        except Exception as e:
            print(f"[警告] 設定ファイルの読み込みに失敗しました。デフォルト設定を使用します: {e}")
    else:
        # 存在しない場合は、雛形を作成しておく
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"[*] 設定ファイル '{config_path}' が見つからなかったため、新しく作成しました。")
        except Exception:
            pass
            
    return default_config


def main():
    # 1. 設定の読み込み
    config = load_config()
    
    url_file = config.get("url_list_file", "urls.txt")
    output_pattern = config.get("output_pattern", "pdf_merge_{date}.pdf")
    pdf_options = config.get("pdf_options", {})

    # 日付文字列を生成して出力ファイル名を決定
    today_str = datetime.now().strftime("%Y%m%d")
    output_filename = output_pattern.replace("{date}", today_str)

    # 2. URLリストの読み込み
    if not os.path.exists(url_file):
        print(f"[エラー] URLリストファイル '{url_file}' が見つかりません。")
        print("ルートディレクトリにファイルを作成し、結合したいURLを1行ずつ記述してください。")
        sys.exit(1)
        
    target_urls = read_urls_from_file(url_file)

    if not target_urls:
        print(f"[エラー] '{url_file}' の中に有効なURLが見つかりません。")
        sys.exit(1)

    print("==================================================")
    print(" 汎用 Web & PDF 一括結合ツール (設定外部化版)")
    print("==================================================")
    print(f"URLリストファイル: {url_file} (計 {len(target_urls)} 件)")
    print(f"出力ファイル名   : {output_filename}")
    print("==================================================")

    merger = PdfWriter()
    temp_dir = tempfile.TemporaryDirectory()
    temp_files = []

    try:
        for idx, url in enumerate(target_urls, 1):
            filename = f"temp_{idx:03d}.pdf"
            temp_path = os.path.join(temp_dir.name, filename)
            
            print(f"[{idx}/{len(target_urls)}] 処理中: {url} ... ", end="", flush=True)

            success = False
            if is_pdf_url(url):
                success = download_pdf(url, temp_path)
            else:
                success = convert_html_to_pdf(url, temp_path, pdf_options)

            if success:
                print("完了")
                merger.append(temp_path)
                temp_files.append(temp_path)
            else:
                print("スキップ（エラー）")

        # 結合処理
        if temp_files:
            print(f"\n[*] 全てのPDFを1つのファイルに結合しています...")
            merger.write(output_filename)
            print(f"==================================================")
            print(f"【成功】PDFファイルの作成が完了しました！")
            print(f"保存先: {os.path.abspath(output_filename)}")
            print(f"==================================================")
        else:
            print("\n[エラー] 結合可能なPDFが1つも生成されませんでした。")

    finally:
        # 一時ファイルのクリーンアップ
        merger.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    main()