"""
Generate 600+ German topics about ancient women's history using paid Pollinations API
"""

import requests
from urllib.parse import quote
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_german_topics():
    """Generate 600+ unique German topics about ancient women's history using paid Pollinations API."""
    
    api_key = os.getenv("POLLINATIONS_API_KEY")
    if not api_key:
        raise ValueError("POLLINATIONS_API_KEY environment variable is required for paid API")
    
    prompt = """Generiere 600 einzigartige deutsche Themen über die Geschichte der Frauen in antiken Zivilisationen.

Anforderungen:
- Jedes Thema sollte eine einzelne Zeile sein
- Fokus auf historische Fakten, Gesetze, Bräuche, Traditionen
- Decke verschiedene antike Zivilisationen ab (Griechenland, Rom, Ägypten, Mesopotamien, China, Indien, Persien, etc.)
- Variiere die Themen: Berufe, Rechte, Rollen, berühmte Frauen, religiöse Praktiken, etc.
- Keine Nummerierung, nur die Themen
- Verwende das Format: "Die [Thema] in [Zivilisation/Zeitperiode]"

Beispiele:
Die Erbgesetze im antiken Griechenland
Die Kleidungsvorschriften in Sparta
Die Bewegungseinschränkungen für Frauen in Athen
Die Frauen im antiken Rom
Die Rechte der Frauen im antiken Ägypten

Generiere jetzt 600 einzigartige Themen:"""

    print("[topics] Generating 600 German topics about ancient women's history using paid API...")
    
    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nova-fast",
        "messages": [
            {"role": "system", "content": "Du bist ein Historiker, der sich auf die Geschichte der Frauen in antiken Zivilisationen spezialisiert hat."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1.0
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    
    topics_text = response.json()['choices'][0]['message']['content'].strip()
    topics = [line.strip() for line in topics_text.split('\n') if line.strip() and not line.strip().startswith('#')]
    
    # Remove any numbering that might have been added
    cleaned_topics = []
    for topic in topics:
        # Remove leading numbers like "1. ", "1) ", etc.
        import re
        cleaned = re.sub(r'^\d+[\.\)]\s*', '', topic)
        if cleaned and len(cleaned) > 10:
            cleaned_topics.append(cleaned)
    
    print(f"[topics] Generated {len(cleaned_topics)} German topics")
    
    # If we don't have enough, generate more
    while len(cleaned_topics) < 600:
        print(f"[topics] Need more topics, generating additional batch...")
        
        additional_prompt = f"Generiere 100 weitere einzigartige deutsche Themen über die Geschichte der Frauen in antiken Zivilisationen. Verwende das Format: 'Die [Thema] in [Zivilisation/Zeitperiode]'. Keine Nummerierung."
        
        url = "https://gen.pollinations.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "nova-fast",
            "messages": [
                {"role": "system", "content": "Du bist ein Historiker, der sich auf die Geschichte der Frauen in antiken Zivilisationen spezialisiert hat."},
                {"role": "user", "content": additional_prompt}
            ],
            "temperature": 1.2
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        more_topics = [line.strip() for line in response.json()['choices'][0]['message']['content'].strip().split('\n') if line.strip()]
        for topic in more_topics:
            import re
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', topic)
            if cleaned and len(cleaned) > 10 and cleaned not in cleaned_topics:
                cleaned_topics.append(cleaned)
        
        print(f"[topics] Now have {len(cleaned_topics)} topics")
    
    # Save to topics.txt
    with open('topics.txt', 'w', encoding='utf-8') as f:
        for topic in cleaned_topics[:600]:  # Ensure exactly 600
            f.write(topic + '\n')
    
    print(f"[topics] ✅ Saved {min(len(cleaned_topics), 600)} German topics to topics.txt using paid API")
    return cleaned_topics[:600]

if __name__ == '__main__':
    topics = generate_german_topics()
    print(f"\n[topics] Sample topics:")
    for i, topic in enumerate(topics[:10], 1):
        print(f"  {i}. {topic}")
