
# apps/units.py
import pandas as pd
import joblib
import os
from flask import current_app
from apps.models import db, User, SurveyAnswer
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODEL_DIR = os.path.join(BASE_DIR, 'apps', 'model')   # ★ 추가

class TypeScoreCalculator(BaseEstimator, TransformerMixin):
    def __init__(self):
        self.type_questions = {
            'type1_agree': ['Q1','Q13','Q35','Q36','Q16','Q18','Q20','Q21','Q31','Q32'],
            'type1_disagree': ['Q33','Q11','Q26','Q38','Q6','Q30','Q28','Q27'],
            'type2_agree': ['Q4','Q5','Q17','Q7','Q35','Q6','Q12','Q9','Q29','Q31','Q32'],
            'type2_disagree': ['Q2','Q10','Q15','Q22','Q28','Q26'],
            'type3_agree': ['Q2','Q3','Q4','Q5','Q7','Q9','Q18','Q20','Q21','Q19','Q45','Q46','Q47','Q48'],
            'type3_disagree': ['Q25','Q38','Q26','Q24','Q6','Q28'],
            'type4_agree': ['Q5','Q7','Q8','Q9','Q12','Q14','Q29','Q31','Q32','Q48','Q49','Q50'],
            'type4_disagree': ['Q23','Q26','Q30','Q28','Q11','Q34','Q27']
        }
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        X = X.copy()
        for key, questions in self.type_questions.items():
            existing_questions = [q for q in questions if q in X.columns]
            X[key] = X[existing_questions].sum(axis=1)
        
        # 각 유형의 점수 = agree - disagree
        X['type1_score'] = X['type1_agree'] - X['type1_disagree']
        X['type2_score'] = X['type2_agree'] - X['type2_disagree']
        X['type3_score'] = X['type3_agree'] - X['type3_disagree']
        X['type4_score'] = X['type4_agree'] - X['type4_disagree']
        
        # 필요한 점수만 반환
        return X[['type1_score', 'type2_score', 'type3_score', 'type4_score']]


# 유형별 주요 Q-진술문 정의
type_questions = {
    'type1_agree': ['Q36', 'Q13', 'Q35', 'Q1', 'Q16'],
    'type1_disagree': ['Q33', 'Q11', 'Q26', 'Q38', 'Q6', 'Q30', 'Q28', 'Q27'],
    'type2_agree': ['Q4', 'Q5', 'Q17', 'Q7', 'Q35', 'Q6', 'Q12'],
    'type2_disagree': ['Q2', 'Q10', 'Q15', 'Q22', 'Q28', 'Q26'],
    'type3_agree': ['Q3', 'Q7', 'Q5', 'Q1', 'Q4', 'Q2', 'Q12', 'Q19'],
    'type3_disagree': ['Q25', 'Q38', 'Q26', 'Q24', 'Q6', 'Q28'],
    'type4_agree': ['Q7', 'Q8', 'Q13', 'Q12', 'Q14', 'Q5'],
    'type4_disagree': ['Q23', 'Q26', 'Q30', 'Q28', 'Q11', 'Q34', 'Q27']
}

# 유형별 점수 계산 함수
def calculate_type_scores_from_db(user_id, type_questions):
    answers = SurveyAnswer.query.filter_by(user_id=user_id).order_by(SurveyAnswer.question_no).all()
    if not answers:
        print("설문 답변이 없습니다.")
        return None

    # 응답 데이터를 딕셔너리로 변환
    answer_dict = {f'Q{ans.question_no}': ans.answer_value for ans in answers}

    # 유형별 점수 계산
    type_scores = {}
    for key, questions in type_questions.items():
        existing_questions = [q for q in questions if q in answer_dict]
        type_scores[key] = sum([answer_dict[q] for q in existing_questions])

    # 각 유형의 점수 = agree - disagree
    type1_score = type_scores.get('type1_agree', 0) - type_scores.get('type1_disagree', 0)
    type2_score = type_scores.get('type2_agree', 0) - type_scores.get('type2_disagree', 0)
    type3_score = type_scores.get('type3_agree', 0) - type_scores.get('type3_disagree', 0)
    type4_score = type_scores.get('type4_agree', 0) - type_scores.get('type4_disagree', 0)

    return [type1_score, type2_score, type3_score, type4_score]

# 클러스터 레이블을 문자열로 변환하는 딕셔너리
cluster_labels = {
    0: '효과지향 자기주도형',
    1: '동기중심 준비형',
    2: '정서중심 활력형',
    3: '생활기반 의무형'
}

def apply_pipeline_model(user_id):
    """
    1) 사용자 설문 응답으로부터 유형 점수 계산
    2) 파이프라인 로드 및 예측 수행
    3) 예측 결과를 User 테이블에 저장
    """
    user = User.query.get(user_id)
    if not user:
        print("사용자를 찾을 수 없습니다.")
        return

    # 사용자 설문 응답으로부터 유형 점수 계산
    type_scores = calculate_type_scores_from_db(user_id, type_questions)
    if type_scores is None:
        return

    ## 파이프라인 로드 (BASE_DIR 기준으로 경로 생성)
    pipeline_path = os.path.join(
        BASE_DIR,
        'apps', 'model',
        'kmeans_exercise_motivation_pipeline.joblib'
   )
    try:
        pipeline = joblib.load(pipeline_path)
    except Exception as e:
        print(f"파이프라인 로드 오류: {e} (path: {pipeline_path})")
        return
    
    # 데이터프레임으로 변환하여 예측에 사용
    type_scores_df = pd.DataFrame([type_scores], columns=['type1_score', 'type2_score', 'type3_score', 'type4_score'])

    # 예측 수행 (파이프라인이 전처리 포함)
    try:
        prediction = pipeline.predict(type_scores_df)  # 예측값은 숫자 (0, 1, 2, 3)
    except Exception as e:
        print(f"모델 적용 오류: {e}")
        return

    # 예측된 숫자형 클러스터를 cluster_labels 딕셔너리를 통해 문자열로 변환
    predicted_label = cluster_labels.get(prediction[0], "Unknown")  # 예측된 레이블을 텍스트로 변환

    # 예측 결과를 User 테이블에 저장
    user.type_id = predicted_label

    # 데이터베이스 커밋
    try:
        db.session.commit()
        print(f"모델 결과가 사용자 {user.username}에 저장되었습니다.")
    except Exception as e:
        print(f"데이터베이스 저장 오류: {e}")
