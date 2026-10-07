"""Hear the natural voice in every language:   python voice_test.py
(needs internet the first time; afterwards the sentences are cached and play offline)"""
import subprocess
import speaker

for lang in ("en", "hi", "te", "ta"):
    text = speaker.sentence(lang, {"cls": "chair", "side": "ahead", "dist": 2})
    mp3 = speaker.synthesize(lang, text)
    print(f"{lang}: {text}  ->  {'natural voice' if mp3 else 'NO INTERNET: robotic fallback'}")
    if mp3:
        subprocess.run(["mpg123", "-q", str(mp3)])
    else:
        subprocess.run(["espeak-ng", "-v", speaker.VOICES[lang], text])
