import json
import re

EMPHASIS_TERMS = [
    "four", "hundred", "tons",
    "minus", "fifty", "degree",
    "forty", "times",
    "molten", "lava",
    "controlled", "fire"
]

with open("/Volumes/Helumi/CinecodeStudio/escapement-reference/audio/jet_vo/transcription.json") as f:
    data = json.load(f)

words = []
for item in data.get("transcription", []):
    t_text = item.get("text", "")
    if not t_text or (t_text.startswith("[_") and t_text.endswith("_]")):
        continue
    timestamps = item.get("timestamps", {})
    t_from = timestamps.get("from")
    t_to = timestamps.get("to")
    
    clean_w = re.sub(r'\[_.*?_\]', '', t_text).strip()
    if not clean_w:
        continue
        
    words.append({
        "word": clean_w,
        "start": t_from,
        "end": t_to,
        "raw": t_text
    })

# Mark emphasis words
for w in words:
    bare = re.sub(r'[^\w]', '', w["word"].lower())
    w["emphasis"] = any(bare == term for term in EMPHASIS_TERMS)

print(f"Total jet words: {len(words)}")

# Group into 2-4 word caption chunks
chunks = []
current_chunk = []

for w in words:
    current_chunk.append(w)
    has_punct = any(p in w["word"] for p in [".", ",", "—", "!", "?"])
    if len(current_chunk) >= 4 or (len(current_chunk) >= 2 and has_punct):
        chunks.append({
            "text": " ".join([item["word"] for item in current_chunk]),
            "start": current_chunk[0]["start"],
            "end": current_chunk[-1]["end"],
            "words": current_chunk
        })
        current_chunk = []

if current_chunk:
    chunks.append({
        "text": " ".join([item["word"] for item in current_chunk]),
        "start": current_chunk[0]["start"],
        "end": current_chunk[-1]["end"],
        "words": current_chunk
    })

with open("/Volumes/Helumi/CinecodeStudio/escapement-reference/audio/jet_vo/words_aligned.json", "w") as f:
    json.dump(words, f, indent=2)

with open("/Volumes/Helumi/CinecodeStudio/escapement-reference/audio/jet_vo/caption_chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)

print(f"Generated {len(chunks)} caption chunks with Whisper timestamps.")
for i, c in enumerate(chunks[:5]):
    print(f"  Chunk {i}: [{c['start']} -> {c['end']}] \"{c['text']}\"")
