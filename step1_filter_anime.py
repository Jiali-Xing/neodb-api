#!/usr/bin/env python3
"""
步驟 1: 從 CSV 檢查 IMDB 並過濾動畫
"""

import csv
import json
import re
import time
import os
import requests

class AnimeFilter:
    def __init__(self, imdb_delay=3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.imdb_cache_file = 'imdb_anime_cache.json'
        self.imdb_anime_cache = self.load_imdb_cache()
        self.imdb_delay = imdb_delay
    
    def load_imdb_cache(self):
        if os.path.exists(self.imdb_cache_file):
            with open(self.imdb_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_imdb_cache(self):
        with open(self.imdb_cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.imdb_anime_cache, f, ensure_ascii=False, indent=2)
    
    def check_imdb_for_anime(self, imdb_id):
        if imdb_id in self.imdb_anime_cache:
            result = self.imdb_anime_cache[imdb_id]
            print(f"  IMDB 快取: Animation={result}")
            return result
        
        try:
            url = f'https://www.imdb.com/title/{imdb_id}/'
            response = self.session.get(url)
            if response.status_code == 200:
                text = response.text
                has_animation = 'Animation' in text
                is_japan = 'Japan' in text
                result = has_animation
                print(f"  IMDB 檢查: Animation={has_animation}, Japan={is_japan}")
                
                self.imdb_anime_cache[imdb_id] = result
                self.save_imdb_cache()
                
                time.sleep(self.imdb_delay)
                return result
            return False
        except Exception as e:
            print(f"  IMDB 檢查錯誤: {e}")
            return False
    
    def is_likely_anime(self, title, info, links):
        imdb_match = re.search(r'imdb:(tt\d+)', info)
        if imdb_match:
            imdb_id = imdb_match.group(1)
            if self.check_imdb_for_anime(imdb_id):
                print(f"  ✓ IMDB 確認為日本動畫: {title}")
                return True
            else:
                print(f"  ✗ IMDB 非日本動畫: {title}")
        return False
    
    def convert_status(self, status):
        status_map = {
            'complete': 'COMPLETED',
            'progress': 'CURRENT',
            'wishlist': 'PLANNING',
            'dropped': 'DROPPED'
        }
        return status_map.get(status, 'PLANNING')
    
    def extract_ids_from_info(self, info_str):
        ids = {}
        imdb_match = re.search(r'imdb:(tt\d+)', info_str)
        if imdb_match:
            ids['imdb'] = imdb_match.group(1)
        year_match = re.search(r'year:(\d{4})', info_str)
        if year_match:
            ids['year'] = year_match.group(1)
        return ids
    
    def extract_ids_from_links(self, links_str):
        ids = {}
        bgm_match = re.search(r'bgm\.tv/subject/(\d+)', links_str)
        if bgm_match:
            ids['bgm'] = bgm_match.group(1)
        douban_match = re.search(r'movie\.douban\.com/subject/(\d+)', links_str)
        if douban_match:
            ids['douban'] = douban_match.group(1)
        tmdb_match = re.search(r'themoviedb\.org/tv/(\d+)', links_str)
        if tmdb_match:
            ids['tmdb'] = tmdb_match.group(1)
        return ids
    
    def process_csv_files(self, output_file='filtered_anime.json'):
        anime_list = []
        
        for csv_file in ['neodb/tv_mark.csv', 'neodb/movie_mark.csv']:
            if not os.path.exists(csv_file):
                continue
            
            print(f"處理 {csv_file}...")
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row['title']
                    info = row.get('info', '')
                    links = row.get('links', '')
                    status = row.get('status', 'wishlist')
                    rating = row.get('rating', '')
                    
                    if self.is_likely_anime(title, info, links):
                        info_ids = self.extract_ids_from_info(info)
                        link_ids = self.extract_ids_from_links(links)
                        
                        anime_data = {
                            'title': title,
                            'status': self.convert_status(status),
                            'score': int(rating) if rating and rating.isdigit() else None,
                            'progress': 0,
                            'external_ids': {**info_ids, **link_ids},
                            'source_file': csv_file
                        }
                        anime_list.append(anime_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(anime_list, f, ensure_ascii=False, indent=2)
        
        print(f"\n完成！找到 {len(anime_list)} 部動畫")
        print(f"結果保存到: {output_file}")

if __name__ == '__main__':
    filter = AnimeFilter()
    filter.process_csv_files()
