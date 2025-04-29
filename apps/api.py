#apps/api.py
from datetime import datetime, date
from .models import db, UserMessage
from flask import flash,session
import openai, logging, uuid, os, json,base64
import re
from flask import current_app


# 난이도 단계별 기간 설정 (예: 3개월 후 '중', 5개월 후 '상')
STAGE_THRESHOLDS = {
    '쉬움': 1,  # 가입 후 3개월
    '보통': 2   # 가입 후 5개월
    # '상'은 이후 계속 유지
}
def update_user_stage(user):
    today = date.today()
    months_passed = (today.year - user.signup_date.year) * 12 + today.month - user.signup_date.month

    new_stage = user.current_stage
    if user.current_stage == '쉬움' and months_passed >= STAGE_THRESHOLDS['쉬움']:
        new_stage = '보통'
    elif user.current_stage == '보통' and months_passed >= STAGE_THRESHOLDS['보통']:
        new_stage = '어려움'

    if new_stage != user.current_stage:
        user.current_stage = new_stage
        user.last_stage_update = today
        db.session.commit()
        flash(f"난이도가 '{user.current_stage}'으로 업데이트되었습니다.")
    else:
        print(f"No stage update needed for User ID: {user.id}")


def generate_empathic_response(message,emotion,  temperature=0.8):
    base_content = ( "대상은 65세 이상의 노인분들입니다."
            "당신은 친절하고 공감 능력이 뛰어난 상담사입니다. 사용자의 감정에 따른 정서적인 지원을 제공합니다. "
            "우선 감정의 구체적인 내용을 표현할 수 있도록 유도해 주세요. "
    "예를 들어, '혹시 어떤 기분이나 상황인지 조금 더 자세히 말씀해주실 수 있으실까요?'와 같이 질문해 주세요. "
    "또한, 사용자가 모호한 감정 표현 후에 부정적인 감정(예: 슬픔, 불안, 분노, 두려움 등)을 추가로 표현할 때는, "
    "그 감정을 충분히 인지하고 공감하며 상황에 대해 더 구체적인 설명을 요청하는 형태의 응답을 해 주세요. "
    "예시로는 다음과 같은 대화 시퀀스를 참고해 주세요:\n\n"
    "[예시 1]\n"
    "사용자: '요즘 제 기분이 복잡해서 정확히 어떤 감정인지 잘 모르겠어요. 왠지 모를 슬픔과 외로움이 섞여 있는 것 같아요.'\n"
    "상담사: '말씀해주신 걸 보니 복잡한 감정 속에 슬픔과 외로움이 함께 자리 잡고 있는 것 같네요. 그런 감정은 정말 힘들 수 있습니다. 혹시 이런 기분이 언제부터 시작되었는지, 또는 특정 상황에서 더 강하게 느껴지시는지 조금 더 자세히 말씀해주실 수 있으실까요?'\n\n"
    "[예시 2]\n"
    "사용자: '최근 아무 이유 없이 불안감과 짜증이 계속 밀려오는 것 같아요. 평소에 즐기던 일들도 이제는 흥미를 잃은 느낌이라서 마음이 답답합니다.'\n"
    "상담사: '불안과 짜증이 지속된다면 일상생활이 많이 힘들겠어요. 혹시 이러한 감정을 느끼게 된 구체적인 상황이나 최근에 있었던 일이 있으신지 공유해주실 수 있으실까요?'\n\n"
    "[예시 3]\n"
    "사용자: '평소에는 괜찮았던 제가 요즘은 이유 모를 두려움과 슬픔에 압도당하는 느낌이에요.'\n"
    "상담사: '두려움과 슬픔이 크게 느껴지신다니 마음이 무겁습니다. 혹시 이런 감정이 언제부터 시작되었는지, 또는 특별히 기억에 남는 상황이 있으신지 조금 더 이야기해주실 수 있으실까요?'\n\n"
    "상담사의 응답은 다양한 어휘와 문장 구조를 활용하여 자연스럽게 이어지도록 해 주세요."
    )
    if emotion == "기타":
        # '기타' 감정에 대해 추가 지침
        base_content += (
            "사용자가 스스로 자신의 감정을 보다 자세히 표현할 수 있도록 유도해 주세요. "
        "예: '혹시 어떤 기분이나 상황인지 조금 더 자세히 말씀해주실 수 있을까요?'와 같이 질문하면서, "
        "사용자가 다양한 단어와 문장으로 자신의 감정을 표현할 수 있도록 여러 가지 예시를 제공해 주세요. "
    )
    else:
        base_content += (
            "사용자의 감정(예: 슬픔, 분노, 두려움, 불안함, 고통 등)이 확인된 경우, 해당 감정을 충분히 인정하고 공감하는 동시에, "
            "다양한 어휘와 문장 구조를 활용하여 여러 가지 형태의 응답(위로, 조언, 격려 등)을 제공해 주세요. "
            "예를 들어, '당신의 슬픔을 충분히 이해합니다. 이런 상황에서는 이렇게 해보시는 것도 좋을 것 같아요.' "
            "또는 '분노를 느끼는 것은 매우 자연스러운 감정입니다. 이러한 감정을 다루기 위해서는 ...'와 같이 다양한 예시를 사용해 주세요. "
        )
    
    system_message = {
        "role": "system", 
        "content":base_content
            }
    emotion_message = {"role": "system", "content": f"감정: {emotion}"}
    user_message = {"role": "user", "content": message}
    
    messages = [system_message, user_message, emotion_message]

    try:
        response = openai.ChatCompletion.create(
                model="gpt-4o-mini-audio-preview-2024-12-17",#"gpt-4o-mini",
                messages=messages,
                max_tokens=1000,
                temperature=temperature,
                top_p=0.8,
                frequency_penalty=0.4,
                presence_penalty=0.6,
                modalities=["text", "audio"],
                audio={ "voice": "alloy", "format": "wav"},
                response_format={"type": "text"} 
            )
        choice = response.choices[0]
        message_content = choice.message.get('content')
        
        if message_content:
            bot_message = message_content.strip()
        else:
            # content가 null인 경우, audio.transcript 사용
            bot_message = choice.message.get('audio', {}).get('transcript', '').strip()
        
        audio_data_base64 = choice.message.get('audio', {}).get('data')

        # 오디오 파일 URL 초기화
        audio_file_url = None

        if audio_data_base64:
            # 오디오 데이터를 디코딩
            audio_bytes = base64.b64decode(audio_data_base64)

            # 고유한 파일명 생성
            filename = f"{uuid.uuid4()}.wav"
            audio_directory = os.path.join(current_app.root_path, 'static', 'audio')
            os.makedirs(audio_directory, exist_ok=True)  # 디렉토리가 없으면 생성
            filepath = os.path.join(audio_directory, filename)

            # 오디오 파일 저장
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            
            # 오디오 파일의 URL 생성
            audio_file_url = f"/static/audio/{filename}"
            logging.info(f"오디오 파일 저장 완료: {audio_file_url}")
        else:
            logging.warning("오디오 데이터가 응답에 포함되지 않았습니다.")

        return bot_message, audio_file_url

    except Exception as e:
        logging.error(f"OpenAI API 호출 중 오류 발생: {str(e)}")
        return None, None

def analyze_emotion(text):
    prompt = f"""
    주어진 텍스트에서 사용자의 주요 감정을 정확하게게 식별하세요.
    텍스트: {text}
    가능한 감정 목록: 슬픔, 기쁨, 분노, 두려움, 놀람, 혐오, 즐거움, 미움, 피곤, 불안함
    감정 :
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 텍스트 분석 전문가입니다." 
                 "감정이 식별될만한 내용을 제외하고는 감정을 기타로 제공해주세요 ."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=10,
            temperature=0,
            top_p=0.8,
            frequency_penalty=0,
            presence_penalty=0,
        )
        emotion = response.choices[0].message['content'].strip()
        match = re.search(r'(슬픔|기쁨|분노|두려움|놀람|혐오|즐거움|피곤|불안함|고통)', emotion)
        if match:
            emotion = match.group(1)
        else:
            emotion = "기타"
        print(f"감정 분석 결과: {emotion}")
        logging.info(f"감정 분석 결과: {emotion}")
        return emotion
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API 감정 분석 호출 오류: {str(e)}")
        raise e
    
def get_or_create_session_id(user):
    if user.session_id:
        return user.session_id
    else:
        session_id = str(uuid.uuid4())
        user.session_id = session_id
        db.session.commit()
        return session_id

