#!/usr/bin/env python3
"""
修正错误的完成时间
"""

import os
import requests
import time
import csv

# 需要修正的条目（使用 AniList 的日文标题）
TITLES_TO_FIX = [
    "もののけ姫",
    "チェンソーマン レゼ篇",
    "ハウルの動く城",
    "ヴァージン・パンク Clockwork Girl",
    "劇場版 生徒会役員共",
    "劇場版 生徒会役員共２",
    "千と千尋の神隠し",
    "名探偵コナン ハロウィンの花嫁",
    "君たちはどう生きるか",
    "大护法",
    "天空の城ラピュタ",
    "聲の形",
    "言の葉の庭",
    "雲のむこう、約束の場所"
]

def load_neodb_dates_by_imdb(csv_file):
    """从 neodb CSV 加载实际的完成日期，按 IMDB ID 索引"""
    dates = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            info = row.get('info', '')
            timestamp = row.get('timestamp', '')
            # 提取 IMDB ID
            import re
            imdb_match = re.search(r'imdb:(tt\d+)', info)
            if imdb_match and timestamp:
                imdb_id = imdb_match.group(1)
                dates[imdb_id] = timestamp
    return dates

def load_anilist_to_imdb_mapping():
    """从 Fribb 映射表加载 AniList ID -> IMDB ID 映射"""
    mapping = {}
    try:
        response = requests.get('https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-full.json', timeout=30)
        if response.status_code == 200:
            data = response.json()
            for entry in data:
                anilist_id = entry.get('anilist_id')
                imdb_id = entry.get('imdb_id')
                if anilist_id and imdb_id:
                    if isinstance(imdb_id, str) and not imdb_id.startswith('tt'):
                        imdb_id = f'tt{imdb_id}'
                    mapping[anilist_id] = imdb_id
            print(f"✓ 载入 {len(mapping)} 个 AniList -> IMDB 映射\n")
    except Exception as e:
        print(f"✗ 下载映射表失败: {e}")
    return mapping

def get_imdb_from_mapping(media_id, mapping):
    """从映射表获取 IMDB ID"""
    return mapping.get(media_id)

def search_anilist_by_title(title, session):
    """搜索 AniList 获取 media ID"""
    query = '''
    query ($search: String) {
        Page(page: 1, perPage: 5) {
            media(search: $search, type: ANIME) {
                id
                title { romaji english native }
            }
        }
    }
    '''
    
    response = session.post(
        'https://graphql.anilist.co',
        json={'query': query, 'variables': {'search': title}}
    )
    
    if response.status_code == 200:
        data = response.json()
        media_list = data.get('data', {}).get('Page', {}).get('media', [])
        if media_list:
            return media_list[0]['id']
    return None

def update_completion_date(media_id, completed_at, access_token):
    """更新完成日期"""
    mutation = '''
    mutation ($mediaId: Int, $completedAt: FuzzyDateInput) {
        SaveMediaListEntry (mediaId: $mediaId, completedAt: $completedAt) {
            id
            completedAt { year month day }
        }
    }
    '''
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    response = requests.post(
        'https://graphql.anilist.co',
        json={'query': mutation, 'variables': {'mediaId': media_id, 'completedAt': completed_at}},
        headers=headers
    )
    
    return response.status_code == 200

def main():
    # 读取 token
    ACCESS_TOKEN = os.environ.get('ANILIST_TOKEN')
    if not ACCESS_TOKEN and os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('ANILIST_TOKEN='):
                ACCESS_TOKEN = content.split('=', 1)[1].strip()
    
    if not ACCESS_TOKEN:
        print("错误: 需要 Access Token")
        return
    
    # 加载 AniList -> IMDB 映射
    anilist_to_imdb = load_anilist_to_imdb_mapping()
    
    # 加载 neodb 日期（按 IMDB ID 索引）
    neodb_dates = load_neodb_dates_by_imdb('neodb/movie_mark.csv')
    
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    })
    
    print("开始修正完成日期...\n")
    
    for title in TITLES_TO_FIX:
        print(f"处理: {title}")
        
        # 搜索 AniList ID
        media_id = search_anilist_by_title(title, session)
        if not media_id:
            print(f"  ✗ 未找到 AniList ID")
            time.sleep(1.5)
            continue
        
        print(f"  找到 AniList ID: {media_id}")
        
        # 获取 IMDB ID
        imdb_id = get_imdb_from_mapping(media_id, anilist_to_imdb)
        if not imdb_id:
            print(f"  ✗ 未找到 IMDB ID")
            continue
        
        print(f"  找到 IMDB ID: {imdb_id}")
        
        # 从 neodb 获取实际日期
        actual_date = neodb_dates.get(imdb_id)
        if not actual_date:
            print(f"  ✗ 未找到 neodb 日期")
            continue
        
        # 解析日期
        from datetime import datetime
        try:
            ts = datetime.fromisoformat(actual_date.replace('+00:00', ''))
            completed_at = {
                'year': ts.year,
                'month': ts.month,
                'day': ts.day
            }
            
            # 更新
            if update_completion_date(media_id, completed_at, ACCESS_TOKEN):
                print(f"  ✓ 已更新为: {ts.date()}")
            else:
                print(f"  ✗ 更新失败")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
        
        time.sleep(2)
    
    print("\n完成！")

if __name__ == '__main__':
    main()
