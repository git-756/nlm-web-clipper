import os
import time
import argparse
from web_fetcher import fetch_html
from nlm_formatter import format_to_nlm_text

# 出力先ディレクトリの設定
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

def main():
    # ==========================================
    # コマンドライン引数の設定
    # ==========================================
    parser = argparse.ArgumentParser(description="指定したURLからテキストを抽出し、Markdownに変換します。")
    parser.add_argument("-f", "--file", type=str, help="URLリストが書かれたテキストファイルのパス")
    parser.add_argument("-u", "--urls", type=str, nargs="+", help="直接指定するURL（スペース区切りで複数指定可能）")
    
    args = parser.parse_args()
    urls_to_process = []

    # 1. テキストファイルからの読み込み (-f オプション)
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    # 空行や、コメントアウトされた行を除外
                    if url and not url.startswith("#"):
                        urls_to_process.append(url)
            print(f"ファイル '{args.file}' から {len(urls_to_process)} 件のURLを読み込みました。")
        except FileNotFoundError:
            print(f"[エラー] ファイル '{args.file}' が見つかりません。パスを確認してください。")

    # 2. 直接指定されたURLの追加 (-u オプション)
    if args.urls:
        urls_to_process.extend(args.urls)
        print(f"直接指定された {len(args.urls)} 件のURLを追加しました。")

    # 重複の排除（順序は保持する）
    urls_to_process = list(dict.fromkeys(urls_to_process))

    if not urls_to_process:
        print("\n[エラー] 処理するURLがありません。")
        print("使い方:")
        print("  テキストファイルから: uv run src/main.py -f target_urls.txt")
        print("  URLを直接指定:      uv run src/main.py -u https://example.com https://example.org")
        print("  両方を組み合わせる: uv run src/main.py -f target_urls.txt -u https://example.com")
        return

    # ==========================================
    # 抽出とMarkdown変換処理
    # ==========================================
    print(f"\n合計 {len(urls_to_process)} 件のURLを処理します...")
    print(f"出力先ディレクトリ: {OUTPUT_DIR}\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i, url in enumerate(urls_to_process):
        print(f"[{i+1}/{len(urls_to_process)}] 処理中: {url}")
        
        # 1. HTMLの取得
        html = fetch_html(url)
        if not html:
            continue

        # 2. HTMLのクリーニングとMarkdownへの変換
        fallback_name = f"onshape_doc_{i:03d}"
        title, clean_text = format_to_nlm_text(html, fallback_name)

        if not clean_text:
            print(f" -> [警告] 有効なテキストが抽出できませんでした ({url})")
            continue

        # ファイル名に使えない文字が残っていないか最終チェック
        safe_filename = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
        if not safe_filename:
            safe_filename = fallback_name

        file_path = os.path.join(OUTPUT_DIR, f"{safe_filename}.md")
        
        # 3. ファイルへの書き出し
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Source URL: {url}\n\n")
            f.write(clean_text)
        
        print(f" -> 保存完了: {safe_filename}.md")

        # サーバー負荷軽減のため必ず待機
        time.sleep(2)
        
    print("\nすべての処理が完了しました！")

if __name__ == "__main__":
    main()