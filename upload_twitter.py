"""
Enhanced Twitter/X Upload Script

Uploads videos to Twitter/X using Twitter API v2 with improved error handling and authentication verification.

Requirements:
- Twitter Developer Account with Elevated access ($100/month for video uploads)
- TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""

import os
from pathlib import Path
import tweepy
import time
import requests
from urllib.parse import urlparse

def upload_to_twitter(video_file, caption):
    """Upload video to Twitter/X using API v2 with enhanced error handling and authentication verification."""
    
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_secret = os.getenv('TWITTER_ACCESS_SECRET')
    
    if not all([api_key, api_secret, access_token, access_secret]):
        raise ValueError(
            "Missing Twitter credentials! Set these environment variables:\n"
            "  - TWITTER_API_KEY\n"
            "  - TWITTER_API_SECRET\n"
            "  - TWITTER_ACCESS_TOKEN\n"
            "  - TWITTER_ACCESS_SECRET\n"
            "\nNote: Requires Twitter API Elevated access (~$100/month) for video uploads"
        )
    
    print("[twitter] Uploading to Twitter/X...")
    
    # Verify authentication first
    try:
        verify_authentication(api_key, api_secret, access_token, access_secret)
    except Exception as e:
        raise Exception(f"Authentication failed: {e}")
    
    # Authenticate with Twitter API v1.1 for media upload
    auth = tweepy.OAuth1UserHandler(
        api_key, api_secret,
        access_token, access_secret
    )
    api_v1 = tweepy.API(auth)
    
    # Authenticate with Twitter API v2 for posting
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )
    
    # Upload video with retry logic (uses v1.1 API)
    print("[twitter] Uploading video...")
    max_retries = 3
    media = None
    
    for attempt in range(max_retries):
        try:
            media = api_v1.media_upload(
                filename=str(video_file),
                media_category='tweet_video'
            )
            print(f"[twitter] Video uploaded, media_id: {media.media_id}")
            break
        except tweepy.TooManyRequests as e:
            print(f"[twitter] Rate limited! Attempt {attempt + 1} failed.")
            if attempt < max_retries - 1:
                wait_time = min(60 * (2 ** attempt), 300)  # Exponential backoff, max 5 minutes
                print(f"[twitter] Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                raise Exception("Rate limit exceeded after maximum retries")
        except Exception as e:
            print(f"[twitter] Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise Exception(f"Failed to upload video after {max_retries} attempts")
    
    if not media:
        raise Exception("Failed to upload media")
    
    # Wait for media processing
    print("[twitter] Waiting for media processing...")
    wait_for_media_processing(api_v1, media.media_id)
    
    # Create tweet with video (uses v2 API)
    print("[twitter] Posting tweet...")
    
    # Twitter has 280 character limit
    tweet_text = caption[:280] if len(caption) > 280 else caption
    
    # Retry logic for tweet creation
    tweet_success = False
    tweet_id = None
    
    for attempt in range(max_retries):
        try:
            response = client.create_tweet(
                text=tweet_text,
                media_ids=[media.media_id]
            )
            tweet_id = response.data['id']
            tweet_success = True
            break
        except tweepy.TooManyRequests as e:
            print(f"[twitter] Rate limited on tweet creation! Attempt {attempt + 1} failed.")
            if attempt < max_retries - 1:
                wait_time = min(60 * (2 ** attempt), 300)
                print(f"[twitter] Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                raise Exception("Rate limit exceeded after maximum retries")
        except Exception as e:
            print(f"[twitter] Tweet creation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise Exception(f"Failed to create tweet after {max_retries} attempts")
    
    if not tweet_success or not tweet_id:
        raise Exception("Failed to create tweet")
    
    print(f"[twitter] ✅ Posted to Twitter! Tweet ID: {tweet_id}")
    print(f"[twitter] URL: https://twitter.com/i/web/status/{tweet_id}")
    
    return {
        'id': tweet_id,
        'url': f"https://twitter.com/i/web/status/{tweet_id}",
        'media_id': media.media_id,
        'platform': 'twitter'
    }

def verify_authentication(api_key, api_secret, access_token, access_secret):
    """Verify Twitter API authentication."""
    print("[twitter] Verifying authentication...")
    
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)
    
    try:
        # Test authentication by getting user info
        user = api.verify_credentials()
        print(f"[twitter] ✅ Authenticated as @{user.screen_name}")
        return True
    except Exception as e:
        raise Exception(f"Authentication verification failed: {e}")

def wait_for_media_processing(api, media_id):
    """Wait for Twitter media processing to complete."""
    max_wait = 120  # 2 minutes
    waited = 0
    wait_interval = 5
    
    while waited < max_wait:
        try:
            status = api.get_media_upload_status(media_id)
            processing_info = status.processing_info
            
            if processing_info:
                state = processing_info.get('state')
                print(f"[twitter] Media processing state: {state} ({waited}s)")
                
                if state == 'succeeded':
                    print("[twitter] ✅ Media processing complete!")
                    return
                elif state == 'failed':
                    error = processing_info.get('error', {})
                    raise Exception(f"Media processing failed: {error}")
                
                # Check for progress info
                progress_percent = processing_info.get('progress_percent')
                if progress_percent:
                    print(f"[twitter] Processing progress: {progress_percent}%")
            
            time.sleep(wait_interval)
            waited += wait_interval
            
        except AttributeError:
            # If processing_info is not available, assume processing is complete
            print("[twitter] Media processing status not available, assuming complete.")
            return
        except Exception as e:
            print(f"[twitter] Media status check failed: {e}")
            time.sleep(wait_interval)
            waited += wait_interval
    
    print("[twitter] ⚠️  Media may still be processing. Proceeding with tweet creation.")

def main():
    """Test upload to Twitter."""
    video_file = Path('output/final_video.mp4')
    
    if not video_file.exists():
        print("[twitter] ❌ No video found at output/final_video.mp4")
        return
    
    # Read story for caption
    story_file = Path('output/story.txt')
    if story_file.exists():
        story = story_file.read_text(encoding='utf-8')
        # Create short caption for Twitter
        first_sentence = story.split('.')[0] if '.' in story else story[:200]
        caption = f"{first_sentence}... 🏛️\n\n#Geschichte #AntikeFrauen"
    else:
        caption = "Die Geschichte der Frauen in der Antike 🏛️ #Geschichte #AntikeFrauen"
    
    try:
        upload_to_twitter(video_file, caption)
    except Exception as e:
        print(f"[twitter] ❌ Upload failed: {e}")
        raise

if __name__ == '__main__':
    main()
