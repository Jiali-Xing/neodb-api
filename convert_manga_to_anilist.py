#!/usr/bin/env python3
"""
將 NeoDB 書籍標記轉換為 AniList 漫畫格式
"""

import csv
import json
import re
import time
import os
from typing import Dict, List, Optional
import requests

class NeoDBToAniListMangaConverter:
    def __init__(self, api_delay=1.0):
        self.anilist_url = 'https://graphql.anilist.co'
        self.session = requests.Session()
        self.api_delay = api_delay
        self.search_cache = {}
        self.cache_file = 'manga_search_cache.json'
        self.load_cache()
    
    def load_cache(self):
        """載入搜尋快取"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.search_cache = json.load(f)
            print(f"載入快取: {len(self.search_cache)} 個條目")
    
    def save_cache(self):
        """儲存搜尋快取"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.search_cache, f, ensure_ascii=False, indent=2)
    
    def search_anilist_manga(self, title: str) -> Optional[Dict]:
        """搜尋 AniList 漫畫"""
        if title in self.search_cache:
            return self.search_cache[title]
        
        query = '''
        query ($search: String) {
            Page(page: 1, perPage: 5) {
                media(search: $search, type: MANGA) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    synonyms
                    startDate { year }
                    averageScore
                }
            }
        }
        '''
        
        try:
            response = self.session.post(
                self.anilist_url,
                json={'query': query, 'variables': {'search': title}}
            )
            
            if response.status_code == 200:
                data = response.json()
                media_list = data.get('data', {}).get('Page', {}).get('media', [])
                if media_list:
                    result = media_list[0]
                    self.search_cache[title] = result
                    self.save_cache()
                    return result
                else:
                    self.search_cache[title] = None
                    self.save_cache()
            else:
                print(f"  AniList API 錯誤: {response.status_code}")
                if response.status_code == 429:
                    time.sleep(self.api_delay * 2)
            
            time.sleep(self.api_delay)
            return None
            
        except Exception as e:
            print(f"搜尋錯誤: {e}")
            time.sleep(self.api_delay)
            return None
    
    def convert_status(self, status: str) -> str:
        """轉換閱讀狀態"""
        status_map = {
            'complete': 'COMPLETED',
            'progress': 'CURRENT',
            'wishlist': 'PLANNING',
            'dropped': 'DROPPED'
        }
        return status_map.get(status, 'PLANNING')
    
    def is_likely_manga(self, title: str, info: str, links: str) -> bool:
        """判斷是否可能是漫畫 - 更嚴格的檢查"""
        # 必須有 bgm.tv 鏈接才認為是漫畫
        if 'bgm.tv' in links:
            return True
        
        # 或者明確包含漫畫關鍵字
        manga_keywords = [
            '漫畫', 'manga', 'comic'
        ]
        
        for keyword in manga_keywords:
            if keyword in title.lower():
                return True
        
        # 檢查 author 是否是知名漫畫家（可選）
        if 'author:' in info:
            # 如果有日文作者名且標題也有日文，可能是漫畫
            has_japanese_author = bool(re.search(r'author:[^,]*[\u3040-\u309F\u30A0-\u30FF\u4e00-\u9fff]', info))
            has_japanese_title = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF]', title))
            if has_japanese_author and has_japanese_title:
                return True
        
        return False
    
    def parse_neodb_books(self) -> List[Dict]:
        """解析 NeoDB 書籍資料"""
        manga_list = []
        book_file = 'neodb/book_mark.csv'
        
        if not os.path.exists(book_file):
            print(f"找不到文件: {book_file}")
            return manga_list
        
        print(f"處理 {book_file}...")
        
        with open(book_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                title = row['title']
                info = row.get('info', '')
                links = row.get('links', '')
                status = row.get('status', 'wishlist')
                rating = row.get('rating', '')
                
                # 只處理可能是漫畫的條目
                if self.is_likely_manga(title, info, links):
                    manga_data = {
                        'title': title,
                        'status': self.convert_status(status),
                        'score': int(rating) if rating and rating.isdigit() else None,
                        'progress': 0,
                        'source_file': book_file
                    }
                    manga_list.append(manga_data)
        
        return manga_list
    
    def convert_to_anilist(self, output_file: str):
        """轉換到 AniList 格式"""
        print("解析 NeoDB 書籍資料...")
        manga_list = self.parse_neodb_books()
        
        print(f"找到 {len(manga_list)} 個可能的漫畫條目")
        print(f"快取中已有 {len(self.search_cache)} 個搜尋結果")
        
        converted_list = []
        failed_searches = []
        
        for i, manga in enumerate(manga_list, 1):
            print(f"[{i}/{len(manga_list)}] 搜尋: {manga['title']}")
            
            # 清理標題
            clean_title = re.sub(r'\s*\([^)]*\)', '', manga['title']).strip()
            
            result = self.search_anilist_manga(clean_title)
            
            if result:
                entry = {
                    'mediaId': result['id'],
                    'status': manga['status'],
                    'progress': manga['progress']
                }
                
                if manga['score']:
                    entry['score'] = manga['score']
                
                converted_list.append(entry)
                
                print(f"  ✓ 找到: {result['title']['romaji']} (ID: {result['id']})")
            else:
                failed_searches.append({
                    'originalTitle': manga['title'],
                    'searchTitle': clean_title,
                    'sourceFile': manga['source_file']
                })
                print(f"  ✗ 未找到")
        
        # 生成輸出
        output = {
            'anilistImport': {
                'lists': [{
                    'name': 'Manga List',
                    'entries': converted_list
                }]
            },
            'summary': {
                'total': len(manga_list),
                'successful': len(converted_list),
                'failed': len(failed_searches)
            },
            'failedSearches': failed_searches
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n轉換完成！")
        print(f"成功: {len(converted_list)}/{len(manga_list)}")
        print(f"失敗: {len(failed_searches)}")
        print(f"輸出文件: {output_file}")

if __name__ == "__main__":
    converter = NeoDBToAniListMangaConverter(api_delay=1.5)
    converter.convert_to_anilist('anilist_manga_import.json')
