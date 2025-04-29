# flask_app/models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json, logging
db = SQLAlchemy()
class Type(db.Model):
    __tablename__ = 'types'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    
    users = db.relationship('User', back_populates='type', lazy=True)
    questions = db.relationship('Question', back_populates='type', lazy=True)
    activities = db.relationship('Activity', back_populates='type', lazy=True)
# 회원정보 테이블
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 고유 넘버
    username = db.Column(db.String(50), unique=True, nullable=False)  # 아이디
    password = db.Column(db.String(100), nullable=False)              # 비번
    name = db.Column(db.String(50), nullable=False)                   # 이름
    email = db.Column(db.String(120), unique=True, nullable=False)    # 이메일
    address = db.Column(db.String(200))                               # 주소
    gender = db.Column(db.String(10))                                 # 성별
    is_admin = db.Column(db.Boolean, default=False)
    signup_date = db.Column(db.Date, nullable=False, default=datetime.now)  # 자동 등록
    session_id = db.Column(db.String(100), nullable=True)
    # 난이도 관리
    current_stage = db.Column(db.String(10), nullable=False, default='쉬움')  # 초기 난이도 '하'
    last_stage_update = db.Column(db.Date, nullable=False, default=datetime.now)  # 난이도 마지막 업데이트 날짜

    #type_id = db.Column(db.String, db.ForeignKey('types.name'), nullable=True)
    type_id = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=True)
    # 관계 설정
    type = db.relationship('Type', back_populates='users', lazy=True)
    survey_answers = db.relationship('SurveyAnswer', back_populates='user', lazy=True)
    activities = db.relationship('UserActivity', back_populates='user', lazy=True)
    questions = db.relationship('UserQuestion', back_populates='user', lazy=True)
    audio_messages = db.relationship('AudioMessage', back_populates='user', lazy=True)
    messages = db.relationship('UserMessage', back_populates='user', lazy=True)

class WelfareCenter(db.Model):
    __tablename__ = 'welfare_center'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)  # 기관명
    addressC = db.Column(db.String(120), nullable=False)  # 주소
    phone_number = db.Column(db.String(20), nullable=True)  # 전화번호
    operator = db.Column(db.String(80), nullable=True)  # 운영주체
    corporation_type = db.Column(db.String(50), nullable=True)  # 법인유형
    latitude = db.Column(db.Float, nullable=True)  # 위도
    longitude = db.Column(db.Float, nullable=True)  # 경도

class Program(db.Model):
    __tablename__ = 'programs'  # 테이블명을 복수형으로 변경
    id = db.Column(db.Integer, primary_key=True)
    welfare_center_id = db.Column(db.Integer, db.ForeignKey('welfare_center.id'), nullable=False)
    location = db.Column(db.String(80), nullable=False)  # 운영장소 (복지관 이름과 연결)
    name = db.Column(db.String(80), nullable=False)  # 프로그램 이름
    target = db.Column(db.String(255), nullable=True)  # 대상
    schedule = db.Column(db.String(255), nullable=True)  # 일시
    content = db.Column(db.Text, nullable=True)  # 내용

    # WelfareCenter와 연계하여 복지관이 지워지면 해당 프로그램도 같이 삭제
    welfare_center = db.relationship(
        'WelfareCenter',
        backref=db.backref('programs', lazy=True, cascade='all, delete-orphan')
    )
# 설문조사 답변 테이블
class SurveyAnswer(db.Model):
    __tablename__ = 'survey_answers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 고유 넘버
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_no = db.Column(db.Integer, nullable=False)  # 질문 번호 (1부터 시작)
    answer_value = db.Column(db.Integer, nullable=False)  # 답변 값 (-3 ~ 3)
    date_submitted = db.Column(db.DateTime, nullable=False, default=datetime.now) 
    user = db.relationship('User', back_populates='survey_answers', lazy=True)

# 활동 테이블
class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(10), nullable=False)  # 하, 중, 상
    type_id = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=False)  # 사용자 유형과 연관

    type = db.relationship('Type', back_populates='activities', lazy=True)
    user_activities = db.relationship('UserActivity', back_populates='activity', lazy=True)

# 사용자 활동 상태 테이블
class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=True)
    user_question_id = db.Column(db.Integer, db.ForeignKey('user_questions.id'), nullable=True)
    activity_type = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(10),  default='미완료')  # 완료, 미완료
    date_recommended = db.Column(db.Date, nullable=False, default=datetime.now)
    miss_count = db.Column(db.Integer, nullable=False, default=0)  # 미완료 횟수

    user = db.relationship('User', back_populates='activities', lazy=True)
    activity = db.relationship('Activity', back_populates='user_activities', lazy=True)
    question = db.relationship('Question', back_populates='user_activities', lazy=True)
    user_question = db.relationship('UserQuestion', back_populates='user_activities', lazy=True)
# 질문 테이블
class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)  # 질문 내용
    difficulty = db.Column(db.String(10), nullable=False)  # 하, 중, 상
    type_id = db.Column(db.Integer, db.ForeignKey('types.id'), nullable=False)  # 질문 유형

    type = db.relationship('Type', back_populates='questions', lazy=True)
    user_questions = db.relationship('UserQuestion', back_populates='question', lazy=True)
    user_activities = db.relationship('UserActivity', back_populates='question', lazy=True)

# 사용자 질문 상태 테이블
class UserQuestion(db.Model):
    __tablename__ = 'user_questions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)

    user = db.relationship('User', back_populates='questions', lazy=True)
    question = db.relationship('Question', back_populates='user_questions', lazy=True)
    user_activities = db.relationship('UserActivity', back_populates='user_question', lazy=True)

# user_messages 테이블
class UserMessage(db.Model):
    __tablename__ = 'user_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' 또는 'bot'
    content = db.Column(db.Text, nullable=False)
    emotion = db.Column(db.String(50), nullable=True)  # 감정 저장 필드 추가
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tts_url = db.Column(db.String(255), nullable=True)  # TTS URL 추가

    user = db.relationship('User', back_populates='messages', lazy=True)
    def set_tts_urls(self, urls):
        try:
            self.tts_url = json.dumps(urls)
        except (TypeError, ValueError) as e:
            logging.error(f"Invalid JSON data: {e}")
            self.tts_url = json.dumps([])

    def get_tts_urls(self):
        try:
            return json.loads(self.tts_url) if self.tts_url else []
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return []
# audio_messages 테이블
class AudioMessage(db.Model):
    __tablename__ = 'audio_messages'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    audio_data = db.Column(db.LargeBinary, nullable=False)  # 음성 데이터 저장
    transcript = db.Column(db.Text, nullable=True)         # 음성 인식 결과
    emotion = db.Column(db.String(50), nullable=True)      # 감정 저장
    timestamp = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', back_populates='audio_messages', lazy=True)