"""
Enhanced Threads Upload Script

Uploads videos to Threads using Instagram Graph API with temporary hosting.
Threads uses the same API as Instagram.

Requirements:
- Instagram Business or Creator account
- Facebook App with Instagram Graph API access
- THREADS_ACCESS_TOKEN and THREADS_USER_ID in environment
"""

import os
import requests
from pathlib import Path
import time
import tempfile
import json
from urllib.parse import urlparse

def upload_to_threads(video_file, caption):
    """Upload video to Threads using Instagram Graph API with temporary hosting for better reliability."""
    
    access_token = os.getenv('THREADS_ACCESS_TOKEN')
    user_id = os.getenv('THREADS_USER_ID')
    
    if not access_token or not user_id:
        raise ValueError(
            "Missing Threads credentials! Set these environment variables:\n"
            "  - THREADS_ACCESS_TOKEN\n"
            "  - THREADS_USER_ID"
        )
    
    print("[threads] Uploading to Threads...")
    
    # Step 1: Upload to temporary hosting service
    print("[threads] Uploading to temporary hosting...")
    temp_url = upload_to_temp_hosting(video_file)
    print(f"[threads] Temp URL: {temp_url}")
    
    # Step 2: Create media container with retry logic
    print("[threads] Creating media container...")
    
    container_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    
    params = {
        'media_type': 'VIDEO',
        'video_url': temp_url,  # Use temporary URL
        'text': caption,
        'access_token': access_token
    }
    
    # Retry logic for container creation
    max_retries = 3
    container_id = None
    
    for attempt in range(max_retries):
        try:
            response = requests.post(container_url, params=params, timeout=60)
            if response.status_code != 200:
                raise Exception(f"Failed to create container: {response.text}")
            
            container_id = response.json().get('id')
            print(f"[threads] Container created: {container_id}")
            break
        except Exception as e:
            print(f"[threads] Container creation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise Exception(f"Failed to create container after {max_retries} attempts")
    
    # Step 3: Wait for processing with enhanced status checking
    print("[threads] Waiting for video processing...")
    max_wait = 300  # Increased to 5 minutes
    waited = 0
    wait_interval = 10
    
    processing_complete = False
    
    while waited < max_wait and not processing_complete:
        try:
            status_url = f"https://graph.threads.net/v1.0/{container_id}"
            status_params = {'fields': 'status_code,status', 'access_token': access_token}
            
            status_response = requests.get(status_url, params=status_params, timeout=30)
            status_data = status_response.json()
            
            status_code = status_data.get('status_code')
            detailed_status = status_data.get('status', 'unknown')
            
            print(f"[threads] Processing status: {status_code} ({detailed_status}) - {waited}s elapsed")
            
            if status_code == 'FINISHED':
                processing_complete = True
                print("[threads] ✅ Video processing complete!")
            elif status_code == 'ERROR':
                error_details = status_data.get('error', {})
                raise Exception(f"Video processing failed: {error_details}")
            
        except Exception as e:
            print(f"[threads] Status check failed: {e}")
            # Continue waiting even if status check fails
        
        if not processing_complete:
            time.sleep(wait_interval)
            waited += wait_interval
    
    if not processing_complete:
        print("[threads] ⚠️  Video may still be processing. Proceeding with publication.")
    
    # Step 4: Publish the post with retry logic
    print("[threads] Publishing post...")
    
    publish_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
    publish_params = {
        'creation_id': container_id,
        'access_token': access_token
    }
    
    # Retry logic for publishing
    publish_success = False
    for attempt in range(max_retries):
        try:
            publish_response = requests.post(publish_url, params=publish_params, timeout=60)
            if publish_response.status_code != 200:
                raise Exception(f"Failed to publish: {publish_response.text}")
            
            thread_id = publish_response.json().get('id')
            publish_success = True
            break
        except Exception as e:
            print(f"[threads] Publish attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise Exception(f"Failed to publish after {max_retries} attempts")
    
    if not publish_success:
        raise Exception("Failed to publish to Threads")
    
    print(f"[threads] ✅ Published to Threads! ID: {thread_id}")
    
    # Step 5: Clean up temporary file
    try:
        cleanup_temp_file(temp_url)
    except Exception as e:
        print(f"[threads] Warning: Could not clean up temporary file: {e}")
    
    return {
        'id': thread_id,
        'container_id': container_id,
        'temp_url': temp_url,
        'platform': 'threads'
    }

def main():
    """Test upload to Threads."""
    video_file = Path('output/final_video.mp4')
    
    if not video_file.exists():
        print("[threads] ❌ No video found at output/final_video.mp4")
        return
    
    # Read story for caption
    story_file = Path('output/story.txt')
    if story_file.exists():
        caption = story_file.read_text(encoding='utf-8')[:500]  # Threads has character limit
    else:
        caption = "Die Geschichte der Frauen in der Antike 🏛️"
    
    try:
        upload_to_threads(video_file, caption)
    except Exception as e:
        print(f"[threads] ❌ Upload failed: {e}")
        raise

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

if __name__ == '__main__':
    main()
