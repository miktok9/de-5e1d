"""
Enhanced TikTok Upload

TikTok Content Posting API for uploading videos with improved error handling.
Supports both file upload and URL-based upload methods.
Requires: TikTok Developer account + OAuth
"""

import os
import requests
import time
from pathlib import Path
import tempfile
import json
from urllib.parse import urlparse

def upload_to_tiktok(video_file, title, description, use_url_upload=False):
    """Upload video to TikTok using either direct file upload or URL-based upload.
    
    Args:
        video_file: Path to video file
        title: Video title
        description: Video description
        use_url_upload: Boolean to use URL-based upload instead of direct file upload
    """
    
    access_token = os.getenv('TIKTOK_ACCESS_TOKEN')
    
    if not access_token:
        raise ValueError("Missing TIKTOK_ACCESS_TOKEN")
    
    print(f"[tiktok] Uploading: {video_file}")
    
    # TikTok Content Posting API
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Prepare source info based on upload method
    if use_url_upload:
        # Upload to temporary hosting first
        print("[tiktok] Using URL-based upload method")
        temp_url = upload_to_temp_hosting(video_file)
        print(f"[tiktok] Temp URL: {temp_url}")
        
        source_info = {
            'source': 'PULL_FROM_URL',
            'video_url': temp_url
        }
    else:
        # Direct file upload
        print("[tiktok] Using direct file upload method")
        source_info = {
            'source': 'FILE_UPLOAD',
            'video_size': os.path.getsize(video_file),
            'chunk_size': 10000000,
            'total_chunk_count': 1
        }
    
    data = {
        'post_info': {
            'title': title,
            'description': description,
            'privacy_level': 'PUBLIC_TO_EVERYONE',
            'disable_duet': False,
            'disable_comment': False,
            'disable_stitch': False,
            'video_cover_timestamp_ms': 1000
        },
        'source_info': source_info
    }
    
    # Initialize upload with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"[tiktok] Upload initialization attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise Exception(f"Failed to initialize TikTok upload after {max_retries} attempts")
    
    result = response.json()
    publish_id = result['data']['publish_id']
    
    print(f"[tiktok] Upload initialized: {publish_id}")
    
    # Upload video file if using direct upload method
    if not use_url_upload:
        upload_url = result['data']['upload_url']
        
        with open(video_file, 'rb') as f:
            video_data = f.read()
            
        # Upload with retry logic
        for attempt in range(max_retries):
            try:
                upload_response = requests.put(
                    upload_url,
                    headers={'Content-Type': 'video/mp4'},
                    data=video_data,
                    timeout=120
                )
                upload_response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                print(f"[tiktok] File upload attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                else:
                    raise Exception(f"Failed to upload video file after {max_retries} attempts")
    
    # Check upload status
    print("[tiktok] Checking upload status...")
    status_url = f"https://open.tiktokapis.com/v2/post/publish/status/?publish_id={publish_id}"
    
    # Wait for processing to complete
    max_wait_time = 300  # 5 minutes
    wait_interval = 15
    elapsed_time = 0
    processing_complete = False
    
    while not processing_complete and elapsed_time < max_wait_time:
        time.sleep(wait_interval)
        elapsed_time += wait_interval
        
        try:
            status_response = requests.get(status_url, headers=headers, timeout=30)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            status = status_data.get('data', {}).get('status')
            print(f"[tiktok] Status: {status} ({elapsed_time}s)")
            
            if status == 'PUBLISH_COMPLETE':
                processing_complete = True
                print("[tiktok] ✅ Upload complete!")
            elif status == 'FAILED':
                error_code = status_data.get('data', {}).get('error_code', 'Unknown')
                error_message = status_data.get('data', {}).get('error_message', 'Unknown error')
                raise Exception(f"TikTok upload failed - Code: {error_code}, Message: {error_message}")
            
        except requests.exceptions.RequestException as e:
            print(f"[tiktok] Status check failed: {e}")
            # Continue waiting even if status check fails
    
    if not processing_complete:
        print(f"[tiktok] Warning: Upload may still be processing. Check TikTok Creator Center for status.")
    
    # Clean up temporary file if URL upload was used
    if use_url_upload and 'temp_url' in locals():
        try:
            cleanup_temp_file(temp_url)
        except Exception as e:
            print(f"[tiktok] Warning: Could not clean up temporary file: {e}")
    
    return {'id': publish_id, 'status': 'complete' if processing_complete else 'processing'}

def upload_to_temp_hosting(video_file):
    """Upload video to temporary hosting service (tmpfiles.org)."""
    url = "https://tmpfiles.org/api/v1/upload"
    
    with open(video_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        temp_url = data['data']['url']
        
        # Convert to direct download URL
        parsed = urlparse(temp_url)
        direct_url = f"{parsed.scheme}://{parsed.netloc}/dl{parsed.path}"
        
        return direct_url

def cleanup_temp_file(temp_url):
    """Attempt to clean up temporary file (best effort)."""
    # tmpfiles.org automatically deletes files after 14 days
    # This is just a placeholder - actual cleanup would require
    # storing the deletion token from the initial upload response
    pass
