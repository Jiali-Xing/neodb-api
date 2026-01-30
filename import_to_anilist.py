#!/usr/bin/env python3
"""
直接通過 AniList API 導入數據
"""

import json
import csv
import time
import os
from datetime import datetime, timedelta
import requests

def load_neodb_metadata(csv_file_path):
    """Load timestamp, rating and comment from NeoDB CSV."""
    metadata = {}
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row['title']
            timestamp = row.get('timestamp', '')
            rating = row.get('rating', '')
            comment = row.get('comment', '')
            metadata[title] = {'timestamp': timestamp, 'rating': rating, 'comment': comment}
    return metadata

def import_to_anilist(json_file_path, neodb_csv_path, access_token):
    """直接通過 AniList API 導入"""
    
    # Validate token first
    test_query = 'query { Viewer { id name } }'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    print(f"Debug: Token length = {len(access_token)}")
    print(f"Debug: Token starts with = {access_token[:30]}...")
    
    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': test_query},
            headers=headers
        )
        if response.status_code != 200 or 'errors' in response.json():
            print(f"❌ Token validation failed: {response.text}")
            print("\nPlease get a valid token from: https://anilist.co/settings/developer")
            return
        print(f"✓ Token validated for user: {response.json()['data']['Viewer']['name']}\n")
    except Exception as e:
        print(f"❌ Failed to validate token: {e}")
        return
    
    # Load data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    neodb_metadata = load_neodb_metadata(neodb_csv_path)
    entries = data['anilistImport']['lists'][0]['entries']
    
    # AniList mutation
    mutation = '''
    mutation ($mediaId: Int, $status: MediaListStatus, $score: Float, $progress: Int, $startedAt: FuzzyDateInput, $completedAt: FuzzyDateInput, $notes: String) {
        SaveMediaListEntry (mediaId: $mediaId, status: $status, score: $score, progress: $progress, startedAt: $startedAt, completedAt: $completedAt, notes: $notes) {
            id
            status
        }
    }
    '''
    
    success_count = 0
    failed_count = 0
    
    for entry in entries:
        media_id = entry['mediaId']
        status = entry['status']
        score = entry.get('score', 0)
        progress = entry.get('progress', 0)
        
        # Get metadata
        detailed_info = None
        for detail in data.get('detailedResults', {}).get('successful', []):
            if detail['mediaId'] == media_id:
                detailed_info = detail
                break
        
        notes = ""
        started_at = None
        completed_at = None
        
        if detailed_info:
            search_title = detailed_info.get('searchTitle', '') or detailed_info.get('originalTitle', '')
            if search_title in neodb_metadata:
                meta = neodb_metadata[search_title]
                notes = meta.get('comment', '')
                
                if meta['timestamp']:
                    try:
                        ts = datetime.fromisoformat(meta['timestamp'].replace('+00:00', ''))
                        completed_at = {
                            'year': ts.year,
                            'month': ts.month,
                            'day': ts.day
                        }
                        start_ts = ts - timedelta(days=30)
                        started_at = {
                            'year': start_ts.year,
                            'month': start_ts.month,
                            'day': start_ts.day
                        }
                    except:
                        pass
                
                if meta['rating'] and not score:
                    try:
                        score = float(meta['rating'])
                    except:
                        pass
        
        variables = {
            'mediaId': media_id,
            'status': status,
            'score': score,
            'progress': progress,
            'startedAt': started_at,
            'completedAt': completed_at,
            'notes': notes
        }
        
        try:
            response = requests.post(
                'https://graphql.anilist.co',
                json={'query': mutation, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"✓ Imported media ID {media_id}")
            else:
                failed_count += 1
                print(f"✗ Failed media ID {media_id}: {response.text}")
            
            time.sleep(0.6)  # Rate limit: ~1 request per second
            
        except Exception as e:
            failed_count += 1
            print(f"✗ Error importing media ID {media_id}: {e}")
    
    print(f"\n完成！成功: {success_count}, 失敗: {failed_count}")

if __name__ == "__main__":
    # 從環境變量或配置文件讀取 access token
    ACCESS_TOKEN = os.environ.get('ANILIST_TOKEN')
    
    if not ACCESS_TOKEN:
        # 嘗試從 .env 文件讀取
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('ANILIST_TOKEN='):
                    ACCESS_TOKEN = content.split('=', 1)[1].strip()
    
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = input("請輸入你的 AniList Access Token: ").strip()
    
    if not ACCESS_TOKEN:
        print("錯誤: 需要 Access Token")
        print("請訪問 https://anilist.co/settings/developer 獲取")
        print("然後創建 .env 文件並添加: ANILIST_TOKEN=你的token")
        exit(1)
    
    json_file = "anilist_import_from_neodb.json"
    neodb_csv = "neodb/tv_mark.csv"
    
    import_to_anilist(json_file, neodb_csv, ACCESS_TOKEN)
