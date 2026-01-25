"""
Twitter/X Upload - Enhanced Version
Uploads videos to Twitter/X using official APIs with improved error handling
"""

import os
from pathlib import Path
import tweepy
import time

def upload_to_twitter(video_path, caption):
    """
    Upload video to Twitter/X using API v2 with enhanced error handling.
    """

    print("\n" + "=" * 60)
    print("🐦 TWITTER UPLOAD STARTING")
    print("=" * 60)

    # Get credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_secret = os.getenv('TWITTER_ACCESS_SECRET')

    if not all([api_key, api_secret, access_token, access_secret]):
        error_msg = (
            "❌ Missing Twitter credentials! Set these environment variables:\n"
            "  - TWITTER_API_KEY\n"
            "  - TWITTER_API_SECRET\n"
            "  - TWITTER_ACCESS_TOKEN\n"
            "  - TWITTER_ACCESS_SECRET\n"
            "\nNote: Requires Twitter API Elevated access (~$100/month) for video uploads"
        )
        print(f"[twitter] {error_msg}")
        raise ValueError(error_msg)

    print(f"[twitter] ✅ Credentials loaded")
    print(f"[twitter] API Key: {api_key[:10]}...")
    print(f"[twitter] Access Token: {access_token[:10]}...")

    # Check video file
    video_path_obj = Path(video_path)
    if not video_path_obj.exists():
        error_msg = f"❌ Video file not found: {video_path}"
        print(f"[twitter] {error_msg}")
        raise FileNotFoundError(error_msg)

    file_size_mb = video_path_obj.stat().st_size / (1024 * 1024)
    print(f"[twitter] ✅ Video file found: {video_path}")
    print(f"[twitter] Video size: {file_size_mb:.2f} MB")

    # Limit caption to Twitter's 280 character limit
    caption_limited = caption[:280] if len(caption) > 280 else caption
    print(f"[twitter] Caption length: {len(caption_limited)}/280 characters")

    try:
        # Step 1: Authenticate with Twitter APIs
        print(f"[twitter] 🔐 Step 1: Authenticating with Twitter APIs...")

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

        # Test authentication
        try:
            api_v1.verify_credentials()
            print(f"[twitter] ✅ API v1.1 authentication successful")
        except Exception as e:
            error_msg = f"API v1.1 authentication failed: {e}"
            print(f"[twitter] ❌ {error_msg}")
            raise Exception(error_msg)

        print(f"[twitter] ✅ Authentication successful")

        # Step 2: Upload video (uses v1.1 API)
        print(f"[twitter] 📤 Step 2: Uploading video to Twitter...")
        print(f"[twitter] This may take a few minutes for large videos...")

        start_time = time.time()
        media = api_v1.media_upload(
            filename=str(video_path_obj),
            media_category='tweet_video',
            wait_for_async_finalize=True  # Wait for processing to complete
        )
        upload_time = time.time() - start_time

        print(f"[twitter] ✅ Video uploaded in {upload_time:.1f}s, media_id: {media.media_id}")

        # Step 3: Create tweet with video (uses v2 API)
        print(f"[twitter] 📝 Step 3: Creating tweet with video...")

        response = client.create_tweet(
            text=caption_limited,
            media_ids=[media.media_id]
        )

        tweet_id = response.data['id']
        tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"

        print(f"[twitter] ✅ SUCCESS! Tweet posted to Twitter/X!")
        print(f"[twitter] Tweet ID: {tweet_id}")
        print(f"[twitter] URL: {tweet_url}")
        print(f"[twitter] Check your Twitter profile to see the tweet!")
        print("=" * 60)

        return {
            'id': tweet_id,
            'url': tweet_url,
            'platform': 'twitter',
            'status': 'success'
        }

    except tweepy.TweepyException as e:
        error_msg = f"Twitter API error: {e}"
        print(f"[twitter] ❌ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"[twitter] ❌ {error_msg}")
        print("=" * 60)
        raise

def main():
    """Test upload to Twitter."""
    video_file = Path('output/final_video.mp4')

    if not video_file.exists():
        print(f"[twitter] ❌ Video not found: {video_file}")
        return

    # Read story for caption
    story_file = Path('output/story.txt')
    if story_file.exists():
        story = story_file.read_text(encoding='utf-8')
        # Create short caption for Twitter
        first_sentence = story.split('.')[0] if '.' in story else story[:200]
        caption = f"{first_sentence}... 🏛️\n\n#Geschichte #AntikeFrauen"
    else:
        caption = "Geschichte der antiken Frauen 🏛️ #Geschichte #AntikeFrauen"

    try:
        result = upload_to_twitter(str(video_file), caption)
        print(f"\n✅ Success! Result: {result}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")

if __name__ == '__main__':
    main()