import pyperclip
import time

output_file = "urls.txt"
print("クリップボードの監視を開始しました。URLをコピーすると自動でファイルに追記されます... (Ctrl+Cで終了)")

last_copied = ""

try:
    while True:
        # クリップボードの中身を取得
        current_copied = pyperclip.paste().strip()
        
        # 新しくコピーされた文字列がURLっぽく、かつ前回と違う場合のみ処理
        if current_copied != last_copied and current_copied.startswith("http"):
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(current_copied + "\n")
            print(f"保存しました: {current_copied}")
            last_copied = current_copied
            
        time.sleep(1) # 1秒ごとにクリップボードをチェック
except KeyboardInterrupt:
    print("\n監視を終了しました。")