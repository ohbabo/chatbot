from apps.models import Question, UserQuestion, Type, Activity, UserActivity, db, WelfareCenter, Program
from flask import flash, current_app
import random, logging, os
from datetime import datetime
import pandas as pd
from .GPS_mapping import get_lat_lng_from_address

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  경로 설정 ― 프로젝트 루트/모델 폴더를 한 번만 정의
# ──────────────────────────────────────────────────────────────
THIS_FILE    = os.path.abspath(__file__)
FLASK_APPDIR = os.path.dirname(THIS_FILE)                # …/flask_app
PROJECT_ROOT = os.path.abspath(os.path.join(FLASK_APPDIR, '..'))
MODEL_DIR    = os.path.join(PROJECT_ROOT, 'apps', 'model')
# ──────────────────────────────────────────────────────────────


def recommend_question(user):
    """
    사용자 유형을 기반으로 추천 질문을 반환합니다.
    """
    questions_csv = os.path.join(MODEL_DIR, 'qusetions.csv')
    current_app.logger.info(f"[recommend_question] csv = {questions_csv}")

    try:
        df = pd.read_csv(questions_csv, encoding='utf-8')
    except FileNotFoundError:
        current_app.logger.error(f"질문 CSV 없음: {questions_csv}")
        flash('질문 파일을 찾을 수 없습니다.')
        return None

    if not user.type_id:
        flash('사용자 유형이 설정되지 않았습니다. 설문을 완료해주세요.')
        return None

    difficulty_map = {'Type1':'쉬움','Type2':'쉬움','Type3':'쉬움','Type4':'쉬움'}
    sel_diff = difficulty_map.get(user.type_id, '쉬움')

    done_ids = [uq.question_id for uq in UserQuestion.query.filter_by(user_id=user.id)]
    avail = df[(df['difficulty']==sel_diff) & (~df['id'].isin(done_ids))]

    if avail.empty:
        flash('더 이상 추천할 질문이 없습니다.')
        return None

    return avail.sample(1).iloc[0].to_dict()


def recommend_activities(user, num_recommendations=3):
    """
    사용자 난이도에 맞는 활동을 추천합니다.
    """
    current_app.logger.info(f"[recommend_activities] User={user.id}, Stage={user.current_stage}")

    available = Activity.query.filter_by(difficulty=user.current_stage).all()
    done_ids = [ua.activity_id for ua in UserActivity.query.filter_by(user_id=user.id)]
    avail = [a for a in available if a.id not in done_ids]

    if not avail:
        flash('더 이상 추천할 활동이 없습니다.')
        return []

    return random.sample(avail, min(num_recommendations, len(avail)))


def recommend_activities_and_save(user, num_recommendations=3):
    """
    추천 활동을 DB에 저장합니다.
    """
    if not user.type_id:
        current_app.logger.warning(f"사용자 유형 미설정: {user.id}")
        return []

    avail = Activity.query.filter_by(difficulty=user.current_stage, type_id=user.type_id).all()
    done_ids = [ua.activity_id for ua in UserActivity.query.filter_by(user_id=user.id)]
    avail = [a for a in avail if a.id not in done_ids]

    if not avail:
        flash('더 이상 추천할 활동이 없습니다.')
        return []

    picks = random.sample(avail, min(num_recommendations, len(avail)))
    for act in picks:
        db.session.add(UserActivity(
            user_id=user.id,
            activity_id=act.id,
            status='미완료',
            date_recommended=datetime.now().date(),
            miss_count=0
        ))
    db.session.commit()
    return picks


def recommend_question_and_save(user):
    """
    질문 추천 후 해당 Activity / UserActivity 생성
    """
    rec = recommend_question(user)
    if not rec:
        return None

    q_obj = Question.query.get(rec['id'])
    if not q_obj:
        return None

    act = Activity(text=q_obj.text, difficulty=q_obj.difficulty, question_id=q_obj.id)
    db.session.add(act)
    db.session.flush()

    db.session.add(UserActivity(user_id=user.id, activity_id=act.id, status='미완료', miss_count=0))
    db.session.commit()
    return act


def load_questions_from_csv(app):
    """
    CSV → Question 테이블 일괄 로드
    """
    with app.app_context():
        csv_path = os.path.join(MODEL_DIR, '질문 최종.csv')
        current_app.logger.info(f"[load_questions] csv = {csv_path}")

        try:
            df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
        except FileNotFoundError:
            logging.error(f"질문 CSV 없음: {csv_path}")
            return
        except Exception as e:
            logging.error(f"질문 CSV 읽기 오류: {e}")
            return

        required = {'text', 'difficulty', 'type'}
        missing = required - set(df.columns)
        if missing:
            logging.error(f"질문 CSV 컬럼 누락: {missing}")
            return

        for index, row in df.iterrows():
            try:
                type_obj = Type.query.filter_by(name=row['type']).first()
                if not type_obj:
                    logging.error(f"타입 미존재: {row['type']}")
                    continue

                if Question.query.filter_by(text=row['text']).first():
                    continue

                db.session.add(Question(text=row['text'], difficulty=row['difficulty'], type=type_obj))
            except KeyError as e:
                logging.error(f"행 {index} 누락된 데이터: {e}")
            except Exception as e:
                logging.error(f"행 {index} 오류: {e}")

        try:
            db.session.commit()
            logging.info("질문 로드 완료")
        except Exception as e:
            db.session.rollback()
            logging.error(f"질문 커밋 오류: {e}")


def load_welfare_and_program_data(app):
    """
    복지관 & 프로그램 CSV → DB
    """
    with app.app_context():
        Program.query.delete()
        WelfareCenter.query.delete()
        db.session.commit()

        welfare_csv = os.path.join(MODEL_DIR, 'WelfareCenterlist.csv')
        current_app.logger.info(f"[load_welfare] csv = {welfare_csv}")
        if os.path.exists(welfare_csv):
            wf = pd.read_csv(welfare_csv, encoding='utf-8')
            for _, r in wf.iterrows():
                lat, lng = get_lat_lng_from_address(r['주소'])
                if not WelfareCenter.query.filter_by(name=r['기관명'], addressC=r['주소']).first():
                    db.session.add(WelfareCenter(
                        name=r['기관명'], addressC=r['주소'], phone_number=r.get('전화번호'),
                        operator=r.get('운영주체'), corporation_type=r.get('법인유형'),
                        latitude=lat, longitude=lng
                    ))
            db.session.commit()
        else:
            logging.error(f"복지관 CSV 없음: {welfare_csv}")

        program_csv = os.path.join(MODEL_DIR, 'Welprogram.csv')
        current_app.logger.info(f"[load_program] csv = {program_csv}")
        if os.path.exists(program_csv):
            pf = pd.read_csv(program_csv, encoding='utf-8').fillna("정보 없음")
            for _, r in pf.iterrows():
                wc = WelfareCenter.query.filter(WelfareCenter.name.like(f"%{r['운영장소']}% ")).first()
                if wc and not Program.query.filter_by(
                    welfare_center_id=wc.id, location=r['운영장소'],
                    name=r['운영 프로그램'], schedule=r['일시'], content=r['내용']
                ).first():
                    db.session.add(Program(
                        welfare_center_id=wc.id, location=r['운영장소'], name=r['운영 프로그램'],
                        target=r['대상'], schedule=r['일시'], content=r['내용']
                    ))
            db.session.commit()
        else:
            logging.error(f"프로그램 CSV 없음: {program_csv}")
