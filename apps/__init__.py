# apps/__init__.py

# 이 파일은 팩토리 패턴을 깨지 않도록, 모델만 import해둡니다.
from .models import db, User, SurveyAnswer
