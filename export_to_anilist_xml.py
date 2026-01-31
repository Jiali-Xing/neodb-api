#!/usr/bin/env python3
"""
Script to convert anilist_import_from_neodb.json to XML format for AniList import.
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import csv
from datetime import datetime, timedelta

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

def create_anilist_xml(json_file_path, output_xml_path, neodb_csv_path=None):
    """
    Convert the JSON data to AniList-compatible XML format.
    Only include entries with AniList IDs that are likely to exist in MAL database.
    """
    # Load NeoDB metadata if provided
    neodb_metadata = {}
    if neodb_csv_path:
        neodb_metadata = load_neodb_metadata(neodb_csv_path)
    
    # Read the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process all entries
    valid_entries = data['anilistImport']['lists'][0]['entries']
    
    print(f"Processing {len(valid_entries)} entries")
    
    # Create root XML element
    root = ET.Element('myanimelist')
    
    # Add myinfo section
    myinfo = ET.SubElement(root, 'myinfo')
    ET.SubElement(myinfo, 'user_id').text = '0'
    ET.SubElement(myinfo, 'user_name').text = 'neodb_import'
    ET.SubElement(myinfo, 'user_export_type').text = '1'
    ET.SubElement(myinfo, 'user_total_anime').text = str(len(valid_entries))
    ET.SubElement(myinfo, 'user_total_watching').text = str(sum(1 for entry in valid_entries if entry['status'] == 'CURRENT'))
    ET.SubElement(myinfo, 'user_total_completed').text = str(sum(1 for entry in valid_entries if entry['status'] == 'COMPLETED'))
    ET.SubElement(myinfo, 'user_total_onhold').text = str(sum(1 for entry in valid_entries if entry['status'] == 'PAUSED'))
    ET.SubElement(myinfo, 'user_total_dropped').text = str(sum(1 for entry in valid_entries if entry['status'] == 'DROPPED'))
    ET.SubElement(myinfo, 'user_total_plantowatch').text = str(sum(1 for entry in valid_entries if entry['status'] == 'PLANNING'))
    
    # Process each valid anime entry
    for entry in valid_entries:
        anime = ET.SubElement(root, 'anime')
        
        # Map AniList status to MAL status
        status_mapping = {
            'CURRENT': 'Watching',
            'COMPLETED': 'Completed',
            'PAUSED': 'On-Hold',
            'DROPPED': 'Dropped',
            'PLANNING': 'Plan to Watch'
        }
        
        # Find detailed info for this entry
        detailed_info = None
        for detail in data.get('detailedResults', {}).get('successful', []):
            if detail['mediaId'] == entry['mediaId']:
                detailed_info = detail
                break
        
        # Get original comment from NeoDB CSV
        original_comment = ""
        if detailed_info:
            search_title = detailed_info.get('searchTitle', '') or detailed_info.get('originalTitle', '')
            if search_title in neodb_metadata:
                original_comment = neodb_metadata[search_title].get('comment', '')
        
        # Add anime details
        ET.SubElement(anime, 'series_animedb_id').text = str(entry['mediaId'])
        
        # Use actual title if available
        if detailed_info and detailed_info.get('anilistInfo', {}).get('title', {}).get('english'):
            title = detailed_info['anilistInfo']['title']['english']
        elif detailed_info and detailed_info.get('anilistInfo', {}).get('title', {}).get('romaji'):
            title = detailed_info['anilistInfo']['title']['romaji']
        else:
            title = f"Anime ID {entry['mediaId']}"
        
        ET.SubElement(anime, 'series_title').text = title
        ET.SubElement(anime, 'series_type').text = 'TV'
        ET.SubElement(anime, 'series_episodes').text = '0'
        ET.SubElement(anime, 'my_id').text = '0'
        ET.SubElement(anime, 'my_watched_episodes').text = str(entry.get('progress', 0))
        
        # Get dates and score from NeoDB metadata
        start_date = '0000-00-00'
        finish_date = '0000-00-00'
        score = entry.get('score', 0)
        
        # Try to find metadata by searching title
        if detailed_info:
            search_title = detailed_info.get('searchTitle', '') or detailed_info.get('originalTitle', '')
            if search_title in neodb_metadata:
                meta = neodb_metadata[search_title]
                if meta['timestamp']:
                    try:
                        ts = datetime.fromisoformat(meta['timestamp'].replace('+00:00', ''))
                        finish_date = ts.strftime('%Y-%m-%d')
                        start_date = (ts - timedelta(days=30)).strftime('%Y-%m-%d')
                    except:
                        pass
                if meta['rating'] and not score:
                    try:
                        score = int(meta['rating'])
                    except:
                        pass
        
        ET.SubElement(anime, 'my_start_date').text = start_date
        ET.SubElement(anime, 'my_finish_date').text = finish_date
        ET.SubElement(anime, 'my_rated').text = ''
        ET.SubElement(anime, 'my_score').text = str(score)
        ET.SubElement(anime, 'my_dvd').text = ''
        ET.SubElement(anime, 'my_storage').text = ''
        ET.SubElement(anime, 'my_status').text = status_mapping.get(entry['status'], 'Plan to Watch')
        ET.SubElement(anime, 'my_comments').text = original_comment
        ET.SubElement(anime, 'my_times_watched').text = '0'
        ET.SubElement(anime, 'my_rewatch_value').text = ''
        ET.SubElement(anime, 'my_priority').text = 'LOW'
        ET.SubElement(anime, 'my_tags').text = 'neodb-import'
        ET.SubElement(anime, 'my_rewatching').text = '0'
        ET.SubElement(anime, 'my_rewatching_ep').text = '0'
        ET.SubElement(anime, 'update_on_import').text = '1'
    
    # Create pretty XML string
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove empty lines and write to file
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    
    with open(output_xml_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"XML file created: {output_xml_path}")
    print(f"Total entries processed: {len(valid_entries)}")
    # print(f"Total entries skipped: {len(skipped_entries)}")
    
    # Print status summary
    status_counts = {}
    for entry in valid_entries:
        status = entry['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nStatus breakdown:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    json_file = "anilist_import_from_neodb.json"
    xml_file = "anilist_export_filtered.xml"
    neodb_csv = "neodb/tv_mark.csv"
    
    create_anilist_xml(json_file, xml_file, neodb_csv)