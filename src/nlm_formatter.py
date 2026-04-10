from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re

def format_to_nlm_text(html_content: str, fallback_title: str = "document") -> tuple[str, str]:
    if not html_content:
        return fallback_title, ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. タイトルの取得
    title_tag = soup.find("title")
    title = title_tag.text.strip() if title_tag else fallback_title
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")
    if not safe_title:
        safe_title = fallback_title

    # =========================================================
    # 修正ポイント：先に「本文領域」を特定して確保する
    # =========================================================
    # Wikipedia特有のID（mw-content-text）を最優先、なければ汎用タグ
    content_area = soup.find(id="mw-content-text")
    if not content_area:
        content_area = soup.find("main")
    if not content_area:
        content_area = soup.find("article")
    if not content_area:
        content_area = soup.find("body")
        
    if not content_area:
        return safe_title, ""

    # =========================================================
    # 確保した本文領域の「中だけ」をクリーニングする
    # =========================================================
    tags_to_remove = ["script", "style", "nav", "footer", "aside", "noscript", "iframe", "form"]
    for tag in content_area.find_all(tags_to_remove):
        tag.decompose()

    # 広告やサイドバーなど、明らかに不要なクラス名を限定して削除
    noise_keywords = ['advertisement', 'sidebar', 'banner', 'popup', 'share-button']
    def has_noise_word(attr_value):
        if not attr_value: return False
        attr_str = " ".join(attr_value).lower() if isinstance(attr_value, list) else str(attr_value).lower()
        return any(word in attr_str for word in noise_keywords)

    for element in content_area.find_all(class_=has_noise_word):
        element.decompose()
    for element in content_area.find_all(id=has_noise_word):
        element.decompose()

    # 4. NotebookLM向けにMarkdownへ変換
    raw_markdown = md(str(content_area), heading_style="ATX")
    
    # 5. 余分な空行を整理してすっきりさせる
    clean_lines = [line.strip() for line in raw_markdown.splitlines()]
    clean_markdown = re.sub(r'\n{3,}', '\n\n', '\n'.join(clean_lines))

    return safe_title, clean_markdown