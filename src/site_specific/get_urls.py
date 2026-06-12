from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import os

# 抽出の起点となるURL（このページを開いて、画面上にあるリンクをすべて収集します）
TARGET_URL = "https://cad.onshape.com/help/ja_JP/Content/Sketch/sketch_tools.htm"

# 出力先ファイル
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target_urls.txt")

def extract_document_urls():
    print(f"ブラウザを起動し、{TARGET_URL} にアクセスしています...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(TARGET_URL)
            # 目次のJavaScriptが完全に読み込まれ、通信が落ち着くまで待機
            page.wait_for_load_state("networkidle")
            
            # 画面内に存在するすべての <a> タグの href 属性（URL）を取得
            print("リンクを抽出中...")
            links = page.evaluate("Array.from(document.querySelectorAll('a')).map(a => a.href)")
            
        except Exception as e:
            print(f"ページの読み込みに失敗しました: {e}")
            browser.close()
            return

        browser.close()

    # 取得したリンクのフィルタリングと整形
    valid_urls = set() # 重複を排除するために set を使用
    
    for link in links:
        if not link:
            continue
            
        # 1. 外部サイトを除外し、Onshapeの日本語ヘルプコンテンツだけに絞る
        if "cad.onshape.com/help/ja_JP/Content/" in link:
            
            # 2. クエリパラメータ（?TocPath=...）やページ内ジャンプ（#）を取り除く
            parsed = urlparse(link)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 3. .htm または .html で終わる、実際のページURLだけを保存
            if clean_url.endswith((".htm", ".html")):
                valid_urls.add(clean_url)

    # 抽出したURLをアルファベット順に並べ替えてファイルに保存
    sorted_urls = sorted(list(valid_urls))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in sorted_urls:
            f.write(url + "\n")

    print("=" * 40)
    print(f"抽出完了！ 合計 {len(sorted_urls)} 件のURLを取得しました。")
    print(f"保存先: {OUTPUT_FILE}")
    print("=" * 40)

if __name__ == "__main__":
    extract_document_urls()