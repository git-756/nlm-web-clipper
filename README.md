# NLM Web Clipper

Web上の公式ドキュメントやヘルプページをスクレイピングし、Google NotebookLMなどのLLM（大規模言語モデル）に読み込ませやすいMarkdown形式に自動抽出・整形・結合するツールです。

## 主な機能
- **動的サイト対応**: Playwrightを使用して、JavaScriptで生成される目次やリンク一覧を自動抽出します。
- **ノイズ除去**: BeautifulSoupを用いて、ヘッダー、フッター、ナビゲーション、広告などの不要なHTML要素を自動的に削除します。
- **Markdown変換**: 抽出したクリーンなテキストを、LLMが構造を理解しやすいMarkdown形式に変換します。
- **カテゴリ結合**: 抽出した多数のMarkdownファイルを、URLのパスに基づいて適切なカテゴリごとに数個のファイルに自動結合します。

## 必要条件
- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) (高速なPythonパッケージマネージャー)

## インストール
リポジトリをクローンし、必要なパッケージをインストールします。

```bash
git clone [https://github.com/git-756/nlm-web-clipper.git](https://github.com/git-756/nlm-web-clipper.git)
cd nlm-web-clipper
uv sync  # または uv add requests beautifulsoup4 markdownify playwright
uv run playwright install chromium
```

## 使い方

### 1. ターゲットURLの抽出 (オプション)
動的な目次ページから、取得したいドキュメントのURL一覧を抽出します。

```bash
uv run src/get_urls.py
```
実行後、ルートディレクトリに `target_urls.txt` が生成されます。

### 2. テキストの抽出とMarkdown化
URLリスト（または直接指定したURL）からテキストを抽出し、Markdownに変換します。

```bash
# テキストファイルから一括処理する場合
uv run src/main.py -f target_urls.txt

# URLを直接指定して処理する場合
uv run src/main.py -u [https://example.com/page1](https://example.com/page1)
```
抽出されたファイルは `output/` ディレクトリに保存されます。

### 3. ファイルのカテゴリ別結合
NotebookLMのソース上限（50件）を回避し、AIのコンテキスト理解を助けるため、出力されたファイルをカテゴリ別に結合します。

```bash
uv run src/merge_md.py
```
結合されたファイルは `merged_output/` ディレクトリに生成されます。これをNotebookLMにアップロードしてご利用ください。

## ライセンス
このプロジェクトは [MIT License](LICENSE) のもとで公開されています。