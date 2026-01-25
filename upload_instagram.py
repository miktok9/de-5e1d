"""
Instagram Reels Upload - Enhanced Version
Uploads video to tmpfiles.org, then uses URL for Instagram Graph API
"""

import os
import requests
import time
from pathlib import Path

def upload_to_instagram(video_path, caption):
    """
    Upload video to Instagram Reels via temporary public URL.
    """

    print("\n" + "=" * 60)
    print("📸 INSTAGRAM UPLOAD STARTING")
    print("=" * 60)

    # Get credentials
    access_token = os.getenv('IG_ACCESS_TOKEN')
    user_id = os.getenv('IG_USER_ID')

    if not access_token:
        error_msg = "❌ IG_ACCESS_TOKEN not set"
        print(f"[instagram] {error_msg}")
        raise ValueError(error_msg)

    if not user_id:
        error_msg = "❌ IG_USER_ID not set"
        print(f"[instagram] {error_msg}")
        raise ValueError(error_msg)

    print(f"[instagram] ✅ Credentials loaded")
    print(f"[instagram] User ID: {user_id}")
    print(f"[instagram] Token length: {len(access_token)} chars")

    # Check video file
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[instagram] {error_msg}")
        raise FileNotFoundError(error_msg)

    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[instagram] ✅ Video file found: {video_path}")
    print(f"[instagram] Video size: {file_size_mb:.2f} MB")

    # Limit caption
    caption_limited = caption[:2200] if len(caption) > 2200 else caption
    print(f"[instagram] Caption length: {len(caption_limited)} characters")

    try:
        # Step 1: Upload to tmpfiles.org to get public URL
        print(f"[instagram] 📤 Step 1: Uploading to temporary hosting...")

        with open(video_path_obj, 'rb') as video_file:
            files = {'file': ('video.mp4', video_file, 'video/mp4')}
            temp_response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files=files,
                timeout=180
            )

        if temp_response.status_code != 200:
            error_msg = f"Failed to upload to temporary hosting: {temp_response.status_code}"
            print(f"[instagram] ❌ {error_msg}")
            print(f"[instagram] Response: {temp_response.text[:200]}")
            raise Exception(error_msg)

        temp_data = temp_response.json()
        if temp_data.get('status') != 'success':
            error_msg = f"Temporary hosting failed: {temp_data}"
            print(f"[instagram] ❌ {error_msg}")
            raise Exception(error_msg)

        # tmpfiles.org returns URL in format: https://tmpfiles.org/12345
        # We need direct download link: https://tmpfiles.org/dl/12345
        temp_url = temp_data.get('data', {}).get('url', '')

        # IMPORTANT: Instagram might need HTTPS, not HTTP
        video_url = temp_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/').replace('http://', 'https://')

        print(f"[instagram] ✅ Temporary URL created: {video_url}")

        # Step 2: Create Instagram media container with video URL
        print(f"[instagram] 📦 Step 2: Creating Instagram container...")

        # Try different API versions
        api_versions = ['v18.0', 'v19.0', 'v20.0']
        container_id = None

        for api_version in api_versions:
            print(f"[instagram] Trying API version: {api_version}")

            container_url = f"https://graph.facebook.com/{api_version}/{user_id}/media"
            container_params = {
                'access_token': access_token,
                'media_type': 'REELS',
                'video_url': video_url,
                'caption': caption_limited,
                'share_to_feed': True
            }

            print(f"[instagram] Request URL: {container_url}")
            print(f"[instagram] Parameters: media_type=REELS, video_url={video_url[:50]}..., caption length={len(caption_limited)}")

            container_response = requests.post(container_url, params=container_params, timeout=60)

            print(f"[instagram] Response status: {container_response.status_code}")
            print(f"[instagram] Response body: {container_response.text}")

            if container_response.status_code == 200:
                response_data = container_response.json()
                container_id = response_data.get('id')
                if container_id:
                    print(f"[instagram] ✅ Container created with API {api_version}: {container_id}")
                    break
            else:
                error_data = container_response.json() if container_response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                error_code = error_data.get('error', {}).get('code', 'N/A')
                error_type = error_data.get('error', {}).get('type', 'N/A')

                print(f"[instagram] ❌ API {api_version} failed:")
                print(f"[instagram]    Error type: {error_type}")
                print(f"[instagram]    Error code: {error_code}")
                print(f"[instagram]    Error message: {error_msg}")

        if not container_id:
            error_msg = "Failed to create container with all API versions"
            print(f"[instagram] ❌ {error_msg}")
            raise Exception(error_msg)

        # Step 3: Wait for processing
        print(f"[instagram] ⏳ Step 3: Waiting for video processing...")
        max_wait = 180  # Instagram takes longer
        waited = 0

        while waited < max_wait:
            status_url = f"https://graph.facebook.com/v18.0/{container_id}"
            status_params = {
                'fields': 'status_code',
                'access_token': access_token
            }

            status_response = requests.get(status_url, params=status_params, timeout=30)
            status_data = status_response.json()
            status_code = status_data.get('status_code')

            print(f"[instagram] Status: {status_code} (waited {waited}s)")

            if status_code == 'FINISHED':
                print(f"[instagram] ✅ Video processing complete!")
                break
            elif status_code == 'ERROR':
                error_msg = status_data.get('error_message', 'Video processing failed')
                print(f"[instagram] ❌ {error_msg}")
                raise Exception(error_msg)

            time.sleep(15)
            waited += 15

        if waited >= max_wait:
            error_msg = "Video processing timed out"
            print(f"[instagram] ❌ {error_msg}")
            raise Exception(error_msg)

        # Step 4: Publish
        print(f"[instagram] 📤 Step 4: Publishing to Instagram...")
        publish_url = f"https://graph.facebook.com/v18.0/{user_id}/media_publish"
        publish_params = {
            'access_token': access_token,
            'creation_id': container_id
        }

        publish_response = requests.post(publish_url, params=publish_params, timeout=60)

        if publish_response.status_code != 200:
            error_data = publish_response.json() if publish_response.text else {}
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"[instagram] ❌ Publish failed: {error_msg}")
            raise Exception(f"Instagram Publish Error: {error_msg}")

        media_id = publish_response.json().get('id')

        print(f"[instagram] ✅ SUCCESS! Video published to Instagram!")
        print(f"[instagram] Media ID: {media_id}")
        print(f"[instagram] Check your Instagram profile to see the Reel!")
        print("=" * 60)

        return {
            'id': media_id,
            'platform': 'instagram',
            'status': 'success'
        }

    except Exception as e:
        print(f"[instagram] ❌ ERROR!")
        print(f"[instagram] {str(e)}")
        print("=" * 60)
        raise

def main():
    """Test upload to Instagram."""
    video_file = Path('output/final_video.mp4')

    if not video_file.exists():
        print(f"[instagram] ❌ Video not found: {video_file}")
        return

    # Read story for caption
    story_file = Path('output/story.txt')
    if story_file.exists():
        caption = story_file.read_text(encoding='utf-8')[:2200]  # Instagram caption limit
    else:
        caption = "Geschichte der antiken Frauen 🏛️ #Shorts #Geschichte #Frauen"

    try:
        result = upload_to_instagram(str(video_file), caption)
        print(f"\n✅ Success! Result: {result}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == '__main__':
    main()