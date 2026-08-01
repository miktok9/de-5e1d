"""
TikTok Upload - Enhanced Version
Uses TikTok Content Posting API with improved error handling
"""

import os
import requests
import time
from pathlib import Path

def upload_to_tiktok(video_path, title, description):
    """
    Upload video to TikTok using Content Posting API.
    """

    print("\n" + "=" * 60)
    print("🎵 TIKTOK UPLOAD STARTING")
    print("=" * 60)

    # Get credentials
    access_token = os.getenv('TIKTOK_ACCESS_TOKEN')

    if not access_token:
        error_msg = "❌ TIKTOK_ACCESS_TOKEN not set"
        print(f"[tiktok] {error_msg}")
        raise ValueError(error_msg)

    print(f"[tiktok] ✅ Credentials loaded")
    print(f"[tiktok] Token length: {len(access_token)} chars")

    # Check video file
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[tiktok] {error_msg}")
        raise FileNotFoundError(error_msg)

    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[tiktok] ✅ Video file found: {video_path}")
    print(f"[tiktok] Video size: {file_size_mb:.2f} MB")

    # Limit title and description
    title_limited = title[:220] if len(title) > 220 else title
    description_limited = description[:2200] if len(description) > 2200 else description
    print(f"[tiktok] Title length: {len(title_limited)} characters")
    print(f"[tiktok] Description length: {len(description_limited)} characters")

    try:
        # Step 1: Initialize upload with TikTok API
        print(f"[tiktok] 📤 Step 1: Initializing TikTok upload...")

        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Try different source configurations
        source_configs = [
            {
                'source': 'FILE_UPLOAD',
                'video_size': video_path_obj.stat().st_size,
                'chunk_size': 10000000,
                'total_chunk_count': 1
            },
            {
                'source': 'PULL_FROM_URL',
                'video_url': None  # Will be set after temp upload
            }
        ]

        publish_id = None
        upload_url = None

        for config in source_configs:
            print(f"[tiktok] Trying source config: {config['source']}")

            data = {
                'post_info': {
                    'title': title_limited,
                    'description': description_limited,
                    'privacy_level': 'PUBLIC_TO_EVERYONE',
                    'disable_duet': False,
                    'disable_comment': False,
                    'disable_stitch': False,
                    'video_cover_timestamp_ms': 1000
                },
                'source_info': config
            }

            if config['source'] == 'PULL_FROM_URL':
                # First upload to temp hosting
                print(f"[tiktok] Uploading to temporary hosting for URL-based upload...")

                with open(video_path_obj, 'rb') as video_file:
                    files = {'file': ('video.mp4', video_file, 'video/mp4')}
                    temp_response = requests.post(
                        'https://tmpfiles.org/api/v1/upload',
                        files=files,
                        timeout=180
                    )

                if temp_response.status_code == 200:
                    temp_data = temp_response.json()
                    if temp_data.get('status') == 'success':
                        temp_url = temp_data.get('data', {}).get('url', '')
                        video_url = temp_url.replace('tmpfiles.org/', 'tmpfiles.org/dl/').replace('http://', 'https://')
                        data['source_info']['video_url'] = video_url
                        print(f"[tiktok] ✅ Temporary URL: {video_url}")
                    else:
                        print(f"[tiktok] ⚠️  Temp hosting failed, skipping URL method")
                        continue

            init_response = requests.post(init_url, headers=headers, json=data, timeout=60)

            print(f"[tiktok] Init response status: {init_response.status_code}")
            print(f"[tiktok] Init response: {init_response.text}")

            if init_response.status_code == 200:
                result = init_response.json()
                if 'data' in result and result['data'].get('publish_id'):
                    publish_id = result['data']['publish_id']
                    upload_url = result['data'].get('upload_url')
                    print(f"[tiktok] ✅ Upload initialized: {publish_id}")
                    break
            else:
                error_data = init_response.json() if init_response.text else {}
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                print(f"[tiktok] ❌ Init failed: {error_msg}")

        if not publish_id:
            error_msg = "Failed to initialize upload with any configuration"
            print(f"[tiktok] ❌ {error_msg}")
            raise Exception(error_msg)

        # Step 2: Upload video if we have an upload URL (FILE_UPLOAD method)
        if upload_url and 'tmpfiles.org' not in str(video_path):
            print(f"[tiktok] 📤 Step 2: Uploading video file...")

            with open(video_path_obj, 'rb') as f:
                video_data = f.read()

            upload_response = requests.put(
                upload_url,
                headers={'Content-Type': 'video/mp4'},
                data=video_data,
                timeout=300  # Long timeout for video upload
            )

            if upload_response.status_code not in [200, 201]:
                error_msg = f"Video upload failed: {upload_response.status_code}"
                print(f"[tiktok] ❌ {error_msg}")
                print(f"[tiktok] Response: {upload_response.text[:200]}")
                raise Exception(error_msg)

            print(f"[tiktok] ✅ Video file uploaded successfully")

        # Step 3: Check status
        print(f"[tiktok] ⏳ Step 3: Checking upload status...")

        status_url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        max_checks = 30

        for check in range(max_checks):
            status_data = {
                'publish_id': publish_id
            }

            status_response = requests.post(status_url, headers=headers, json=status_data, timeout=30)
            status_result = status_response.json()

            status = status_result.get('data', {}).get('status')
            print(f"[tiktok] Status check {check + 1}: {status}")

            if status == 'SUCCESS':
                print(f"[tiktok] ✅ SUCCESS! Video published to TikTok!")
                print(f"[tiktok] Publish ID: {publish_id}")
                print(f"[tiktok] Check your TikTok profile to see the video!")
                print("=" * 60)

                {'id': publish_id, 'platform': 'tiktok', 'status': 'success', 'link': f"https://www.tiktok.com/@{os.getenv('TIKTOK_USERNAME', '')}/video/{publish_id}"}
            elif status in ['FAILED', 'ERROR']:
                error_msg = status_result.get('data', {}).get('error_message', 'Upload failed')
                print(f"[tiktok] ❌ Upload failed: {error_msg}")
                raise Exception(f"TikTok upload failed: {error_msg}")

            time.sleep(10)  # Wait 10 seconds between checks

        # If we get here, it timed out
        error_msg = "Status check timed out"
        print(f"[tiktok] ❌ {error_msg}")
        raise Exception(error_msg)

    except Exception as e:
        print(f"[tiktok] ❌ ERROR!")
        print(f"[tiktok] {str(e)}")
        print("=" * 60)
        raise

def main():
    """Test upload to TikTok."""
    video_file = Path('output/final_video.mp4')

    if not video_file.exists():
        print(f"[tiktok] ❌ Video not found: {video_file}")
        return

    # Test parameters
    title = "Geschichte der antiken Frauen"
    description = "Entdecken Sie bemerkenswerte Frauen der Antike #Geschichte #Frauen"

    try:
        result = upload_to_tiktok(str(video_file), title, description)
        print(f"\n✅ Success! Result: {result}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == '__main__':
    main()