"""
Generate 600 German topics about ancient women's history using paid Pollinations API.
"""

import requests
from urllib.parse import quote
from pathlib import Path
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_german_topics_batch(batch_num, count=100):
    """Generate a batch of German topics using paid Pollinations API."""
    
    api_key = os.getenv("POLLINATIONS_API_KEY")
    if not api_key:
        raise ValueError("POLLINATIONS_API_KEY environment variable is required for paid API")
    
    system = (
        "Du bist ein Historiker, der sich auf die Geschichte der Frauen in antiken Zivilisationen spezialisiert hat. "
        f"Erstelle {count} einzigartige Themen auf Deutsch über Frauen in antiken Zivilisationen. "
        "Jedes Thema sollte 5-10 Wörter lang sein, interessant und lehrreich. "
        "Decke folgende Aspekte ab: Gesetze, Bräuche, berühmte Frauen, Berufe, Religion, Kultur, Kunst. "
        "Gib NUR die Themen aus, eines pro Zeile, ohne Nummerierung oder Aufzählungszeichen."
    )
    
    prompt = f"Erstelle {count} einzigartige deutsche Themen über Frauen in antiken Zivilisationen"
    
    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nova-fast",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.9
    }
    
    print(f"[batch {batch_num}] Generating {count} German topics using paid API...")
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        
        response_text = r.json()['choices'][0]['message']['content'].strip()
        
        # Parse topics
        topics = []
        for line in response_text.split('\n'):
            cleaned = line.strip()
            # Remove common prefixes
            for prefix in ['- ', '* ', '• ', '→ ', '> ']:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
            # Remove numbering
            import re
            cleaned = re.sub(r'^\d+[\.\:\)\-]\s*', '', cleaned)
            
            if cleaned and len(cleaned) > 5:
                topics.append(cleaned)
        
        print(f"[batch {batch_num}] Generated {len(topics)} topics")
        return topics[:count]
    
    except Exception as e:
        print(f"[batch {batch_num}] Error: {e}")
        return []

def main():
    """Generate 600 German topics in batches using paid Pollinations API."""
    
    all_topics = []
    batches = 6  # 6 batches of 100 = 600 topics
    
    for i in range(batches):
        topics = generate_german_topics_batch(i+1, 100)
        all_topics.extend(topics)
        
        print(f"[progress] Total topics so far: {len(all_topics)}")
        
        # Wait between batches to avoid rate limits
        if i < batches - 1:
            print("[progress] Waiting 5 seconds before next batch...")
            time.sleep(5)
    
    # Write to file
    topics_file = Path('topics.txt')
    with open(topics_file, 'w', encoding='utf-8') as f:
        for topic in all_topics:
            f.write(f"{topic}\n")
    
    print(f"\n[done] Generated {len(all_topics)} German topics using paid API!")
    print(f"[done] Saved to {topics_file}")

if __name__ == '__main__':
    main()
