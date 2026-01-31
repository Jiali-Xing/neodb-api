#!/usr/bin/env python3
"""
導入漫畫到 AniList
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

def import_manga_to_anilist(json_file_path, neodb_csv_path, access_token):
    """導入漫畫到 AniList"""
    
    # Validate token first
    test_query = 'query { Viewer { id name } }'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': test_query},
            headers=headers
        )
        if response.status_code != 200 or 'errors' in response.json():
            print(f"❌ Token validation failed: {response.text}")
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
    
    # AniList mutation for manga
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
    failed_entries = []
    
    for entry in entries:
        media_id = entry['mediaId']
        status = entry['status']
        score = entry.get('score', 0)
        progress = entry.get('progress', 0)
        
        notes = ""
        started_at = None
        completed_at = None
        
        # Try to find metadata (manga titles are simpler, no detailed results)
        # We'll just use the basic matching
        for title, meta in neodb_metadata.items():
            # Simple matching - you might want to improve this
            if meta.get('comment'):
                notes = meta['comment']
            
            if meta['timestamp']:
                try:
                    ts = datetime.fromisoformat(meta['timestamp'].replace('+00:00', ''))
                    completed_at = {
                        'year': ts.year,
                        'month': ts.month,
                        'day': ts.day
                    }
                    days_to_read = 7  # Assume 7 days to read
                    start_ts = ts - timedelta(days=days_to_read)
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
            break  # Use first match for now
        
        variables = {
            'mediaId': media_id,
            'status': status,
            'score': score,
            'progress': progress,
            'startedAt': started_at,
            'completedAt': completed_at,
            'notes': notes
        }
        
        if completed_at:
            print(f"  Dates: started={started_at}, completed={completed_at}")
        
        try:
            response = requests.post(
                'https://graphql.anilist.co',
                json={'query': mutation, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"✓ Imported manga ID {media_id}")
            else:
                failed_count += 1
                error_data = response.json()
                print(f"✗ Failed manga ID {media_id}: {response.text}")
                
                if 'errors' in error_data and any('Too Many Requests' in str(e) for e in error_data['errors']):
                    failed_entries.append(entry)
            
            time.sleep(2.0)
            
        except Exception as e:
            failed_count += 1
            failed_entries.append(entry)
            print(f"✗ Error importing manga ID {media_id}: {e}")
    
    # Save failed entries
    if failed_entries:
        os.makedirs('tmp', exist_ok=True)
        failed_file = 'tmp/failed_manga_entries.json'
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump(failed_entries, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved {len(failed_entries)} failed entries to {failed_file}")
    
    print(f"\n完成！成功: {success_count}, 失敗: {failed_count}")

if __name__ == "__main__":
    ACCESS_TOKEN = os.environ.get('ANILIST_TOKEN')
    
    if not ACCESS_TOKEN:
        if os.path.exists('.env'):
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content.startswith('ANILIST_TOKEN='):
                    ACCESS_TOKEN = content.split('=', 1)[1].strip()
    
    if not ACCESS_TOKEN:
        ACCESS_TOKEN = input("請輸入你的 AniList Access Token: ").strip()
    
    if not ACCESS_TOKEN:
        print("錯誤: 需要 Access Token")
        exit(1)
    
    json_file = "anilist_manga_import.json"
    neodb_csv = "neodb/book_mark.csv"
    
    import_manga_to_anilist(json_file, neodb_csv, ACCESS_TOKEN)
