# apps/app.py
from flask import Flask
from apps.models import db 
from apps.views import main_bp, login_manager, csrf, mail
from flask_jwt_extended import JWTManager
from apps.config import Config
from apps.utils import load_questions_from_csv,load_welfare_and_program_data
from flask_migrate import Migrate






def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    app.config.from_object(Config)

    jwt = JWTManager(app)

    # DB 초기화
    login_manager.init_app(app)
    csrf.init_app(app)
    db.init_app(app)
    mail.init_app(app)
    Migrate(app, db)
    
    if Config.openai_api_key:
        print("OpenAI API 키가 성공적으로 로드되었습니다.")
    else:
        print("OpenAI API 키가 로드되지 않았습니다.")
    if Config.SUPERTONE_API_KEY:
        print("슈퍼톤 API 키가 성공적으로 로드되었습니다.")
    else:
        print("슈퍼톤 API 키가 로드되지 않았습니다.")

    # Blueprint 등록
    app.register_blueprint(main_bp)

    # DB 생성 (테이블이 없는 경우에만)
    with app.app_context():
        #db.drop_all()
        db.create_all()
        #add_types()
        load_questions_from_csv(app) # 
        #load_welfare_and_program_data(app)

    return app


    