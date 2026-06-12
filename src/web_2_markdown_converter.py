"""
Web to Clean Markdown Extractor (Super Safe & MathJax Block Version)
共通設定ファイル (config.json) と URLリストファイル (urls.txt) を読み込み、
MathJaxの実行をネットワークレベルで意図的にブロックしつつ、
DOM内に残された不可視の数式スクリプトタグ（<script type="math/tex">）を
Playwrightのテキスト回収前にプレーンテキスト（$ 数式 $）へ強制書き換えすることで、
HTMLソース上の「生のLaTeXテキスト数式」を100%無傷で完全回収する最強Markdown抽出スクリプト。

License: MIT License
"""

import os
import sys
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def rescue_math_and_clean_dom(page):
    """DOM内に隠されているMathJax用scriptタグからLaTeXコードを救出してテキスト化し、不要な外枠を除去する"""
    page.evaluate("""() => {
        // --- 1. <script type="math/tex"> タグ内の生LaTeXコードをプレーンテキストに書き換えて救出 ---
        // これを行うことで、innerTextの取得時に数式テキストが「不可視データ」として無視されるのを100%防ぎます。
        document.querySelectorAll('script[type^="math/tex"]').forEach(el => {
            const texCode = el.textContent.trim();
            if (!texCode) return;
            
            // ディスプレイモード（ブロック数式）かインライン数式かを判定して整形
            const isDisplay = el.type.includes('mode=display') || el.parentNode.tagName === 'DIV';
            const replacement = isDisplay ? `\\n\\n$$${texCode}$$\\n\\n` : ` $${texCode}$ `;
            
            // scriptタグの直前に、普通の文字（テキストノード）として数式を挿入
            el.parentNode.insertBefore(document.createTextNode(replacement), el);
            // 用済みとなったscriptタグ自体はDOMから物理削除
            el.remove();
        });

        // --- 2. 本文を絶対に誤消去しない、安全かつ厳選された外枠ノイズのみをセレクトしてDOM削除 ---
        const safeNoiseSelectors = [
            // 標準レイアウトの外枠
            'header', 'footer', 'aside', 'nav', 'form', 'iframe', 'audio', 'object', 'embed',
            '#header', '#footer', '#global-header', '#menu', '#sidebar', '.sidebar',
            '#submenu', '.print-btn', '.survey-area', '.anket',
            '#topic-path', '.topic-path', '#topicpath', '.breadcrumb',
            '#player-container', '.audio-player', '.back-to-top', '.utility-nav',
            '#search', '.search', '.sitemap', '.contact', '.association', '.guide-member',
            '.anket-area',
            
            // すでに描画されてしまっていた場合のMathJax残骸タグも合わせてクリア
            '.MathJax_Preview', '.MathJax', '.MathJax_Display', 'mjx-container',
            
            // スクリプトやスタイルシート
            'noscript', 'style', 'link[rel="stylesheet"]'
        ];
        
        safeNoiseSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                try { el.remove(); } catch(e) {}
            });
        });
    }""")


def filter_noise_lines(text):
    """取得したプレーンテキスト全体から、Python側で不要なナビゲーションや著作権表示を美しく削ぎ落とす"""
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
        "00:00",
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
        "需要設備",
        "歷史",
        "Copyright © 2007 Japan Electric Engineers' Association, All Rights Reserved.",
        "Copyright© 2007 Japan Electric Engineer's Association, All Rights Reserved."
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
            
        # 再生時間表示（例: -15:42、-13:42、-12:08 など）を弾く
        if stripped.startswith("-") and ":" in stripped and len(stripped) < 10:
            continue
            
        # ナビゲーション用のリンクテキストを排除
        if "解説講座HPのトップに戻る" in stripped or "電気数学のトップに戻る" in stripped or "ページトップに戻る" in stripped:
            continue
        if "ホーム > 音声付き電気技術解説講座" in stripped:
            continue
            
        cleaned_lines.append(stripped)

    # 連続する空行を綺麗に1行に圧縮する
    squeezed_lines = []
    for line in cleaned_lines:
        if line != "":
            squeezed_lines.append(line)
        elif squeezed_lines and squeezed_lines[-1] != "":
            squeezed_lines.append("")
            
    return "\n".join(squeezed_lines).strip()


def extract_clean_markdown(url):
    """PlaywrightでMathJaxをロードブロックした上で、生の数式を含むテキストを美しく抽出する"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=HEADERS["User-Agent"]
            )
            page = context.new_page()

            # 💡 MathJaxに関連する外部スクリプトの読み込みリクエストを完全遮断
            page.route("**/*mathjax*", lambda route: route.abort())
            page.route("**/MathJax.js*", lambda route: route.abort())
            page.route("**/*.js", lambda route: route.abort() if "mathjax" in route.request.url.lower() else route.continue_())

            # ページへ遷移
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # ロードを少し待つ
            page.wait_for_timeout(1000)
            
            page_title = page.title() or "無題の解説ページ"
            if " | 音声付き電気技術解説講座" in page_title:
                page_title = page_title.split(" | ")[0]
            
            # DOMから数式を完全救出＆安全クリーンアップ
            rescue_math_and_clean_dom(page)
            
            # 完全にテキストノード化された、数式を含む生テキストを一撃で取得
            raw_body_text = page.evaluate("() => document.body.innerText")
            
            browser.close()
            
            # 不要な定型メニュー行や再生ボタンの文字を完全にフィルタリング
            filtered_body_text = filter_noise_lines(raw_body_text)
            
            # 構造化されたMarkdownパーツとしてパッケージング
            markdown_content = f"\n\n# {page_title}\n\n"
            markdown_content += f"> ソースURL: {url}\n\n"
            markdown_content += "<!-- ARTICLE CONTENT START -->\n\n"
            markdown_content += filtered_body_text
            markdown_content += "\n\n<!-- ARTICLE CONTENT END -->\n\n---\n"
            
            return markdown_content
    except Exception as e:
        print(f"\n  [エラー] Markdownデータの抽出に失敗しました: {url} -> {e}")
        return None


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
            
    return {
        "url_list_file": "urls.txt",
        "markdown_output_pattern": "electrical_math_optimized_{date}.md"
    }


def main():
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
    print(" 2. クリーンMarkdown 抽出・一括結合ツール (MathJax Rescue Version)")
    print("==================================================")
    print(f"URLリスト: {url_file} (計 {len(target_urls)} 件)")
    print(f"出力MD   : {output_filename}")
    print("==================================================")

    merged_markdown = f"# 電気数学 統合ナレッジドキュメント\n\n自動生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n"
    success_count = 0

    for idx, url in enumerate(target_urls, 1):
        print(f"[{idx}/{len(target_urls)}] 本文＆数式(LaTeX)を完全抽出中: {url} ... ", end="", flush=True)
        
        md_part = extract_clean_markdown(url)
        if md_part:
            print("完了")
            merged_markdown += md_part
            success_count += 1
        else:
            print("スキップ（エラー）")

    if success_count > 0:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(merged_markdown)
        print(f"==================================================")
        print(f"【成功】完璧な数式入り統合Markdownの作成が完了しました！")
        print(f"保存先: {os.path.abspath(output_filename)}")
        print("💡 これをNotebookLMにアップロードすれば、世界最強の電気数学学習ソースになります。")
        print(f"==================================================")
    else:
        print("\n[エラー] 抽出できたコンテンツがありませんでした。")


if __name__ == "__main__":
    main()