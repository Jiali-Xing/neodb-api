#!/usr/bin/env python3
"""
步驟 2: 使用 Fribb/Anime-Lists 將 IMDB ID 映射到 AniList ID
"""

import json
import requests

class IMDBToAniListMapper:
    def __init__(self):
        self.id_mapping = {}
        self.mapping_url = 'https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-full.json'
    
    def load_id_mapping(self):
        """從 GitHub 下載 ID 映射表"""
        print("正在下載 Fribb/Anime-Lists 映射表...")
        try:
            response = requests.get(self.mapping_url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # 建立 IMDB -> AniList 的映射
                for entry in data:
                    imdb_id = entry.get('imdb_id')
                    anilist_id = entry.get('anilist_id')
                    if imdb_id and anilist_id:
                        # 移除 tt 前綴如果存在
                        imdb_clean = imdb_id.replace('tt', '') if isinstance(imdb_id, str) else str(imdb_id)
                        self.id_mapping[f'tt{imdb_clean}'] = anilist_id
                print(f"✓ 載入 {len(self.id_mapping)} 個 IMDB -> AniList 映射")
                return True
            else:
                print(f"✗ 下載失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ 下載錯誤: {e}")
            return False
    
    def convert_to_anilist(self, filtered_file='filtered_anime.json', output_file='anilist_import_from_neodb.json'):
        """將過濾後的動畫轉換為 AniList 格式"""
        
        if not self.load_id_mapping():
            print("無法載入映射表，退出")
            return
        
        # 讀取過濾後的動畫列表
        with open(filtered_file, 'r', encoding='utf-8') as f:
            anime_list = json.load(f)
        
        print(f"\n開始轉換 {len(anime_list)} 部動畫...")
        
        converted_list = []
        failed_list = []
        
        for i, anime in enumerate(anime_list, 1):
            title = anime['title']
            imdb_id = anime['external_ids'].get('imdb')
            
            print(f"[{i}/{len(anime_list)}] {title}")
            
            if not imdb_id:
                print(f"  ✗ 沒有 IMDB ID")
                failed_list.append(anime)
                continue
            
            anilist_id = self.id_mapping.get(imdb_id)
            
            if anilist_id:
                converted_anime = {
                    'mediaId': anilist_id,
                    'status': anime['status'],
                    'progress': anime['progress'],
                    'originalTitle': anime['title'],
                    'sourceFile': anime['source_file'],
                    'externalIds': anime['external_ids']
                }
                if anime.get('score'):
                    converted_anime['score'] = anime['score']
                
                converted_list.append(converted_anime)
                print(f"  ✓ 找到 AniList ID: {anilist_id}")
            else:
                print(f"  ✗ 未找到映射 (IMDB: {imdb_id})")
                failed_list.append(anime)
        
        # 生成輸出
        output = {
            'metadata': {
                'total': len(anime_list),
                'successful': len(converted_list),
                'failed': len(failed_list)
            },
            'anilistImport': {
                'lists': [{
                    'name': 'Anime List from neodb',
                    'entries': [{
                        'mediaId': item['mediaId'],
                        'status': item['status'],
                        'progress': item['progress'],
                        **({'score': item['score']} if 'score' in item else {})
                    } for item in converted_list]
                }]
            },
            'detailedResults': {
                'successful': converted_list,
                'failed': failed_list
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n轉換完成！")
        print(f"成功: {len(converted_list)}/{len(anime_list)}")
        print(f"失敗: {len(failed_list)}")
        print(f"輸出文件: {output_file}")

if __name__ == '__main__':
    mapper = IMDBToAniListMapper()
    mapper.convert_to_anilist()
