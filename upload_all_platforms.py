"""
Uploads generated shorts to YouTube
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

upload_dir = Path(__file__).parent / "upload"
if upload_dir.exists() and str(upload_dir) not in sys.path:
    sys.path.insert(0, str(upload_dir))

# Facebook upload permanently disabled per user instruction
upload_to_facebook = None
upload_to_instagram = None
upload_to_youtube = None
upload_to_vk = None
upload_to_telegram = None
upload_to_twitter = None
upload_to_threads = None
upload_to_tiktok = None

try:
    from upload_to_youtube import upload_to_youtube as yt_upload
    upload_to_youtube = yt_upload
except ImportError as e:
    print(f"[!] YouTube upload module not available: {e}")


def is_valid_text(text: str) -> bool:
    """Validate that text is clean historical content and not an API error or garbage."""
    if not text or len(text.strip()) < 10:
        return False
    lower = text.lower()
    error_keywords = [
        "credit", "credits", "top up", "top-up", "pollinations", "api key",
        "balance", "rate limit", "error", "unauthorized", "quota", "billing",
        "quest", "account behind", "tokens", "http", "402", "429", "insufficient",
        "service you're using", "service youre using"
    ]
    return not any(kw in lower for kw in error_keywords)


def sanitize_story_text(text: str) -> str:
    if not text:
        return ""
    if not is_valid_text(text):
        return ""
    cleaned = re.sub(r'https?://\S+', '', text)
    cleaned = re.sub(r'[*_#\[\]\(\)<>]', '', cleaned)
    return " ".join(cleaned.split()).strip()


def get_clean_topic() -> str:
    """Retrieve and sanitize the current topic."""
    topic = "Ancient History"
    topic_file = Path("output/topic.txt")
    if topic_file.exists():
        try:
            t = topic_file.read_text(encoding="utf-8").strip()
            if t and is_valid_text(t):
                topic = t
        except Exception:
            pass
    return topic


def get_video_title() -> str:
    """Generate a clean, high-impact YouTube Shorts title (max 100 chars, with #Shorts)."""
    topic = get_clean_topic()
    
    clean_topic = re.sub(r'[\r\n\t]+', ' ', topic)
    clean_topic = ' '.join(clean_topic.split()).strip('"-–—| ')
    clean_topic = re.sub(r'[*_#\[\]\(\)]', '', clean_topic)
    
    branded_suffix = " | Antike Geschichte #Shorts"
    short_suffix = " #Shorts"
    
    if len(clean_topic) + len(branded_suffix) <= 100:
        return f"{clean_topic}{branded_suffix}"
    elif len(clean_topic) + len(short_suffix) <= 100:
        return f"{clean_topic}{short_suffix}"
    else:
        max_allowed = 100 - len(short_suffix) - 3
        truncated = clean_topic[:max_allowed]
        if " " in truncated:
            truncated = truncated.rsplit(" ", 1)[0]
        return f"{truncated}...{short_suffix}"


def get_latest_reel():
    fv = Path("output/final_video.mp4")
    if fv.exists():
        latest = fv
    else:
        video_dir = Path("output/video")
        if not video_dir.exists():
            print("No output/video directory found")
            return None
        reels = list(video_dir.glob("*/final_reel.mp4"))
        if not reels:
            print("No reels found in output/video directory")
            return None
        latest = max(reels, key=lambda p: p.stat().st_mtime)
        
    metadata_file = latest.parent / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass
            
    topic = get_clean_topic()

    return {
        "video_path": str(latest),
        "metadata": metadata,
        "category": topic,
        "phrases": metadata.get("phrases", [])
    }


def get_english_story() -> str:
    try:
        ef = Path("output/story_en.txt")
        if ef.exists():
            return sanitize_story_text(ef.read_text(encoding="utf-8"))
    except Exception:
        pass
    return ""


def get_native_story() -> str:
    try:
        nf = Path("output/story.txt")
        if nf.exists():
            return sanitize_story_text(nf.read_text(encoding="utf-8"))
    except Exception:
        pass
    return ""


def generate_caption(phrases=None, category="Ancient History", platform="youtube"):
    """
    Generate professional, informative bilingual YouTube description:
    Topic + Native Story + English Translation + Channel CTA + Hashtags.
    """
    topic = get_clean_topic()
    native_text = get_native_story()
    en_text = get_english_story()

    lines = [
        f"🏛️ {topic}",
        ""
    ]

    if native_text and is_valid_text(native_text):
        lines.append(native_text.strip())
        lines.append("")
    else:
        lines.append(f"{topic} - Ancient History.")
        lines.append("")

    if en_text and is_valid_text(en_text):
        lines.append("📖 English Translation:")
        lines.append(en_text.strip())
        lines.append("")

    lines.extend(['✨ Abonnieren für tägliche Geschichten aus der antiken Geschichte und Mythologie!', '🔔 Aktiviere die Glocke, um keine Folge zu verpassen.'])
    lines.extend([
        "",
        "#Shorts #AncientHistory #History #AntikeGeschichte #WomensHistory"
    ])

    return "\n".join(lines)


def upload_to_all_platforms(video_path, caption, category, phrases=None, video_title=""):
    results = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "video": video_path,
        "uploads": {},
        "platforms_attempted": [],
        "platforms_successful": [],
        "platforms_skipped": [],
        "platforms_failed": []
    }

    print("\n" + "=" * 80)
    print("YOUTUBE SHORTS UPLOAD")
    print("=" * 80)
    print(f"Video: {video_path}")
    print(f"Title: {video_title}")
    print(f"Category: {category}")
    print(f"Description length: {len(caption)} characters")
    print("=" * 80)

    if not Path(video_path).exists():
        print(f"[ERROR] Video file not found: {video_path}")
        return results

    # Only YouTube is enabled per user requirements (Facebook strictly disabled)
    platforms = [
        ("youtube", upload_to_youtube, "YouTube"),
    ]

    tags = ['Ancient History', 'Geschichte', 'Antike Geschichte', 'Mythologie', 'Shorts', 'History', 'Womens History']

    for platform_name, upload_func, display_name in platforms:
        print(f"\n{display_name} UPLOAD...")
        results["platforms_attempted"].append(platform_name)

        if upload_func:
            try:
                upload_result = upload_func(video_path, video_title, caption, tags)
                if upload_result:
                    results["uploads"][platform_name] = upload_result
                    results["platforms_successful"].append(platform_name)
                else:
                    results["uploads"][platform_name] = {"status": "failed", "error": "Upload function returned None"}
                    results["platforms_failed"].append(platform_name)
            except Exception as e:
                error_msg = str(e)
                results["uploads"][platform_name] = {"status": "failed", "error": error_msg}
                results["platforms_failed"].append(platform_name)
                print(f"  Error: {error_msg}")
        else:
            results["uploads"][platform_name] = {"status": "skipped", "reason": "Module not available"}
            results["platforms_skipped"].append(platform_name)

    print("\n" + "=" * 60)
    print("UPLOAD STATUS REPORT")
    print("=" * 60)
    pinfo = results["uploads"].get("youtube", {})
    if pinfo and pinfo.get("status") in ("success", "published"):
        pid = pinfo.get("id", "N/A")
        link = pinfo.get("link") or f"https://youtube.com/shorts/{pid}"
        print(f"YOUTUBE: SUCCESS (ID: {pid}) LINK: {link}")
    elif pinfo:
        err = str(pinfo.get("error", ""))[:120]
        print(f"YOUTUBE: FAILED - {err}")
    else:
        print("YOUTUBE: SKIPPED")
    print("=" * 60)

    results_file = Path("output") / f"upload_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def main():
    print("\n" + "=" * 80)
    print("AUTOMATED YOUTUBE UPLOAD")
    print("=" * 80)

    reel = get_latest_reel()
    if not reel:
        print("\nNo reel found!")
        sys.exit(1)

    print(f"\nFound latest reel:")
    print(f"   Category: {reel['category']}")
    print(f"   Video: {reel['video_path']}")
    print(f"   Phrases: {len(reel['phrases'])}")

    video_title = get_video_title()
    caption = generate_caption(reel['phrases'], reel['category'], platform="youtube")
    
    print(f"\nGenerated Title: {video_title}")
    print(f"Generated Description ({len(caption)} chars):")
    print("-" * 80)
    print(caption)
    print("-" * 80)

    results = upload_to_all_platforms(reel['video_path'], caption, reel['category'], reel['phrases'], video_title)

    successful = len(results.get("platforms_successful", []))
    if successful > 0:
        print(f"\nUpload complete! YouTube video successfully published.")
        sys.exit(0)
    else:
        print("\nYouTube upload failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
