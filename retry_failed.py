#!/usr/bin/env python3
"""
重試失敗的導入
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

def retry_failed_imports(failed_file, json_file, neodb_csv, access_token):
    """重試失敗的導入"""
    
    if not os.path.exists(failed_file):
        print(f"❌ 找不到文件: {failed_file}")
        return
    
    with open(failed_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    neodb_metadata = load_neodb_metadata(neodb_csv)
    
    print(f"準備重試 {len(entries)} 個失敗的條目...\n")
    
    mutation = '''
    mutation ($mediaId: Int, $status: MediaListStatus, $score: Float, $progress: Int, $startedAt: FuzzyDateInput, $completedAt: FuzzyDateInput, $notes: String) {
        SaveMediaListEntry (mediaId: $mediaId, status: $status, score: $score, progress: $progress, startedAt: $startedAt, completedAt: $completedAt, notes: $notes) {
            id
            status
        }
    }
    '''
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    success_count = 0
    failed_count = 0
    still_failed = []
    
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
            possible_titles = [
                detailed_info.get('searchTitle', ''),
                detailed_info.get('originalTitle', ''),
                detailed_info.get('englishTitle', ''),
                detailed_info.get('romajiTitle', '')
            ]
            
            expanded_titles = []
            for title in possible_titles:
                if title:
                    expanded_titles.append(title)
                    if ' / ' in title:
                        expanded_titles.extend(title.split(' / '))
            
            meta = None
            matched_title = None
            for title in expanded_titles:
                title = title.strip()
                if title and title in neodb_metadata:
                    meta = neodb_metadata[title]
                    matched_title = title
                    break
            
            if meta:
                notes = meta.get('comment', '')
                
                if meta['timestamp']:
                    try:
                        ts = datetime.fromisoformat(meta['timestamp'].replace('+00:00', ''))
                        completed_at = {
                            'year': ts.year,
                            'month': ts.month,
                            'day': ts.day
                        }
                        days_to_watch = max(progress, 1) if progress else 7
                        start_ts = ts - timedelta(days=days_to_watch)
                        started_at = {
                            'year': start_ts.year,
                            'month': start_ts.month,
                            'day': start_ts.day
                        }
                        print(f"  → {matched_title}: {ts.date()} (from CSV)")
                    except Exception as e:
                        print(f"  → Failed to parse timestamp for {matched_title}: {e}")
                
                if meta['rating'] and not score:
                    try:
                        score = float(meta['rating'])
                    except:
                        pass
            else:
                print(f"  → No metadata found for: {' / '.join(filter(None, expanded_titles[:2]))}")
        
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
            print(f"    Dates: started={started_at}, completed={completed_at}")
        
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
                still_failed.append(entry)
            
            time.sleep(2.0)  # Even slower for retry
            
        except Exception as e:
            failed_count += 1
            still_failed.append(entry)
            print(f"✗ Error importing media ID {media_id}: {e}")
    
    # Update failed entries file
    if still_failed:
        with open(failed_file, 'w', encoding='utf-8') as f:
            json.dump(still_failed, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Updated {failed_file} with {len(still_failed)} still-failed entries")
    else:
        os.remove(failed_file)
        print(f"\n🎉 All entries imported successfully! Removed {failed_file}")
    
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
        print("錯誤: 需要 Access Token")
        exit(1)
    
    retry_failed_imports(
        'tmp/failed_entries.json',
        'anilist_import_from_neodb.json',
        'neodb/tv_mark.csv',
        ACCESS_TOKEN
    )
