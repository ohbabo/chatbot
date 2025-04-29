import os,logging,requests
SUPERTONE_API_KEY = os.getenv('SUPERTONE_API_KEY')
"""
def get_supertone_voices():
   
    SuperTone API를 호출하여 사용 가능한 보이스 목록을 가져옵니다.

    Returns:
        list: 보이스 정보의 리스트
    
    url = "https://supertoneapi.com/v1/voices"
    headers = {
        "x-sup-api-key": SUPERTONE_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            voices = response.json().get('voices', [])
            logging.info(f"가져온 보이스 수: {len(voices)}")
            return voices
        else:
            logging.error(f"보이스 가져오기 실패: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logging.error(f"SuperTone 보이스 가져오기 중 오류 발생: {str(e)}")
        return []


if __name__ == "__main__":
    voices = get_supertone_voices()
    for voice in voices:
        print(f"Voice ID: {voice['voice_id']}, Name: {voice['name']}")
"""

import requests
url = "https://supertoneapi.com/v1/text-to-speech/cgwRLxwBrcdjSVQHW8nBXy"

querystring = {"output_format":"wav"}

payload = {
    "language": "ko",
    "text": "오늘 힘든 하루를 보내셨군요. 그런 날은 정말 지치고 힘들 수 있어요",
    "model": "pro",
    "voice_settings": {
        "pitch_shift": -4,
        "pitch_variance": 0.9,
        "speed": 0.8
    }
}
headers = {
    "x-sup-api-key": "3cd79b366c36dc4925652d0cf6aa5a06",
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers, params=querystring)

print("Content-Type:", response.headers.get('Content-Type'))
if response.status_code == 200:
    with open("output.wav", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print("음성 파일이 'output.wav'로 저장되었습니다.")
else:
    print(f"TTS 생성 실패: {response.status_code}")
    print(response.text)