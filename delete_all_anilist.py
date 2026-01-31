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
                    media {
                        id
                        title {
                            romaji
                        }
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
    
    confirm = input(f"確定要刪除所有 {len(all_entries)} 個條目嗎？(yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return
    
    # Delete mutation
    delete_mutation = '''
    mutation ($id: Int) {
        DeleteMediaListEntry(id: $id) {
            deleted
        }
    }
    '''
    
    deleted_count = 0
    failed_count = 0
    
    for entry in all_entries:
        entry_id = entry['id']
        title = entry['media']['title']['romaji']
        
        try:
            response = requests.post(
                'https://graphql.anilist.co',
                json={'query': delete_mutation, 'variables': {'id': entry_id}},
                headers=headers
            )
            
            if response.status_code == 200:
                deleted_count += 1
                print(f"✓ Deleted: {title} (ID: {entry_id})")
            else:
                failed_count += 1
                print(f"✗ Failed to delete: {title} - {response.text}")
            
            time.sleep(4)  # Rate limit: slower to be safe
            
        except Exception as e:
            failed_count += 1
            print(f"✗ Error deleting {title}: {e}")
    
    print(f"\n完成！刪除: {deleted_count}, 失敗: {failed_count}")

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
