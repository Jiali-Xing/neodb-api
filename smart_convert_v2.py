#!/home/jiali/miniconda3/envs/pyspark/bin/python
import csv
import requests
import json
import time
import re
import html
import os
from typing import Dict, List, Optional

class SmartMALToAniListConverter:
    def __init__(self, api_delay=6, imdb_delay=5):
        self.anilist_url = 'https://graphql.anilist.co'
        self.omdb_api_key = None  # 可以設置 OMDB API key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache_file = 'search_cache.json'
        self.search_cache = self.load_cache()
        self.api_delay = api_delay  # AniList API 延遲
        self.imdb_delay = imdb_delay  # IMDB/TMDB API 延遲
        
    def load_cache(self) -> Dict:
        """載入搜尋快取"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_cache(self):
        """儲存搜尋快取"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.search_cache, f, ensure_ascii=False, indent=2)
        
    def get_english_title_from_imdb(self, imdb_id: str) -> Optional[str]:
        """從 IMDB 獲取英文標題"""
        try:
            # 使用 OMDB API（如果有 key）
            if self.omdb_api_key:
                url = f'http://www.omdbapi.com/?i={imdb_id}&apikey={self.omdb_api_key}'
                response = self.session.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('Response') == 'True':
                        return data.get('Title')
            
            # 備用方案：嘗試從 IMDB 頁面抓取（簡單版本）
            url = f'https://www.imdb.com/title/{imdb_id}/'
            response = self.session.get(url)
            if response.status_code == 200:
                # 簡單的正則表達式提取標題
                title_match = re.search(r'<title>([^<]+) \(', response.text)
                if title_match:
                    title = title_match.group(1).strip()
                    # 清理標題和 HTML 編碼
                    title = re.sub(r'\s*-\s*IMDb$', '', title)
                    # 修復所有 HTML 編碼問題
                    title = html.unescape(title)
                    # 移除引號
                    title = title.strip('"\'')
                    return title
            
            time.sleep(self.imdb_delay)  # 避免請求過快
            return None
            
        except Exception as e:
            print(f"從 IMDB 獲取標題失敗 {imdb_id}: {e}")
            time.sleep(self.imdb_delay)
            return None
    
    def get_english_title_from_tmdb(self, tmdb_id: str) -> Optional[str]:
        """從 TMDB 獲取英文標題"""
        try:
            # TMDB API 不需要 key 的基本資訊
            url = f'https://api.themoviedb.org/3/tv/{tmdb_id}?language=en-US'
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('name') or data.get('original_name')
            
            time.sleep(self.imdb_delay)  # 避免請求過快
            return None
            
        except Exception as e:
            print(f"從 TMDB 獲取標題失敗 {tmdb_id}: {e}")
            time.sleep(self.imdb_delay)
            return None
    
    def get_best_english_title(self, anime_data: Dict) -> str:
        """獲取最佳的英文標題"""
        original_title = anime_data['title']
        external_ids = anime_data.get('external_ids', {})
        
        # 如果原標題已經在快取中，直接使用原標題，不需要 IMDB 搜尋
        if original_title in self.search_cache:
            print(f"  原標題已在快取中，跳過 IMDB 搜尋")
            return original_title
        
        # 如果原標題已經是英文，直接使用
        if re.match(r'^[a-zA-Z0-9\s\-:!?.,()&]+$', original_title):
            return original_title
        
        # 嘗試從 IMDB 獲取英文標題
        if 'imdb' in external_ids:
            english_title = self.get_english_title_from_imdb(external_ids['imdb'])
            if english_title:
                print(f"  從 IMDB 獲取英文標題: {english_title}")
                # 檢查英文標題是否已在快取中
                if english_title in self.search_cache:
                    print(f"  英文標題已在快取中")
                return english_title
        
        # 嘗試從 TMDB 獲取英文標題
        if 'tmdb' in external_ids:
            english_title = self.get_english_title_from_tmdb(external_ids['tmdb'])
            if english_title:
                print(f"  從 TMDB 獲取英文標題: {english_title}")
                # 檢查英文標題是否已在快取中
                if english_title in self.search_cache:
                    print(f"  英文標題已在快取中")
                return english_title
        
        # 如果都沒有，返回清理後的原標題
        clean_title = re.sub(r'\s*\([^)]*\)', '', original_title).strip()
        clean_title = re.sub(r'\s*第[一二三四五六七八九十\d]+季?', '', clean_title).strip()
        return clean_title
        
    def extract_ids_from_info(self, info_str: str) -> Dict[str, str]:
        """從 info 字串中提取各種 ID"""
        ids = {}
        
        # 提取 IMDB ID
        imdb_match = re.search(r'imdb:(tt\d+)', info_str)
        if imdb_match:
            ids['imdb'] = imdb_match.group(1)
            
        # 提取年份
        year_match = re.search(r'year:(\d{4})', info_str)
        if year_match:
            ids['year'] = year_match.group(1)
            
        return ids
    
    def extract_ids_from_links(self, links_str: str) -> Dict[str, str]:
        """從 links 字串中提取各種資料庫 ID"""
        ids = {}
        
        # BGM.tv ID
        bgm_match = re.search(r'bgm\.tv/subject/(\d+)', links_str)
        if bgm_match:
            ids['bgm'] = bgm_match.group(1)
            
        # Douban ID  
        douban_match = re.search(r'movie\.douban\.com/subject/(\d+)', links_str)
        if douban_match:
            ids['douban'] = douban_match.group(1)
            
        # TMDB ID
        tmdb_match = re.search(r'themoviedb\.org/tv/(\d+)', links_str)
        if tmdb_match:
            ids['tmdb'] = tmdb_match.group(1)
            
        return ids
    
    def search_anilist_by_title(self, title: str) -> Optional[Dict]:
        """用標題搜尋 AniList，使用快取"""
        # 檢查快取（不再在這裡檢查，因為在主循環中已經檢查過）
        
        query = '''
        query ($search: String) {
            Page(page: 1, perPage: 5) {
                media(search: $search, type: ANIME) {
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
                    # 儲存到快取
                    self.search_cache[title] = result
                    self.save_cache()
                    return result
                else:
                    # 儲存空結果到快取
                    self.search_cache[title] = None
                    self.save_cache()
            else:
                print(f"  AniList API 錯誤: {response.status_code} - {response.text[:100]}")
                if response.status_code == 429:
                    print(f"  觸發速率限制，增加延遲")
                    time.sleep(self.api_delay * 2)
                # 不儲存錯誤結果到快取，以便下次重試
            
            time.sleep(self.api_delay)  # 使用參數化延遲
            return None
            
        except Exception as e:
            print(f"搜尋錯誤: {e}")
            time.sleep(self.api_delay)
            return None
    
    def convert_status(self, status: str) -> str:
        """轉換觀看狀態"""
        status_map = {
            'complete': 'COMPLETED',
            'progress': 'CURRENT', 
            'wishlist': 'PLANNING',
            'dropped': 'DROPPED'
        }
        return status_map.get(status, 'PLANNING')
    
    def parse_neodb_data(self) -> List[Dict]:
        """解析 neodb TV 和電影資料"""
        anime_list = []
        
        # 處理 TV 資料
        tv_file = 'neodb/tv_mark.csv'
        if os.path.exists(tv_file):
            print(f"處理 {tv_file}...")
            anime_list.extend(self.parse_csv_file(tv_file))
        
        # 處理電影資料
        movie_file = 'neodb/movie_mark.csv'
        if os.path.exists(movie_file):
            print(f"處理 {movie_file}...")
            anime_list.extend(self.parse_csv_file(movie_file))
        
        return anime_list
    
    def parse_csv_file(self, filename: str) -> List[Dict]:
        """解析單個 CSV 檔案"""
        anime_list = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                title = row['title']
                info = row.get('info', '')
                links = row.get('links', '')
                status = row.get('status', 'wishlist')
                rating = row.get('rating', '')
                
                # 只處理可能是動畫的條目
                if self.is_likely_anime(title, info, links):
                    # 提取各種 ID
                    info_ids = self.extract_ids_from_info(info)
                    link_ids = self.extract_ids_from_links(links)
                    
                    anime_data = {
                        'title': title,
                        'status': self.convert_status(status),
                        'score': int(rating) if rating and rating.isdigit() else None,
                        'progress': 0,  # neodb 沒有進度資訊
                        'external_ids': {**info_ids, **link_ids},
                        'source_file': filename
                    }
                    anime_list.append(anime_data)
        
        return anime_list
    
    def is_likely_anime(self, title: str, info: str, links: str) -> bool:
        """判斷是否可能是動畫"""
        # 有 bgm.tv 連結的很可能是動畫
        if 'bgm.tv' in links:
            return True
        
        # 包含動畫相關關鍵字
        anime_keywords = [
            'season', '第一季', '第二季', '第三季', '第四季', 
            'ova', 'tv', '劇場版', '特別篇', '番外篇',
            '動畫', 'anime', '第一部', '第二部'
        ]
        
        if any(keyword in title.lower() for keyword in anime_keywords):
            return True
        
        # 包含日文字符
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', title):
            return True
        
        # 已知的動畫標題模式
        anime_patterns = [
            r'.*第\d+季',
            r'.*OVA',
            r'.*劇場版',
            r'.*特別篇'
        ]
        
        for pattern in anime_patterns:
            if re.search(pattern, title):
                return True
        
        return False
    
    def convert_to_anilist(self, output_file: str):
        """轉換到 AniList 格式"""
        print("解析 neodb 資料...")
        anime_list = self.parse_neodb_data()
        
        print(f"找到 {len(anime_list)} 個可能的動畫條目，開始搜尋 AniList ID...")
        print(f"快取中已有 {len(self.search_cache)} 個搜尋結果")
        
        converted_list = []
        failed_searches = []
        skipped_count = 0
        
        for i, anime in enumerate(anime_list, 1):
            print(f"[{i}/{len(anime_list)}] 搜尋: {anime['title']}")
            
            # 獲取最佳英文標題
            english_title = self.get_best_english_title(anime)
            
            result = None
            search_attempts = [english_title]
            
            # 如果英文標題與原標題不同，也嘗試原標題
            if english_title != anime['title']:
                search_attempts.append(anime['title'])
            
            # 嘗試用標題的第一部分（移除季數）
            if '第' in anime['title']:
                base_title = anime['title'].split('第')[0].strip()
                if base_title not in search_attempts:
                    search_attempts.append(base_title)
            
            # 移除括號內容的版本
            clean_original = re.sub(r'\s*\([^)]*\)', '', anime['title']).strip()
            if clean_original not in search_attempts:
                search_attempts.append(clean_original)
            
            # 檢查是否所有搜尋嘗試都已經在快取中
            all_cached = True
            has_null_cache = False
            for attempt in search_attempts:
                if attempt and attempt not in self.search_cache:
                    all_cached = False
                    break
                elif attempt and self.search_cache.get(attempt) is None:
                    has_null_cache = True
            
            if all_cached and has_null_cache:
                print(f"  所有搜尋嘗試都已快取且結果為空，跳過")
                skipped_count += 1
                # 也保存未找到的條目資訊
                failed_anime = {
                    'originalTitle': anime['title'],
                    'searchTitle': english_title,
                    'sourceFile': anime['source_file'],
                    'externalIds': anime['external_ids'],
                    'status': anime['status'],
                    'progress': anime['progress']
                }
                if anime['score']:
                    failed_anime['score'] = anime['score']
                    
                failed_searches.append(failed_anime)
                print(f"  ✗ 已知未找到（快取）")
                continue
            elif all_cached:
                print(f"  所有搜尋嘗試都已快取，跳過網路搜尋")
                skipped_count += 1
                
                # 從快取中找到第一個有結果的（無延遲）
                for attempt in search_attempts:
                    if attempt and self.search_cache.get(attempt):
                        result = self.search_cache[attempt]
                        print(f"  從快取獲取結果: '{attempt}' (無延遲)")
                        # 為已快取的結果也生成完整資訊
                        converted_anime = {
                            'mediaId': result['id'],
                            'status': anime['status'],
                            'progress': anime['progress'],
                            'originalTitle': anime['title'],
                            'searchTitle': attempt,
                            'sourceFile': anime['source_file'],
                            'externalIds': anime['external_ids'],
                            'anilistInfo': {
                                'title': result['title'],
                                'year': result.get('startDate', {}).get('year'),
                                'averageScore': result.get('averageScore')
                            }
                        }
                        if anime['score']:
                            converted_anime['score'] = anime['score']
                        converted_list.append(converted_anime)
                        
                        titles = result['title']
                        found_title = titles.get('english') or titles.get('romaji') or titles.get('native')
                        year = result.get('startDate', {}).get('year', '')
                        print(f"  ✓ 找到: {found_title} ({year}) (ID: {result['id']})")
                        break
            else:
                # 逐一嘗試搜尋（只搜尋未快取的）
                for attempt in search_attempts:
                    if attempt:
                        # 先檢查快取
                        if attempt in self.search_cache:
                            cached_result = self.search_cache[attempt]
                            if cached_result:
                                result = cached_result
                                print(f"  從快取獲取結果: '{attempt}' (無延遲)")
                                break
                            # 如果快取結果為 None，繼續下一個嘗試
                        else:
                            # 未快取，進行網路搜尋
                            result = self.search_anilist_by_title(attempt)
                            if result:
                                if attempt != english_title:
                                    print(f"  用 '{attempt}' 搜尋成功")
                                break
            
            if result:
                converted_anime = {
                    'mediaId': result['id'],
                    'status': anime['status'],
                    'progress': anime['progress'],
                    # 保存原始資訊以便合併
                    'originalTitle': anime['title'],
                    'searchTitle': english_title,
                    'sourceFile': anime['source_file'],
                    'externalIds': anime['external_ids'],
                    'anilistInfo': {
                        'title': result['title'],
                        'year': result.get('startDate', {}).get('year'),
                        'averageScore': result.get('averageScore')
                    }
                }
                
                if anime['score']:
                    converted_anime['score'] = anime['score']
                
                converted_list.append(converted_anime)
                titles = result['title']
                found_title = titles.get('english') or titles.get('romaji') or titles.get('native')
                year = result.get('startDate', {}).get('year', '')
                print(f"  ✓ 找到: {found_title} ({year}) (ID: {result['id']})")
            else:
                # 也保存未找到的條目資訊
                failed_anime = {
                    'originalTitle': anime['title'],
                    'searchTitle': english_title,
                    'sourceFile': anime['source_file'],
                    'externalIds': anime['external_ids'],
                    'status': anime['status'],
                    'progress': anime['progress']
                }
                if anime['score']:
                    failed_anime['score'] = anime['score']
                    
                failed_searches.append(failed_anime)
                print(f"  ✗ 未找到")
        
        # 儲存結果
        result_data = {
            'metadata': {
                'convertedAt': time.strftime('%Y-%m-%d %H:%M:%S'),
                'totalProcessed': len(anime_list),
                'successfullyConverted': len(converted_list),
                'failed': len(failed_searches),
                'skipped': skipped_count
            },
            'anilistImport': {
                'lists': [{
                    'name': 'Anime List from neodb',
                    'entries': [{
                        'mediaId': item['mediaId'],
                        'status': item['status'],
                        'progress': item['progress'],
                        **(({'score': item['score']} if 'score' in item else {}))
                    } for item in converted_list]
                }]
            },
            'detailedResults': {
                'successful': converted_list,
                'failed': failed_searches
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # 另外儲存純 AniList 格式的檔案
        anilist_only_file = output_file.replace('.json', '_anilist_only.json')
        with open(anilist_only_file, 'w', encoding='utf-8') as f:
            json.dump(result_data['anilistImport'], f, ensure_ascii=False, indent=2)
        
        print(f"\n轉換完成！")
        print(f"成功轉換: {len(converted_list)} 部")
        print(f"轉換失敗: {len(failed_searches)} 部")
        print(f"跳過搜尋（已快取）: {skipped_count} 部")
        print(f"完整結果儲存至: {output_file}")
        print(f"AniList 專用格式儲存至: {anilist_only_file}")
        print(f"搜尋快取儲存至: {self.cache_file}")
        
        if failed_searches:
            print(f"\n未找到的動畫（前10個）:")
            for item in failed_searches[:10]:
                if isinstance(item, dict):
                    print(f"  - {item['originalTitle']}")
                else:
                    print(f"  - {item}")
            if len(failed_searches) > 10:
                print(f"  ... 還有 {len(failed_searches) - 10} 個")

if __name__ == '__main__':
    converter = SmartMALToAniListConverter()
    converter.convert_to_anilist('anilist_import_from_neodb.json')