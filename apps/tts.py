# tts.py
import os
import time
import requests
from datetime import datetime


# Supertone API 설정
SUPERTONE_API_URL = "https://supertoneapi.com/v1/text-to-speech/cgwRLxwBrcdjSVQHW8nBXy"
SUPERTONE_API_KEY = os.getenv('SUPERTONE_API_KEY')

# TTS 생성 함수
def generate_supertone_tts(text, output_path):
    payload = {
        "language": "ko",
        "text": text,
        "model": "pro",
        "voice_settings": {
            "pitch_shift": -4,
            "pitch_variance": 0.9,
            "speed": 0.8
        }
    }
    headers = {
        "x-sup-api-key": SUPERTONE_API_KEY,
        "Content-Type": "application/json"
    }
    querystring = {"output_format": "wav"}

    try:
        response = requests.post(SUPERTONE_API_URL, json=payload, headers=headers, params=querystring)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"[{datetime.now()}] TTS 생성 성공: {output_path}")
            return True
        else:
            print(f"[{datetime.now()}] TTS 생성 실패: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"[{datetime.now()}] TTS 생성 중 예외 발생: {e}")
        return False
