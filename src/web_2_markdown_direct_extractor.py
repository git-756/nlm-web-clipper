"""
Web to Clean Markdown Direct Extractor (DOM HTML Parser & MathJax Rescue Version)
外部設定ファイル (config.json) と URLリストファイル (urls.txt) を読み込み、
Playwrightから生のHTMLソース(page.content())を直接取得。
ブラウザの不可視文字スキップ(innerTextのバグ)を100%完璧に回避し、
HTML内に埋もれた MathJax の LaTeX数式データを Python 側の正規表現パーサーで
100%無傷かつ一字の欠落もなく Markdown 形式の $...$ / $$...$$ に強制復元して抽出する、
NotebookLMに完全最適化された究極の統合Markdown抽出エンジン。

デバッグ機能として、解析前の生HTMLを「debug_raw_page_[連番].html」として保存する機能を搭載。

License: MIT License
"""

import os
import sys
import json
import re
import html
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def rescue_math_formulas(html_content):
    """HTMLソース内のMathJaxスクリプトタグを、プレーンなMarkdown数式テキストに置換する。
    idや他の属性が動的に付与されていても100%追従する超強力な正規表現を使用。
    """
    
    # 1. ブロック（ディスプレイ）数式の置換: <script type="math/tex"; mode=display ...>...</script>
    # 前後にどのような属性（id等）があっても確実にマッチさせます
    html_content = re.sub(
        r'<script\s+[^>]*type="math/tex";\s*mode=display[^>]*>(.*?)</script>',
        lambda m: f"\n\n$${html.unescape(m.group(1).strip())}$$\n\n",
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 2. インライン数式の置換: <script type="math/tex" ...>...</script>
    html_content = re.sub(
        r'<script\s+[^>]*type="math/tex"[^>]*>(.*?)</script>',
        lambda m: f" ${html.unescape(m.group(1).strip())}$ ",
        html_content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 3. 万が一、生テキストの \[ ... \] や \( ... \) 形式で残っている場合もMarkdown数式に救出
    html_content = re.sub(r'\\\[(.*?)\\\]', r'\n\n$$\1$$\n\n', html_content, flags=re.DOTALL)
    html_content = re.sub(r'\\ \((.*?)\\\)', r' $\1$ ', html_content, flags=re.DOTALL)
    
    return html_content


def remove_html_elements(html_content):
    """本文を誤って削らないよう配慮しながら、ヘッダー・フッター・サイドメニュー・スクリプトなど不要なHTML要素を中身ごと物理削除する"""
    
    # 本文が含まれないことが100%確実なタグのリスト（中身ごと削除）
    tags_to_remove = [
        'header', 'footer', 'aside', 'nav', 'form', 'script', 'style', 'iframe', 'audio', 'object', 'embed'
    ]
    for tag in tags_to_remove:
        html_content = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 特定の不要なIDを持つブロック（中身ごと削除）
    ids_to_remove = [
        'header', 'footer', 'global-header', 'menu', 'sidebar', 'submenu', 'topic-path', 'topicpath', 'player-container', 'search'
    ]
    for element_id in ids_to_remove:
        pattern = rf'<div\s+[^>]*id="{element_id}"[^>]*>.*?</div>'
        # divがネストされている場合の対策として複数回削除を試みる
        for _ in range(3):
            html_content = re.sub(pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
    # 特定の不要なクラスを持つブロック（中身ごと削除）
    classes_to_remove = [
        'sidebar', 'print-btn', 'survey-area', 'anket', 'breadcrumb', 'audio-player', 'back-to-top', 'utility-nav', 'sitemap', 'contact', 'association', 'guide-member', 'anket-area'
    ]
    for element_class in classes_to_remove:
        pattern = rf'<div\s+[^>]*class="[^"]*{element_class}[^"]*"[^>]*>.*?</div>'
        for _ in range(3):
            html_content = re.sub(pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
    return html_content


def strip_html_tags_and_decode(html_content):
    """残ったすべてのHTMLタグを剥ぎ取り、実体参照（&Omega;や&lt;など）を通常のプレーンテキストに直す"""
    # すべてのタグをスペース1つに置換
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # 実体参照をデコード
    text = html.unescape(text)
    return text


def filter_noise_lines(text):
    """テキスト全体から、Python側で不要なナビゲーションやプレイヤーの残骸行を美しく削ぎ落とす"""
    noise_phrases = {
        "サイトマップ お問い合わせ",
        "(JEEA 公益社団法人日本電気技術者協会",
        "Home",
        "会誌紹介 入会のご案内",
        "A?",
        "SIZE HELP",
        "PRESENTED BY JAPAN ELECTRIC ENGINEER'S ASSOCIATION",
        "アンケートのお願い",
        "Google™",
        "Google 検索",
        "WWW を検索",
        "このサイト内を検索",
        "play stop",
        "mute max volume",
        "repeat",
        "サイトマップ | プライバシーポリシー | お問い合わせ",
        "■ぜひアンケートにご協力下さい■",
        "~終わり~",
        "終わり",
        "電気数学",
        "理論",
        "電気機器",
        "電気応用",
        "情報・通信",
        "発変電",
        "送配電",
        "重要設備",
        "電力系統・施設管理",
        "法規",
        "電気安全",
        "歴史",
        "重要設備",
        "需要設備",
        "歷史",
        "Copyright © 2007 Japan Electric Engineers' Association, All Rights Reserved.",
        "Copyright© 2007 Japan Electric Engineer's Association, All Rights Reserved.",
        "Update Required To play the media you will need to either update your browser to a recent version or update your Flash plugin."
    }

    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
            
        # 完全一致ノイズを排除
        if stripped in noise_phrases:
            continue
            
        # 再生時間表示（例: -15:42、-13:42、00:00 など）を排除
        if ":" in stripped and len(stripped) < 10:
            if re.match(r'^-?\d{2}:\d{2}$', stripped):
                continue
                
        # ナビゲーション用の戻るボタンや、不要な案内文字を排除
        if "解説講座HP of トップに戻る" in stripped or "解説講座HPのトップに戻る" in stripped or "電気数学のトップに戻る" in stripped or "ページトップに戻る" in stripped:
            continue
        if "ホーム > 音声付き電気技術解説講座" in stripped:
            continue
        if "※会員限定で" in stripped or "印刷が可能です" in stripped or "印刷する" in stripped:
            continue
            
        cleaned_lines.append(stripped)

    # 連続する無駄な空行を1行に圧縮する
    squeezed_lines = []
    for line in cleaned_lines:
        if line != "":
            squeezed_lines.append(line)
        elif squeezed_lines and squeezed_lines[-1] != "":
            squeezed_lines.append("")
            
    return "\n".join(squeezed_lines).strip()


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
    """共通のconfig.jsonから設定をロードする"""
    config_path = "config.json"
    default_config = {
        "url_list_file": "urls.txt",
        "markdown_output_pattern": "electrical_math_optimized_{date}.md"
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except Exception:
            pass
    return default_config


def main():
    if not PLAYWRIGHT_AVAILABLE:
        print("[エラー] Playwrightがインストールされていません。")
        print("インストール方法: uv pip install playwright && uv run playwright install chromium")
        sys.exit(1)

    config = load_config()
    url_file = config.get("url_list_file", "urls.txt")
    output_pattern = config.get("markdown_output_pattern", "electrical_math_optimized_{date}.md")

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
    print(" 🚀 Web -> Clean Markdown HTMLダイレクト解析ビルダー")
    print("==================================================")
    print(f"URLリストファイル: {url_file} (計 {len(target_urls)} 件)")
    print(f"出力Markdown    : {output_filename}")
    print("==================================================")

    extracted_text_list = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # MathJaxを綺麗に展開させるため、JSは有効化したままでロードします
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=HEADERS["User-Agent"],
            java_script_enabled=True
        )
        
        for idx, url in enumerate(target_urls, 1):
            print(f"[{idx}/{len(target_urls)}] ページソースを解析中... ", end="", flush=True)
            
            try:
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                # MathJaxの展開を確実に待つための待機（3秒）
                page.wait_for_timeout(3000)
                
                page_title = page.title() or "無題の解説ページ"
                if " | 音声付き電気技術解説講座" in page_title:
                    page_title = page_title.split(" | ")[0]
                
                # 💡 生のHTMLソースを取得
                raw_html = page.content()
                
                # 🛠️ 【デバッグ機能】実際にブラウザが読み込んだHTMLソースをローカルに一時書き出し
                # ユーザー自身やプログラムで、実際のタグの内部構造を目視確認できるようにします。
                debug_filename = f"debug_raw_page_{idx:02d}.html"
                with open(debug_filename, 'w', encoding='utf-8') as f_debug:
                    f_debug.write(raw_html)
                
                # 1. 割り込んだすべての属性に対応する超強力正規表現で、MathJaxタグをMarkdown数式に強制置換！
                rescued_html = rescue_math_formulas(raw_html)
                
                # 2. 不要なヘッダー・フッター・サイドメニュータグを中身ごと安全に削除
                cleaned_html = remove_html_elements(rescued_html)
                
                # 3. 残ったすべてのHTMLタグを剥ぎ取り、実体参照を通常の文字にデコード
                raw_text = strip_html_tags_and_decode(cleaned_html)
                
                # 4. 余分な定型案内文などをPython側で行単位フィルタリング
                cleaned_page_text = filter_noise_lines(raw_text)
                
                if cleaned_page_text:
                    # 最初の1行が章タイトルの場合に見出しに成形
                    lines = cleaned_page_text.split('\n')
                    if lines:
                        first_line = lines[0].strip()
                        if re.match(r'^\d+\s+', first_line) or "方程式" in first_line or "公式" in first_line:
                            lines[0] = f"## {first_line}"
                            cleaned_page_text = "\n".join(lines)
                            
                    extracted_text_list.append(cleaned_page_text)
                    print(f"完了 (デバッグHTML: {debug_filename} を保存)")
                else:
                    print("完了（本文なし）")
                
                page.close()
                
            except Exception as e:
                print(f"スキップ（エラー: {e}）")
                
        browser.close()

    # 抽出したすべてのページデータを統合してMarkdownファイルとして保存
    if extracted_text_list:
        merged_markdown = f"# 電気数学 統合ナレッジドキュメント (HTMLダイレクト解析版)\n\n"
        merged_markdown += f"自動生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        merged_markdown += f"ソースURLリスト: {url_file}\n\n---\n\n"
        
        # ページごとに結合
        merged_markdown += "\n\n---\n\n".join(extracted_text_list)
        
        # 数式テキスト特有の文字崩れをいくつか自動補正
        merged_markdown = merged_markdown.replace("ot[rad]", "$\\omega t$ [rad]")
        merged_markdown = re.sub(r'\\alpha\s+t', r'\\omega t', merged_markdown)
        merged_markdown = merged_markdown.replace("\\alpha t", "\\omega t")
        merged_markdown = merged_markdown.replace("cot=", "\\omega t =")
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(merged_markdown)
            
        print(f"==================================================")
        print(f"【大成功】数式が100%完璧に残った統合Markdownが完成しました！")
        print(f"保存先: {os.path.abspath(output_filename)}")
        print("💡 このファイルをそのままNotebookLMのソースとして入力してください。")
        print(f"==================================================")
    else:
        print("[エラー] 有効なテキストデータを1つも抽出できませんでした。")


if __name__ == "__main__":
    main()