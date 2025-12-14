import json
import os
import requests
import time
import re
from tqdm import tqdm

def sanitize_filename(filename):
    """Sanitize filename to be safe for filesystem"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_file(url, filepath):
    """Download a file from URL to filepath"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        
        # If the first URL format fails (404/400), try an alternative or log it
        if response.status_code != 200:
            # Fallback strategy could go here if we had multiple URL patterns
            print(f"Failed to download {url} (Status: {response.status_code})")
            return False

        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        with open(filepath, 'wb') as f, tqdm(
            desc=os.path.basename(filepath),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
        ) as bar:
            for chunk in response.iter_content(chunk_size=block_size):
                size = f.write(chunk)
                bar.update(size)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    input_file = 'procurement_results.json'
    base_dir = 'downloads'
    
    if not os.path.exists(input_file):
        print(f"File {input_file} not found! Run find_procurements.py first.")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            tenders = json.load(f)
    except json.JSONDecodeError:
        print(f"Error reading {input_file}. Check if it is valid JSON.")
        return
    
    total_downloaded = 0
    total_failed = 0
    
    print(f"Found {len(tenders)} tenders to process.")

    for tender in tenders:
        tender_id = tender.get('objectId')
        tender_title = tender.get('title', 'Untitled')
        
        if not tender_id:
            continue

        # Create specific directory for this tender
        # Use first 8 chars of ID + sanitized title (truncated) to keep path reasonable
        safe_title = sanitize_filename(tender_title)[:50]
        tender_dir_name = f"{tender_id[:8]}_{safe_title.strip()}"
        tender_dir = os.path.join(base_dir, tender_dir_name)
        
        docs = tender.get('tenderDocuments', [])
        if not docs:
            continue
            
        print(f"\nProcessing Tender: {tender_title} ({tender_id})")
        
        if not os.path.exists(tender_dir):
            os.makedirs(tender_dir)
            
        for doc in docs:
            attachment = doc.get('attachment')
            if not attachment:
                continue

            file_name = attachment.get('fileName')
            # unique_id = attachment.get('uniqueAttachmentIdentifier') # User requested to use objectId instead
            doc_id = doc.get('objectId')
            
            if not file_name or not doc_id:
                continue

            # Construct the download URL
            download_url = f"https://ezamowienia.gov.pl/mp-readmodels/api/Tender/DownloadDocument/{tender_id}/{doc_id}"
            
            safe_name = sanitize_filename(file_name)
            file_path = os.path.join(tender_dir, safe_name)
            
            if os.path.exists(file_path):
                print(f"  Skipping {safe_name} (already exists)")
                continue
            
            print(f"  Downloading {safe_name}...")
            if download_file(download_url, file_path):
                total_downloaded += 1
            else:
                total_failed += 1
            
            # Be polite to the server
            time.sleep(0.5)

    print(f"\nSummary: Downloaded {total_downloaded} files, Failed {total_failed} files.")

if __name__ == "__main__":
    main()
