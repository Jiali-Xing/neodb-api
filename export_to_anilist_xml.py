#!/usr/bin/env python3
"""
Script to convert anilist_import_from_neodb.json to XML format for AniList import.
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

def create_anilist_xml(json_file_path, output_xml_path):
    """
    Convert the JSON data to AniList-compatible XML format.
    Only include entries with AniList IDs that are likely to exist in MAL database.
    """
    # Read the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter entries - exclude newer AniList IDs that don't exist in MAL
    # Generally, AniList IDs above ~50000 are newer and may not have MAL equivalents
    valid_entries = []
    skipped_entries = []
    
    for entry in data['anilistImport']['lists'][0]['entries']:
        media_id = entry['mediaId']
        # Keep entries with lower IDs that are more likely to exist in MAL
        if media_id <= 50000:
            valid_entries.append(entry)
        else:
            skipped_entries.append(entry)
    
    print(f"Processing {len(valid_entries)} entries (skipping {len(skipped_entries)} newer entries)")
    
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
        
        # Get original comment/review if available
        original_comment = ""
        if detailed_info:
            # Try to get comment from various possible fields
            if 'comment' in detailed_info:
                original_comment = detailed_info['comment']
            elif 'review' in detailed_info:
                original_comment = detailed_info['review']
            elif 'note' in detailed_info:
                original_comment = detailed_info['note']
            elif 'originalTitle' in detailed_info:
                # Use original title as context since no comments are available
                original_comment = f"原标题: {detailed_info['originalTitle']}"
            
            # If still no comment, use search title
            if not original_comment and 'searchTitle' in detailed_info:
                original_comment = f"搜索标题: {detailed_info['searchTitle']}"
        
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
        ET.SubElement(anime, 'my_start_date').text = '0000-00-00'
        ET.SubElement(anime, 'my_finish_date').text = '0000-00-00'
        ET.SubElement(anime, 'my_rated').text = ''
        ET.SubElement(anime, 'my_score').text = str(entry.get('score', 0))
        ET.SubElement(anime, 'my_dvd').text = ''
        ET.SubElement(anime, 'my_storage').text = ''
        ET.SubElement(anime, 'my_status').text = status_mapping.get(entry['status'], 'Plan to Watch')
        ET.SubElement(anime, 'my_comments').text = original_comment  # Use original comment instead of generic text
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
    print(f"Total entries skipped: {len(skipped_entries)}")
    
    # Print status summary for processed entries
    status_counts = {}
    for entry in valid_entries:
        status = entry['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nStatus breakdown (processed entries):")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Print skipped entries
    if skipped_entries:
        print("\nSkipped entries (newer AniList IDs):")
        for entry in sorted(skipped_entries, key=lambda x: x['mediaId']):
            print(f"  ID {entry['mediaId']}: {entry['status']}")
    
    # Create a separate file for skipped entries
    skipped_file = output_xml_path.replace('.xml', '_skipped.json')
    with open(skipped_file, 'w', encoding='utf-8') as f:
        json.dump({
            'skipped_count': len(skipped_entries),
            'entries': skipped_entries
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSkipped entries saved to: {skipped_file}")

if __name__ == "__main__":
    json_file = "anilist_import_from_neodb.json"
    xml_file = "anilist_export_filtered.xml"
    
    create_anilist_xml(json_file, xml_file)