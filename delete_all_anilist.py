#!/usr/bin/env python3
"""
刪除 AniList 上的所有條目
"""

import os
import time
import requests

def delete_all_entries(access_token):
    """刪除所有 AniList 條目"""
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    # Query to get all entries
    query = '''
    query {
        Viewer {
            id
            mediaListOptions {
                animeList {
                    sectionOrder
                }
            }
        }
    }
    '''
    
    print("正在獲取用戶信息...")
    response = requests.post(
        'https://graphql.anilist.co',
        json={'query': query},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ 獲取用戶信息失敗: {response.text}")
        return
    
    user_id = response.json()['data']['Viewer']['id']
    
    # Now get all entries
    query = '''
    query ($userId: Int) {
        MediaListCollection(userId: $userId, type: ANIME) {
            lists {
                entries {
                    id
                    status
                    media {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        synonyms
                    }
                }
            }
        }
    }
    '''
    
    print("正在獲取所有條目...")
    response = requests.post(
        'https://graphql.anilist.co',
        json={'query': query, 'variables': {'userId': user_id}},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ 獲取條目失敗: {response.text}")
        return
    
    data = response.json()
    all_entries = []
    for list_group in data['data']['MediaListCollection']['lists']:
        all_entries.extend(list_group['entries'])
    
    print(f"找到 {len(all_entries)} 個條目\n")
    
    if not all_entries:
        print("沒有條目需要刪除")
        return
    
    print("\n開始逐個確認刪除...\n")
    print("指令: 輸入 1 = 刪除, 回車 = 保留, q = 退出\n")
    print("=" * 80)
    
    # Delete mutation
    delete_mutation = '''
    mutation ($id: Int) {
        DeleteMediaListEntry(id: $id) {
            deleted
        }
    }
    '''
    
    deleted_count = 0
    skipped_count = 0
    
    STATUS_MAP = {
        'COMPLETED': '已完成',
        'CURRENT': '在看',
        'PLANNING': '計劃看',
        'DROPPED': '已棄',
        'PAUSED': '暫停',
        'REPEATING': '重看'
    }
    
    for i, entry in enumerate(all_entries, 1):
        entry_id = entry['id']
        media = entry['media']
        title = media['title']
        synonyms = media.get('synonyms', [])
        status = entry.get('status', 'N/A')
        status_cn = STATUS_MAP.get(status, status)
        
        romaji = title.get('romaji', 'N/A')
        english = title.get('english', 'N/A')
        native = title.get('native', 'N/A')
        
        print(f"\n[{i}/{len(all_entries)}] Entry ID: {entry_id}")
        print(f"羅馬字: {romaji}")
        print(f"英文: {english}")
        print(f"原文: {native}")
        if synonyms:
            print(f"別名: {', '.join(synonyms)}")
        print(f"狀態: {status_cn} ({status})")
        
        choice = input("操作 (1=刪除, 回車=保留, q=退出): ").strip().lower()
        
        if choice == 'q':
            print("\n退出...")
            break
        elif choice == '1':
            try:
                response = requests.post(
                    'https://graphql.anilist.co',
                    json={'query': delete_mutation, 'variables': {'id': entry_id}},
                    headers=headers
                )
                
                if response.status_code == 200:
                    deleted_count += 1
                    print(f"✗ 已刪除")
                else:
                    print(f"✗ 刪除失敗: {response.text}")
                
                time.sleep(1.5)
                
            except Exception as e:
                print(f"✗ 錯誤: {e}")
        else:
            skipped_count += 1
            print("✓ 保留")
    
    print(f"\n完成！刪除: {deleted_count}, 保留: {skipped_count}")

if __name__ == "__main__":
    ACCESS_TOKEN = os.environ.get('ANILIST_TOKEN')
    
    if not ACCESS_TOKEN:
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('ANILIST_TOKEN='):
                    ACCESS_TOKEN = content.split('=', 1)[1].strip()
    
    if not ACCESS_TOKEN:
        print("錯誤: 需要 Access Token")
        exit(1)
    
    delete_all_entries(ACCESS_TOKEN)
