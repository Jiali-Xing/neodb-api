#!/usr/bin/env python3
"""
交互式清理 anilist_import_from_neodb.json 中的錯誤條目
"""

import json

STATUS_MAP = {
    'COMPLETED': '已完成',
    'CURRENT': '在看',
    'PLANNING': '計劃看',
    'DROPPED': '已棄',
    'PAUSED': '暫停',
    'REPEATING': '重看'
}

def clean_json_interactive(json_file):
    """交互式清理 JSON 文件"""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries = data['anilistImport']['lists'][0]['entries']
    detailed = {d['mediaId']: d for d in data.get('detailedResults', {}).get('successful', [])}
    
    total = len(entries)
    
    print(f"總共 {total} 個條目\n")
    print("指令: 輸入 1 = 刪除, 回車 = 保留, q = 退出並保存\n")
    print("=" * 80)
    
    to_remove = []
    
    for i, entry in enumerate(entries, 1):
        media_id = entry.get('mediaId', 'N/A')
        status = entry.get('status', 'N/A')
        status_cn = STATUS_MAP.get(status, status)
        
        # Get detailed info
        detail = detailed.get(media_id, {})
        original_title = detail.get('originalTitle', '')
        
        # Get AniList info
        anilist_info = detail.get('anilistInfo', {})
        anilist_title = anilist_info.get('title', {})
        native_title = anilist_title.get('native', '')
        romaji_title = anilist_title.get('romaji', '')
        english_title = anilist_title.get('english', '')
        
        print(f"\n[{i}/{total}] Media ID: {media_id}")
        print(f"原始標題: {original_title or 'N/A'}")
        print(f"羅馬字: {romaji_title or 'N/A'}")
        print(f"英文: {english_title or 'N/A'}")
        print(f"原文: {native_title or 'N/A'}")
        print(f"狀態: {status_cn} ({status})")
        
        choice = input("操作 (1=刪除, 回車=保留, q=退出): ").strip().lower()
        
        if choice == 'q':
            print("\n退出...")
            break
        elif choice == '1':
            to_remove.append(entry)
            print("✗ 標記為刪除")
        else:
            print("✓ 保留")
    
    if to_remove:
        print(f"\n準備刪除 {len(to_remove)} 個條目")
        confirm = input("確認刪除? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            # Remove entries
            for entry in to_remove:
                entries.remove(entry)
            
            # Also remove from detailedResults
            if 'detailedResults' in data and 'successful' in data['detailedResults']:
                removed_ids = {e['mediaId'] for e in to_remove}
                data['detailedResults']['successful'] = [
                    d for d in data['detailedResults']['successful']
                    if d['mediaId'] not in removed_ids
                ]
            
            # Save
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ 已刪除 {len(to_remove)} 個條目")
            print(f"剩餘 {len(entries)} 個條目")
        else:
            print("已取消")
    else:
        print("\n沒有條目被刪除")

if __name__ == "__main__":
    clean_json_interactive('anilist_import_from_neodb.json')
