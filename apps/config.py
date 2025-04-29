import os, openai
from dotenv import load_dotenv
from datetime import timedelta

# ─── 프로젝트 루트 한 번만 계산 ─────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ─── .env 로드 ─────────────────────────────────────────────────────
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY                  = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI     = 'sqlite:///' + os.path.join(BASE_DIR, os.getenv('DATABASE_URL'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY              = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(hours=1)

    DEBUG                       = True
    openai_api_key              = os.getenv("OPENAI_API_KEY")
    UPLOAD_FOLDER               = os.path.join(BASE_DIR, os.getenv('UPLOAD_FOLDER'))
    MAX_CONTENT_LENGTH          = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    SUPERTONE_API_KEY           = os.getenv('SUPERTONE_API_KEY')
    MAIL_SERVER                 = os.getenv('MAIL_SERVER')
    MAIL_PORT                   = os.getenv('MAIL_PORT')
    MAIL_USE_TLS                = os.getenv('MAIL_USE_TLS')
    MAIL_USERNAME               = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD               = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER         = os.getenv('MAIL_DEFAULT_SENDER')
    GOOGLE_MAPS_API_KEY         = os.getenv('GOOGLE_MAPS_API_KEY')
