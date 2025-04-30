# apps/app.py
import os
import csv
import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

from apps.models import db, Type
from apps.views import main_bp, login_manager, csrf, mail
from apps.config import Config
from apps.utils import load_questions_from_csv, load_welfare_and_program_data

def register_cli_commands(app):
    @app.cli.command("seed-types")
    @with_appcontext
    def seed_types():
        """CSV에 등장하는 모든 타입을 먼저 DB에 넣습니다."""
        # 프로젝트 루트 계산
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # CSV 파일 경로
        csv_path = os.path.join(project_root, 'apps', 'model', '질문 최종.csv')
        # 읽어서 unique한 타입 뽑기
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            unique_types = {row['type'] for row in reader}

        # DB에 삽입
        created = 0
        for tname in unique_types:
            if not Type.query.filter_by(name=tname).first():
                db.session.add(Type(name=tname))
                created += 1
        db.session.commit()
        click.echo(f"Seeded {created} types.")

    @app.cli.command("seed-questions")
    @with_appcontext
    def seed_questions():
        """타입이 이미 들어간 뒤에 질문을 CSV에서 읽어 DB에 채웁니다."""
        load_questions_from_csv(current_app)
        click.echo("Questions seeded.")

def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    app.config.from_object(Config)

    # JWT 초기화
    JWTManager(app)

    # 확장 초기화
    login_manager.init_app(app)
    csrf.init_app(app)
    db.init_app(app)
    mail.init_app(app)
    Migrate(app, db)

    # Blueprint 등록
    app.register_blueprint(main_bp)

    # CLI 커맨드 등록
    register_cli_commands(app)

    return app

