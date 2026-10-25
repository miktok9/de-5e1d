import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_authenticated_service():
    client_id = os.getenv('YT_CLIENT_ID')
    client_secret = os.getenv('YT_CLIENT_SECRET')
    refresh_token = os.getenv('YT_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        print("[delete] Missing YouTube credentials in environment!")
        return None
        
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube"]
    )
    creds.refresh(Request())
    return build('youtube', 'v3', credentials=creds)

def main():
    print("=" * 60)
    print("YOUTUBE BAD VIDEO CLEANUP - FULL SCAN")
    print("=" * 60)
    yt = get_authenticated_service()
    if not yt:
        print("[delete] Cannot authenticate to YouTube API.")
        return
        
    try:
        channels_res = yt.channels().list(mine=True, part='contentDetails').execute()
        items = channels_res.get('items', [])
        if not items:
            print("[delete] No channel found.")
            return
            
        uploads_playlist = items[0]['contentDetails']['relatedPlaylists']['uploads']
        page_token = None
        total_scanned = 0
        total_deleted = 0
        
        error_terms = [
            "credit", "top up", "top-up", "pollinations", "api key",
            "doesn't have enough", "account behind", "quest", "quota"
        ]
        
        while True:
            playlist_items = yt.playlistItems().list(
                playlistId=uploads_playlist,
                part='snippet',
                maxResults=50,
                pageToken=page_token
            ).execute()
            
            p_items = playlist_items.get('items', [])
            total_scanned += len(p_items)
            
            for p_item in p_items:
                vid = p_item['snippet']['resourceId']['videoId']
                title = p_item['snippet']['title']
                desc = p_item['snippet']['description']
                combined = (title + " " + desc).lower()
                
                if any(term in combined for term in error_terms):
                    print(f"[delete] Found bad video: '{title[:60]}' (ID: {vid})")
                    try:
                        yt.videos().delete(id=vid).execute()
                        total_deleted += 1
                        print(f"[delete] ✅ SUCCESS: Deleted bad video {vid}")
                    except Exception as ex:
                        print(f"[delete] ❌ Failed to delete {vid}: {ex}")
            
            page_token = playlist_items.get('nextPageToken')
            if not page_token:
                break
                
        print(f"[delete] Scan completed. Scanned: {total_scanned} videos, Deleted: {total_deleted} bad videos.")
    except Exception as e:
        print(f"[delete] Error scanning channel uploads: {e}")

if __name__ == '__main__':
    main()
