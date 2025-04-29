from datetime import datetime
import openai



def get_time_based_recommendation(temperature=0.7):
    current_hour = datetime.now().hour

    # 4시간 단위로 시간대 구분
    if 0 <= current_hour < 4:
        time_period = "새벽"
    elif 4 <= current_hour < 8:
        time_period = "이른 아침"
    elif 8 <= current_hour < 12:
        time_period = "오전"
    elif 12 <= current_hour < 16:
        time_period = "오후"
    elif 16 <= current_hour < 20:
        time_period = "저녁"
    else:  # 20 <= current_hour < 24
        time_period = "밤"

    # GPT API에 전달할 프롬프트 구성
    prompt = (
        f"현재 시간은 {time_period}입니다."
        f"{time_period}에 맞는 친절하고 인사말을 생성해 주세요."
        f"예를 들어, {time_period}라면 '좋은 {time_period}입니다! '와 같은 메시지를 포함해주세요."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # 사용 가능한 GPT 모델 (예: gpt-4, gpt-3.5-turbo 등)
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly assistant who specializes in generating time-based greetings and recommendations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=100,
            temperature=temperature,
            top_p=0.8,
            frequency_penalty=0,
            presence_penalty=0
        )
        # 응답 메시지에서 인삿말 추출 (텍스트 부분)
        greeting = response.choices[0].message["content"].strip()
        return greeting
    except Exception as e:
        # 오류 발생 시 기본 인삿말 반환
        print(f"Error generating greeting: {str(e)}")
        return f"안녕하세요, 좋은 {time_period}입니다!"