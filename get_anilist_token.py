#!/usr/bin/env python3
"""
Helper script to get AniList access token
"""

import webbrowser

print("=== AniList Token 獲取工具 ===")
print("\n步驟：")
print("1. 如果還沒有 Client，請先到 https://anilist.co/settings/developer 創建")
print("   - 點擊 'Create New Client'")
print("   - Name: 隨便填（例如：My Import Tool）")
print("   - Redirect URL: https://anilist.co/api/v2/oauth/pin")
print("\n")

client_id = input("輸入你的 Client ID: ").strip()

if not client_id:
    print("Error: Client ID is required")
    exit(1)

auth_url = f"https://anilist.co/api/v2/oauth/authorize?client_id={client_id}&response_type=token"

print(f"\n正在打開瀏覽器授權...")
webbrowser.open(auth_url)

print("\n授權後，你會看到一個頁面顯示 access_token")
print("或者被重定向到類似這樣的 URL:")
print("https://anilist.co/api/v2/oauth/pin?access_token=XXXXX...")

token = input("\n在這裡貼上你的 access token: ").strip()

if token:
    with open('.env', 'w') as f:
        f.write(f"ANILIST_TOKEN={token}\n")
    print("\n✓ Token saved to .env file")
    print("You can now run: python import_to_anilist.py")
else:
    print("\n✗ No token provided")
