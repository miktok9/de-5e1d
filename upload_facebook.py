"""
Enhanced Facebook Reels Upload

Facebook Graph API for uploading Reels to Facebook Page with temporary hosting.
"""

import os
import requests
import time
from pathlib import Path
import tempfile
import json
from urllib.parse import urlparse

def upload_to_facebook(video_file, description):
    """Upload video to Facebook Reels using temporary hosting for better reliability."""
    
    access_token = os.getenv('FB_ACCESS_TOKEN')
    page_id = os.getenv('FB_PAGE_ID')
    
    if not access_token or not page_id:
        raise ValueError("Missing FB_ACCESS_TOKEN or FB_PAGE_ID")
    
    print(f"[facebook] Uploading: {video_file}")
    
    # Step 1: Upload to temporary hosting service
    print("[facebook] Uploading to temporary hosting...")
    temp_url = upload_to_temp_hosting(video_file)
    print(f"[facebook] Temp URL: {temp_url}")
    
    # Step 2: Upload video using the temporary URL
    url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
    
    # Retry logic for upload
    max_retries = 3
    video_id = None
    
    for attempt in range(max_retries):
        try:
            data = {
                'access_token': access_token,
                'description': description,
                'title': 'Die Geschichte der Frauen in der Antike',
                'file_url': temp_url,  # Use temporary URL instead of direct file upload
                'is_explicit_share': True
            }
            
            response = requests.post(url, data=data, timeout=120)
            response.raise_for_status()
            video_id = response.json()['id']
            print(f"[facebook] ✅ Uploaded! Video ID: {video_id}")
            break
        except requests.exceptions.RequestException as e:
            print(f"[facebook] Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))  # Exponential backoff
            else:
                # If all retries failed, try direct file upload as fallback
                print("[facebook] Falling back to direct file upload...")
                video_id = upload_direct_file(video_file, description, access_token, page_id)
    
    # Step 3: Check video processing status
    print("[facebook] Checking video processing status...")
    check_processing_status(video_id, access_token)
    
    # Step 4: Clean up temporary file
    try:
        cleanup_temp_file(temp_url)
    except Exception as e:
        print(f"[facebook] Warning: Could not clean up temporary file: {e}")
    
    return {'id': video_id, 'temp_url': temp_url}

def upload_direct_file(video_file, description, access_token, page_id):
    """Fallback method: Direct file upload to Facebook."""
    url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
    
    with open(video_file, 'rb') as f:
        files = {'file': f}
        data = {
            'access_token': access_token,
            'description': description,
            'title': 'Die Geschichte der Frauen in der Antike',
            'is_explicit_share': True
        }
        
        response = requests.post(url, files=files, data=data, timeout=120)
        response.raise_for_status()
        
        video_id = response.json()['id']
        print(f"[facebook] ✅ Direct upload successful! Video ID: {video_id}")
        return video_id

def check_processing_status(video_id, access_token):
    """Check Facebook video processing status."""
    status_url = f"https://graph.facebook.com/v18.0/{video_id}"
    params = {
        'access_token': access_token,
        'fields': 'status'
    }
    
    max_checks = 12  # Check for up to 2 minutes
    check_interval = 10
    
    for i in range(max_checks):
        try:
            response = requests.get(status_url, params=params, timeout=30)
            response.raise_for_status()
            status_data = response.json()
            
            status = status_data.get('status', {}).get('video_status')
            if status:
                print(f"[facebook] Processing status: {status} ({(i+1) * check_interval}s)")
                if status == 'ready':
                    print("[facebook] ✅ Video processing complete!")
                    return
                elif status == 'failed':
                    print("[facebook] ⚠️  Video processing failed")
                    return
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"[facebook] Status check failed: {e}")
            time.sleep(check_interval)
    
    print("[facebook] ⚠️  Video may still be processing. Check Facebook Page for status.")

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
