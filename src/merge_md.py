import os
import re

# ディレクトリの設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "output")
OUTPUT_DIR = os.path.join(BASE_DIR, "merged_output") # 元のファイルを残すため別のフォルダに出力

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"[エラー] 入力フォルダが見つかりません: {INPUT_DIR}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 結合したテキストを格納する辞書
    merged_contents = {
        "Onshape_Sketch": [],
        "Onshape_PartStudio": [],
        "Onshape_Assembly": [],
        "Onshape_Drawing_and_View": [],
        "Onshape_System_and_Others": []
    }

    # outputフォルダ内のすべてのMarkdownファイルを取得
    md_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".md")]
    
    if not md_files:
        print("[エラー] 結合するMarkdownファイルがありません。")
        return

    print(f"{len(md_files)} 件のファイルを仕分け・結合します...\n")

    # 仕分け処理
    for filename in md_files:
        file_path = os.path.join(INPUT_DIR, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # ファイル内の「# Source URL: xxx」からURLを抽出
        url_match = re.search(r'# Source URL: (https?://[^\s]+)', content)
        
        if not url_match:
            print(f"[スキップ] URLが特定できませんでした: {filename}")
            continue
            
        url = url_match.group(1)

        # URLのパスからカテゴリーを判定
        if "/Sketch/" in url:
            merged_contents["Onshape_Sketch"].append(content)
        elif "/PartStudio/" in url:
            merged_contents["Onshape_PartStudio"].append(content)
        elif "/Assembly/" in url:
            merged_contents["Onshape_Assembly"].append(content)
        elif "/Drawing/" in url or "/View/" in url:
            merged_contents["Onshape_Drawing_and_View"].append(content)
        else:
            merged_contents["Onshape_System_and_Others"].append(content)

    # 各カテゴリーごとにファイルとして書き出し
    for category_name, contents_list in merged_contents.items():
        if not contents_list:
            print(f" -> [空] {category_name} に分類されたファイルはありませんでした。")
            continue

        output_file_path = os.path.join(OUTPUT_DIR, f"{category_name}.md")
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            # 大見出しとしてカテゴリー名を記載
            f.write(f"# {category_name.replace('_', ' ')}\n\n")
            f.write("このドキュメントは複数の公式ヘルプページを統合したものです。\n\n")
            
            # 各ページの内容を区切り線（---）で繋いで書き込む
            separator = "\n\n" + ("-" * 50) + "\n\n"
            f.write(separator.join(contents_list))
            
        print(f" -> [成功] {category_name}.md を作成しました（{len(contents_list)} ページ分を含む）")

    print(f"\nすべての結合処理が完了しました！\n出力先: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()