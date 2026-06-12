import requests

def fetch_html(url: str) -> str:
    """
    指定されたURLからHTMLを取得する。
    """
    # ブラウザからのアクセスに見せかけるためのヘッダー
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 文字化けを防ぐため、エンコーディングを自動判別結果に合わせる
        response.encoding = response.apparent_encoding
        return response.text
        
    except requests.exceptions.RequestException as e:
        print(f"[エラー] URLの取得に失敗しました ({url}): {e}")
        return ""