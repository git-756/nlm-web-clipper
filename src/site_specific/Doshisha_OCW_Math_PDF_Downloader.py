"""
Doshisha OCW Math Intro - PDF Downloader & Merger
同志社大学 OCW「微分積分・線形代数入門」の1〜25の講義PDFを自動で取得し、1つのPDFに結合するスクリプト。

License: MIT License
"""

import os
import sys
import tempfile
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfWriter

# サーバーによるスクレイピング防止（403 Forbidden）を回避するためのブラウザ用User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_absolute_url(base, href):
    """相対パスを絶対URLに変換するヘルパー関数"""
    return urljoin(base, href)


def download_file(url, save_path):
    """指定されたURLからファイルをダウンロードしてローカルに保存する"""
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  [エラー] ダウンロード失敗 ({url}): {e}")
        return False


def main():
    # ターゲットとなるPC版インデックスページのURL
    index_url = "https://opencourse.doshisha.ac.jp/opc/bj01/math-intro/PC/index.html"
    output_filename = "doshisha_math_intro_complete.pdf"

    print("==================================================")
    print(" 同志社大学 OCW「微分積分・線形代数入門」PDF結合ツール")
    print("==================================================")
    print(f"1. インデックスページを解析中: {index_url}")

    try:
        response = requests.get(index_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        # サイトの文字コードがShift_JISやEUC-JPの場合に対応できるよう自動判定
        response.encoding = response.apparent_encoding
    except Exception as e:
        print(f"インデックスページの取得に失敗しました: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_urls = []

    # --- アプローチ 1: PDF版目次ページ（PC_pdf/index.html等）から探す ---
    print("\n2. PDF版目次ページへのリンクを探索中...")
    pdf_index_url = None
    for a in soup.find_all('a'):
        text = a.get_text()
        href = a.get('href', '')
        # 「こちら」や「PDF版」などのキーワード、またはパスに PC_pdf が含まれているリンクを探す
        if 'こちら' in text or 'PDF版' in text or 'PC_pdf' in href:
            pdf_index_url = get_absolute_url(index_url, href)
            break

    # 見つからない場合の推測フォールバック
    if not pdf_index_url:
        pdf_index_url = "https://opencourse.doshisha.ac.jp/opc/bj01/math-intro/PC_pdf/index.html"
        print(f"   -> 明示的なPDF目次リンクが見つからなかったため、デフォルトURLを試します: {pdf_index_url}")
    else:
        print(f"   -> PDF目次ページを検出しました: {pdf_index_url}")

    # PDF目次ページをパースして個別PDFリンクを取得
    try:
        pdf_res = requests.get(pdf_index_url, headers=HEADERS, timeout=15)
        pdf_res.raise_for_status()
        pdf_res.encoding = pdf_res.apparent_encoding
        pdf_soup = BeautifulSoup(pdf_res.text, 'html.parser')

        for a in pdf_soup.find_all('a'):
            href = a.get('href', '')
            if href.endswith('.pdf') and 'index' not in href:
                abs_pdf_url = get_absolute_url(pdf_index_url, href)
                if abs_pdf_url not in pdf_urls:
                    pdf_urls.append(abs_pdf_url)
    except Exception as e:
        print(f"   -> PDF目次ページからの解析中にエラーが発生しました: {e}")

    # --- アプローチ 2 (フォールバック): HTML版講義ページから各PDFを回収する ---
    if len(pdf_urls) < 25:
        print(f"\n3. PDFの検出数が不足しています（検出数: {len(pdf_urls)}）。各HTML講義ページからPDFを直接探索します...")
        pdf_urls = []  # リストをリセット
        
        # HTML版インデックスから講義ページへのリンク（例: greece.html, number1.html 等）を抽出
        lecture_pages = []
        for a in soup.find_all('a'):
            href = a.get('href', '')
            # 通常の講義HTMLファイルを抽出（index.htmlやスマホ版、外部サイト等を除外）
            if href.endswith('.html') and 'index' not in href and 'mobile' not in href and 'http' not in href:
                abs_lecture_url = get_absolute_url(index_url, href)
                if abs_lecture_url not in lecture_pages:
                    lecture_pages.append(abs_lecture_url)

        # 抽出した各HTMLページを巡回し、その中にあるPDFへの直リンクを探す
        for i, lec_url in enumerate(lecture_pages, 1):
            print(f"   [{i}/{len(lecture_pages)}] 講義ページ解析中: {os.path.basename(lec_url)}")
            try:
                lec_res = requests.get(lec_url, headers=HEADERS, timeout=10)
                if lec_res.status_code == 200:
                    lec_res.encoding = lec_res.apparent_encoding
                    lec_soup = BeautifulSoup(lec_res.text, 'html.parser')
                    for a in lec_soup.find_all('a'):
                        href = a.get('href', '')
                        if href.endswith('.pdf'):
                            abs_pdf_url = get_absolute_url(lec_url, href)
                            if abs_pdf_url not in pdf_urls:
                                pdf_urls.append(abs_pdf_url)
                                break  # 1ページから最初のPDFのみ取得
            except Exception as e:
                print(f"    - 解析エラー: {e}")

    # 最終確認
    if not pdf_urls:
        print("\n[エラー] 結合対象のPDFファイルリンクが検出できませんでした。処理を中断します。")
        sys.exit(1)

    print(f"\n4. 結合対象のPDFファイルを計 {len(pdf_urls)} 件検出しました。")
    for idx, url in enumerate(pdf_urls, 1):
        print(f"   - [{idx:02d}] {os.path.basename(url)}")

    # ダウンロードと結合処理
    merger = PdfWriter()
    temp_dir = tempfile.TemporaryDirectory()
    temp_files = []

    print("\n5. 各PDFのダウンロードおよび結合処理を開始します...")
    try:
        for idx, pdf_url in enumerate(pdf_urls, 1):
            filename = f"temp_{idx:02d}_{os.path.basename(pdf_url)}"
            temp_path = os.path.join(temp_dir.name, filename)
            
            print(f"   [{idx}/{len(pdf_urls)}] ダウンロード中: {os.path.basename(pdf_url)} ...", end="", flush=True)
            if download_file(pdf_url, temp_path):
                print(" 完了")
                merger.append(temp_path)
                temp_files.append(temp_path)
            else:
                print(" 失敗（スキップします）")

        # 最終PDFの書き出し
        if temp_files:
            print(f"\n6. 1つのファイルに統合しています...")
            merger.write(output_filename)
            print(f"==================================================")
            print(f"【成功】全講義を統合したPDFファイルを作成しました！")
            print(f"保存先: {os.path.abspath(output_filename)}")
            print(f"==================================================")
        else:
            print("\n[エラー] ダウンロードできたPDFファイルがありませんでした。")

    finally:
        # クリーンアップ
        merger.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    main()