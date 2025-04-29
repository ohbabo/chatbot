# flask_app/views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify,current_app,send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, login_required, logout_user,LoginManager
from .models import db, User, SurveyAnswer, UserActivity,Type, UserMessage, AudioMessage, WelfareCenter, Program
from .utils import  recommend_activities_and_save
from .forms import SignupForm, LoginForm, EditProfileForm, SurveyForm, UpdateStatusForm, EditActivitiesForm
from .audio_utils import transcribe_audio
from .GPS_mapping import distance_km,get_lat_lng_from_address
from .questions import questions
from .recommendation import get_time_based_recommendation
from .api import update_user_stage, generate_empathic_response, analyze_emotion,get_or_create_session_id
from flask_wtf import CSRFProtect
from .decorators import admin_required
from datetime import datetime, timedelta
from flask_mail import Message, Mail
import logging, os
from flask_jwt_extended import create_access_token

mail = Mail()
csrf = CSRFProtect()
login_manager = LoginManager()

main_bp = Blueprint('main_bp', __name__, template_folder='templates', static_folder='static')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@main_bp.route('/api/signup', methods=['POST'])
@csrf.exempt
def api_signup():
    if not request.is_json:
        return jsonify({
            "status": 'error',
            "message": "요청은 JSON 형식이어야 합니다."
        }), 400

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    email = data.get('email')
    address = data.get('address')
    gender = data.get('gender')

    if not all([username, password, name, email, address, gender]):
        return jsonify({
            'status': "error",
            "message": "모든 필드를 입력해주세요."
        }), 400

    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        return jsonify({
            "status": "error",
            "message": "이미 존재하는 아이디 또는 이메일입니다."
        }), 409

    hashed_pw = generate_password_hash(password)
    new_user = User(
        username=username,
        password=hashed_pw,
        name=name,
        email=email,
        address=address,
        gender=gender
    )
    db.session.add(new_user)
    db.session.commit()

    # JWT 기반이라면 login_user() 대신
    # 회원가입 후 자동 로그인 → JWT 발급 로직을 쓸 수도 있음
    # 여기서는 단순히 success만 응답:
    return jsonify({
        "status": "success",
        "message": "회원가입이 완료되었습니다!",
        "user_id": new_user.id
    }), 201


@main_bp.route('/api/login', methods=['POST'])
@csrf.exempt
def api_login():
    """JSON 데이터를 받아서 username/password 검증 후 JWT 토큰을 발급한다."""
    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "요청은 JSON 형식이어야 합니다."
        }), 400

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "status": "error",
            "message": "아이디와 비밀번호를 입력해주세요."
        }), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        # JWT 발급
        token = create_access_token(identity=user.id)
        return jsonify({
            "status": "success",
            "message": "로그인에 성공하였습니다.",
            "token": token
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "로그인 실패. 아이디 또는 비밀번호를 확인하세요."
        }), 401


@main_bp.route('/api/logout', methods=['POST'])
@csrf.exempt
def api_logout():
    # JWT는 stateless하므로, 클라이언트에서 토큰을 삭제하도록 안내합니다.
    # 토큰 블랙리스트 기능이 구현된 경우, 여기에 해당 토큰을 블랙리스트에 등록하는 로직을 추가할 수 있습니다.
    return jsonify({
        "status": "success",
        "message": "로그아웃 처리되었습니다. 클라이언트에서 토큰을 삭제하세요."
    }), 200


from flask_jwt_extended import jwt_required, get_jwt_identity

@main_bp.route('/api/home', methods=['GET'])
@jwt_required()
def api_home():
    # JWT 토큰에서 사용자 식별 정보를 가져옴
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            "status": "error",
            "message": "사용자를 찾을 수 없습니다."
        }), 404

    # 사용자 활동 관련 업데이트
    update_user_stage(user)

    # 사용자 유형 확인
    user_type_id = user.type_id
    if not user_type_id:
        return jsonify({
            "status": "error",
            "message": "사용자 유형이 설정되지 않았습니다. 설문을 완료해주세요.",
            "activities": [],
            "welfare_centers": []
        }), 400

    # 오늘 날짜 기준 활동 추천
    today = datetime.now().date()
    user_activities_today = UserActivity.query.filter_by(
        user_id=user.id, date_recommended=today
    ).all()
    if not user_activities_today:
        recommended_activities = recommend_activities_and_save(user, num_recommendations=3)
        # 활동 객체를 JSON-serializable 형식으로 변환 (예: to_dict() 메서드 활용)
        activities = [activity.to_dict() for activity in recommended_activities]
    else:
        activities = [activity.to_dict() for activity in user_activities_today]

    # 복지관 및 프로그램 정보 처리
    user_address = user.address
    if not user_address:
        welfare_centers = []
    else:
        user_lat, user_lng = get_lat_lng_from_address(user_address)
        if user_lat is None or user_lng is None:
            welfare_centers = []
        else:
            all_centers = WelfareCenter.query.all()
            welfare_centers = []
            for center in all_centers:
                if center.latitude is not None and center.longitude is not None:
                    dist = distance_km(user_lat, user_lng, center.latitude, center.longitude)
                    if dist <= 2.0:
                        programs = Program.query.filter_by(welfare_center_id=center.id).all()
                        program_list = [
                            {
                                "name": program.name,
                                "target": program.target,
                                "schedule": program.schedule,
                                "content": program.content
                            }
                            for program in programs
                        ]
                        address_with_dist = f"{center.addressC} ({dist:.1f}km)"
                        welfare_centers.append({
                            "name": center.name,
                            "addressC": address_with_dist,
                            "phone_number": center.phone_number or "정보 없음",
                            "operator": center.operator or "정보 없음",
                            "programs": program_list
                        })

    return jsonify({
        "status": "success",
        "data": {
            "activities": activities,
            "user_type_id": user_type_id,
            "welfare_centers": welfare_centers
        }
    }), 200

from flask_jwt_extended import jwt_required, get_jwt_identity

@main_bp.route('/api/survey', methods=['GET', 'POST'])
@jwt_required()
def api_survey():
    # JWT 토큰에서 사용자 ID 가져오기
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    question_index = int(request.args.get('question_index', 0))
    total_questions = len(questions)

    # 모든 설문을 완료한 경우: 사용자 유형 업데이트 후 성공 메시지 반환
    if question_index >= total_questions:
        user_type = Type.query.first()
        if user_type:
            user.type_id = user_type.name  # 유형 업데이트
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "설문이 완료되었습니다. 사용자 유형이 설정되었습니다.",
                "redirect": "/api/home"  # 프론트엔드에서 홈으로 이동하도록 처리
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "설문을 완료했지만, 유형을 설정할 수 없습니다."
            }), 500

    # GET 요청: 질문 정보 및 기존 답변 반환
    if request.method == 'GET':
        existing_answer = SurveyAnswer.query.filter_by(
            user_id=user.id, question_no=question_index + 1
        ).first()
        return jsonify({
            "status": "success",
            "data": {
                "question_index": question_index,
                "total_questions": total_questions,
                "question_text": questions[question_index],
                "existing_answer": existing_answer.answer_value if existing_answer else None
            }
        }), 200

    # POST 요청: 답변 저장
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "요청은 JSON 형식이어야 합니다."
            }), 400
        data = request.get_json()
        answer_value = data.get("answer_value")
        if answer_value is None:
            return jsonify({
                "status": "error",
                "message": "답변 값이 제공되지 않았습니다."
            }), 400

        existing_answer = SurveyAnswer.query.filter_by(
            user_id=user.id, question_no=question_index + 1
        ).first()
        if existing_answer:
            existing_answer.answer_value = int(answer_value)
        else:
            survey_answer = SurveyAnswer(
                user_id=user.id,
                question_no=question_index + 1,
                answer_value=int(answer_value),
                date_submitted=datetime.now()
            )
            db.session.add(survey_answer)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "답변이 저장되었습니다.",
            "next_question_index": question_index + 1
        }), 200


@main_bp.route('/api/survey_restart', methods=['POST'])
@jwt_required()
def api_survey_restart():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # 기존 설문 답변 삭제
    SurveyAnswer.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    # 추가로 저장된 모델 결과 등 초기화 (예시)
    user.category = None
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": "설문이 초기화되었습니다.",
        "next_question_index": 0
    }), 200

@main_bp.route('/api/survey_result', methods=['GET'])
@jwt_required()
def api_survey_result():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            "status": "error",
            "message": "사용자를 찾을 수 없습니다."
        }), 404

    # 해당 유저의 모든 설문 답변 조회 (각각 dict 형식으로 변환)
    user_answers = SurveyAnswer.query.filter_by(user_id=user.id).all()
    answers_data = [answer.to_dict() for answer in user_answers] if hasattr(SurveyAnswer, "to_dict") else [
        {
            "question_no": ans.question_no,
            "answer_value": ans.answer_value,
            "date_submitted": ans.date_submitted.isoformat() if ans.date_submitted else None
        }
        for ans in user_answers
    ]
    
    # 사용자 정보도 dict 형식으로 변환 (필요한 필드만 선택)
    user_data = {
        "id": user.id,
        "username": user.username,
        "type": user.type  # 또는 user.type_id 등 실제 저장 필드에 맞게 수정
    }

    return jsonify({
        "status": "success",
        "data": {
            "user": user_data,
            "user_answers": answers_data
        }
    }), 200


@main_bp.route('/api/edit_profile', methods=['GET', 'POST'])
@jwt_required()
def api_edit_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({
            "status": "error",
            "message": "사용자를 찾을 수 없습니다."
        }), 404

    if request.method == 'GET':
        # 현재 사용자 프로필 정보를 JSON으로 반환
        user_data = {
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "address": user.address,
            "gender": user.gender
        }
        return jsonify({
            "status": "success",
            "data": user_data
        }), 200

    # POST 요청: JSON 데이터로 프로필 업데이트 처리
    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "요청은 JSON 형식이어야 합니다."
        }), 400

    data = request.get_json()
    # 필수 필드가 있다면 유효성 검사 추가 (여기서는 선택적으로 처리)
    # 예를 들어, username, email 등 필요한 필드를 검증할 수 있음
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    user.name = data.get("name", user.name)
    user.address = data.get("address", user.address)
    user.gender = data.get("gender", user.gender)

    # 비밀번호 변경 (선택적)
    if data.get("password"):
        user.password = generate_password_hash(data.get("password"))

    try:
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "프로필이 성공적으로 업데이트되었습니다.",
            "data": {
                "username": user.username,
                "email": user.email,
                "name": user.name,
                "address": user.address,
                "gender": user.gender
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"프로필 업데이트 오류: {e}")
        return jsonify({
            "status": "error",
            "message": "프로필 업데이트 중 오류가 발생했습니다."
        }), 500
    
@main_bp.route('/api/chat', methods=['POST'])
@jwt_required()
@csrf.exempt
def api_chat():
    if not request.is_json:
        logging.error("요청이 JSON 형식이 아닙니다.")
        return jsonify({
            "error": "Bad Request",
            "message": "Request must be in JSON format"
        }), 400

    data = request.get_json()
    logging.info(f"Received JSON data: {data}")
    user_message = data.get("message") or data.get("transcript")
    logging.info(f"Received message: {user_message}")

    if not user_message:
        logging.error("No message provided")
        return jsonify({
            "error": "Bad Request",
            "message": "No message provided"
        }), 400

    try:
        # JWT 토큰에서 사용자 ID 가져오기 및 사용자 객체 조회
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "error": "Unauthorized",
                "message": "사용자를 찾을 수 없습니다."
            }), 401

        # 세션 ID 가져오기 또는 생성 (사용자 객체 기반)
        session_id = get_or_create_session_id(user)

        # 감정 분석 수행
        emotion = analyze_emotion(user_message)
        valid_emotions = ["슬픔", "기쁨", "분노", "두려움", "놀람", "혐오", "즐거움", "피곤", "불안함", "고통"]
        if emotion not in valid_emotions:
            emotion = "기타"

        # OpenAI API 호출 및 응답 생성
        bot_message, tts_url = generate_empathic_response(user_message, emotion)
        if not bot_message:
            logging.error("봇 응답 생성 실패")
            return jsonify({
                "error": "Internal Server Error",
                "message": "봇 응답 생성에 실패했습니다."
            }), 500

        # 사용자 메시지와 봇 응답을 DB에 저장
        user_msg = UserMessage(
            role='user',
            content=user_message,
            emotion=emotion,
            session_id=session_id,
            user=user
        )
        bot_msg = UserMessage(
            role='assistant',
            content=bot_message,
            emotion=None,
            session_id=session_id,
            user=user,
            tts_url=tts_url
        )
        db.session.add(user_msg)
        db.session.add(bot_msg)
        db.session.commit()

        return jsonify({
            "response": bot_message,
            "emotion": emotion,
            "message_id": bot_msg.id,
            "tts_url": tts_url if tts_url else ""
        }), 200

    except Exception as e:
        logging.error(f"Error during chat: {str(e)}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "챗봇 응답에 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
        }), 500
    
@main_bp.route('/reset', methods=['POST'])
@csrf.exempt  # CSRF 보호에서 제외
@login_required
def reset():
    try:
        session_id = get_or_create_session_id(current_user)
        #UserMessage.query.filter_by(session_id=session_id).delete()
        #db.session.commit()
        logging.info(f"Session {session_id} reset.")

        # 시간대에 따른 추천 메시지 가져오기
        recommendation = get_time_based_recommendation()
        logging.info(f"Recommendation: {recommendation}")

        return jsonify({
            "message": "Session has been reset.",
            "recommendation": recommendation
        }), 200
    except Exception as e:
        logging.error(f"Error resetting session: {e}")
        return jsonify({"error": "Internal Server Error", "message": "세션 초기화 중 오류가 발생했습니다."}), 500



@main_bp.route('/api/admin/messages', methods=['GET'])
@jwt_required()
@admin_required
def admin_messages_api():
    messages = UserMessage.query.order_by(UserMessage.timestamp.asc()).all()
    messages_data = [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "emotion": msg.emotion,
            "tts_url": msg.tts_url,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        }
        for msg in messages
    ]
    return jsonify({
        "status": "success",
        "messages": messages_data
    }), 200



@main_bp.route('/upload_audio', methods=['POST'])
@login_required
@csrf.exempt
def upload_audio():
        if 'audio' not in request.files:
            logging.error("No audio file part in the request")
            return jsonify({"error": "Bad Request", "message": "No audio file provided"}), 400

        file = request.files['audio']
        if file.filename == '':
            logging.error("No selected audio file")
            return jsonify({"error": "Bad Request", "message": "No selected audio file"}), 400
        
        ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac'}
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
            logging.error("Unsupported file type")
            return jsonify({"error": "Bad Request", "message": "Unsupported file type"}), 400
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 파일 포인터를 다시 시작

        if file_size > 10 * 1024 * 1024:  # 10MB 제한
            logging.error("File size exceeds limit")
            return jsonify({"error": "Bad Request", "message": "File size exceeds limit"}), 400
    #try:
        # 세션 ID 가져오기 또는 생성
        session_id = get_or_create_session_id(current_user)
        logging.info(f"Session ID: {session_id}")

        if not current_user.is_authenticated:
            logging.error("current_user is not authenticated.")
            return jsonify({"error": "Unauthorized", "message": "사용자가 인증되지 않았습니다."}), 401
        logging.info(f"Current User ID: {current_user.id}")

        if current_user.id is None:
            logging.error("current_user.id is None.")
            return jsonify({"error": "Unauthorized", "message": "사용자 ID가 유효하지 않습니다."}), 401

        # 음성 데이터 저장
        audio_data = file.read()
        audio_msg = AudioMessage(session_id=session_id, audio_data=audio_data, user_id=current_user.id)
        db.session.add(audio_msg)
        db.session.commit()

        # 음성 데이터 파일로 저장 (임시)
        audio_filename = f"temp_audio_{audio_msg.id}.wav"
        re_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_filename)
        with open(re_audio_path, 'wb') as f:
            f.write(audio_data)

        # Whisper 파이프라인을 사용하여 음성 → 텍스트 변환
        transcription = transcribe_audio(re_audio_path)
        audio_msg.transcript = transcription
        db.session.commit()

        # 텍스트 메시지로 변환하여 클라이언트에 반환
        logging.info(f"Transcribed text: {transcription}")

        # 사용자 메시지와 어시스턴트 응답을 DB에 저장
        user_msg = UserMessage(role='user', content=transcription, session_id=session_id,user=current_user)
        db.session.add(user_msg)
        db.session.commit()

        # 임시 파일 삭제
        os.remove(re_audio_path)

        return jsonify({
            "transcript": transcription,
 
        }), 200

    #except Exception as e:
        logging.error(f"Error uploading audio: {str(e)}")
        return jsonify({"error": "Internal Server Error", "message": "음성 파일 처리 중 오류가 발생했습니다."}), 500

@main_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')  # 후에 템플릿 생성

# 모든 사용자 목록 가져오기 (API 엔드포인트)
@main_bp.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def get_all_users():
    users = User.query.all()
    users_data = [
        {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "name": user.name,
        }
        for user in users
    ]
    return jsonify({"users": users_data}), 200

# 특정 사용자의 정보와 채팅 내역 가져오기 (API 엔드포인트)
@main_bp.route('/api/admin/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user_details(user_id):
    user = User.query.get_or_404(user_id)
    messages = UserMessage.query.filter_by(user_id=user_id).order_by(UserMessage.timestamp.asc()).all()
    messages_data = [
        {
            "id": msg.id,
            "role": msg.role,   
            "content": msg.content,
            "emotion": msg.emotion,
            "tts_url": msg.tts_url,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]
    user_data = {
        "id": user.username,
        "username": user.name,
        "is_admin": user.is_admin,
        # 필요한 다른 필드 추가
    }
    return jsonify({"user": user_data, "messages": messages_data}), 200



@main_bp.route('/api/admin/users/<int:user_id>/send-alert-email', methods=['POST'])
@login_required
@csrf.exempt
@admin_required
def send_alert_email(user_id):
    data = request.get_json()
    if not data:
        logging.error("No data provided for email alert.")
        return jsonify({"error": "Invalid request data"}), 400

    ratio = data.get("ratio")
    week_total = data.get("weekTotal")
    negative_count = data.get("negativeCount")
    if ratio is None or week_total is None or negative_count is None:
        logging.error("Missing parameters for email alert.")
        return jsonify({"error": "Missing parameters"}), 400

    # 감정 비율이 60% 미만이면 이메일 전송하지 않음
    if ratio < 0.6:
        return jsonify({"message": "감정 비율이 60% 미만입니다."}), 200

    user = User.query.get_or_404(user_id)
    user_email = user.email
    if not user_email:
        logging.error("User email not found.")
        return jsonify({"error": "User email not found"}), 400

    # 지난 7일간 부정 감정 메시지(부정 감정: 슬픔, 분노, 두려움, 불안함, 고통) 모두 조회
    negative_emotions = ["슬픔", "분노", "두려움", "불안함", "고통"]
    week_ago = datetime.now() - timedelta(days=7)
    negative_messages = (
        UserMessage.query.filter(
            UserMessage.user_id == user_id,
            UserMessage.role == "user",
            UserMessage.timestamp >= week_ago,
            UserMessage.emotion.in_(negative_emotions)
        )
        .order_by(UserMessage.timestamp.asc())
        .all()
    )

    if negative_messages:
        negative_message_details = "\n".join(
            [
                f"{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: \"{msg.content}\" (감정: {msg.emotion})"
                for msg in negative_messages
            ]
        )
    else:
        negative_message_details = "해당 없음"

    subject = "경고: 부정적인 감정 비율 알림"
    body = (
        f"안녕하세요, {user.name}님.\n\n"
        f"최근 7일간의 채팅 내역에서 부정적인 감정이 전체 메시지의 {ratio*100:.1f}%를 차지하였습니다.\n"
        f"(전체 메시지 수: {week_total}, 부정적인 메시지 수: {negative_count})\n\n"
        f"지난 7일간의 부정적인 메시지 내역:\n{negative_message_details}\n\n"
        f"{user.name}님에 대한 조치가 필요합니다."
    )

    msg = Message(subject, recipients=[user_email], body=body)
    try:
        mail.send(msg)
        logging.info(f"Alert email sent to {user_email}")
        return jsonify({"message": "경고 이메일이 전송되었습니다."}), 200
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return jsonify({"error": "Failed to send email"}), 500
    

@main_bp.route("/api/admin/reset_messages", methods=["POST"])
@login_required
def reset_messages():
    # 관리자 권한 체크
    if not current_user.is_admin:
        return jsonify({"error": "관리자 권한이 필요합니다."}), 403

    try:
        db.session.query(UserMessage).delete()  
        # 또는 db.session.execute("TRUNCATE TABLE user_messages") (외래키 주의)
        db.session.commit()
        return jsonify({"message": "All messages deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
