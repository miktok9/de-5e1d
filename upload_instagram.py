"""
Enhanced Instagram Reels Upload

Instagram Graph API for uploading Reels with temporary hosting.
Requires: Business/Creator account + Facebook Page
"""

import os
import requests
import time
from pathlib import Path
import tempfile
import json
from urllib.parse import urlparse

def upload_to_instagram(video_file, caption):
    """Upload video to Instagram Reels using temporary hosting for better reliability."""
    
    access_token = os.getenv('IG_ACCESS_TOKEN')
    user_id = os.getenv('IG_USER_ID')
    
    if not access_token or not user_id:
        raise ValueError("Missing IG_ACCESS_TOKEN or IG_USER_ID")
    
    print(f"[instagram] Uploading: {video_file}")
    
    # Step 1: Upload to temporary hosting service
    print("[instagram] Uploading to temporary hosting...")
    temp_url = upload_to_temp_hosting(video_file)
    print(f"[instagram] Temp URL: {temp_url}")
    
    # Step 2: Create media container using the temporary URL
    url = f"https://graph.facebook.com/v18.0/{user_id}/media"
    
    params = {
        'access_token': access_token,
        'media_type': 'REELS',
        'video_url': temp_url,  # Publicly accessible URL from temporary hosting
        'caption': caption,
        'share_to_feed': True
    }
    
    # Retry logic for container creation
    max_retries = 3
    container_id = None
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, params=params, timeout=60)
            response.raise_for_status()
            container_id = response.json()['id']
            print(f"[instagram] Container created: {container_id}")
            break
        except requests.exceptions.RequestException as e:
            print(f"[instagram] Container creation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Exponential backoff
            else:
                raise Exception(f"Failed to create media container after {max_retries} attempts")
    
    # Step 3: Wait for Instagram processing with status checking
    print("[instagram] Waiting for video processing...")
    processing_complete = False
    max_wait_time = 300  # 5 minutes max
    wait_interval = 10
    elapsed_time = 0
    
    while not processing_complete and elapsed_time < max_wait_time:
        time.sleep(wait_interval)
        elapsed_time += wait_interval
        
        # Check container status
        status_url = f"https://graph.facebook.com/v18.0/{container_id}"
        status_params = {'access_token': access_token}
        
        try:
            status_response = requests.get(status_url, params=status_params, timeout=30)
            status_data = status_response.json()
            
            if 'status' in status_data:
                print(f"[instagram] Processing status: {status_data['status']} ({elapsed_time}s)")
                if status_data['status'] == 'FINISHED':
                    processing_complete = True
                elif status_data['status'] == 'ERROR':
                    raise Exception(f"Instagram processing failed: {status_data.get('error', 'Unknown error')}")
            else:
                # If no status field, assume it's ready after sufficient time
                if elapsed_time >= 60:  # Wait at least 1 minute
                    processing_complete = True
                    print("[instagram] Assuming processing complete (no status field)")
                    
        except Exception as e:
            print(f"[instagram] Status check failed: {e}")
            # Continue waiting even if status check fails
    
    if not processing_complete:
        print(f"[instagram] Warning: Video may still be processing. Proceeding with publication.")
    
    # Step 4: Publish
    publish_url = f"https://graph.facebook.com/v18.0/{user_id}/media_publish"
    publish_params = {
        'access_token': access_token,
        'creation_id': container_id
    }
    
    publish_response = requests.post(publish_url, params=publish_params, timeout=60)
    publish_response.raise_for_status()
    
    media_id = publish_response.json()['id']
    print(f"[instagram] ✅ Published! Media ID: {media_id}")
    
    # Optional: Clean up temporary file (if the service supports it)
    try:
        cleanup_temp_file(temp_url)
    except Exception as e:
        print(f"[instagram] Warning: Could not clean up temporary file: {e}")
    
    return {'id': media_id, 'container_id': container_id, 'temp_url': temp_url}

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

# Note: Instagram requires the video to be hosted at a public URL
# You'll need to upload to a temporary hosting service first
# Or use Instagram's container upload API with local files
