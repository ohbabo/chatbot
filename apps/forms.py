# flask_app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from apps.models import User

class SignupForm(FlaskForm):
    username = StringField('사용자 이름', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('비밀번호', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('비밀번호 확인', validators=[DataRequired(), EqualTo('password')])
    name = StringField('이름', validators=[DataRequired()])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    address = StringField('주소')
    gender = SelectField('성별', choices=[('남성', '남성'), ('여성', '여성'), ('기타', '기타')], validators=[DataRequired()])
    submit = SubmitField('회원가입')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('이미 존재하는 사용자 이름입니다.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('이미 존재하는 이메일입니다.')

class LoginForm(FlaskForm):
    username = StringField('사용자 이름', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    submit = SubmitField('로그인')

class EditProfileForm(FlaskForm):
    username = StringField('사용자 이름', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    name = StringField('이름', validators=[DataRequired()])
    address = StringField('주소')
    gender = SelectField('성별', choices=[('남성', '남성'), ('여성', '여성'), ('기타', '기타')], validators=[DataRequired()])
    password = PasswordField('새 비밀번호', validators=[Length(min=6)])
    confirm_password = PasswordField('비밀번호 확인', validators=[EqualTo('password')])
    submit = SubmitField('프로필 업데이트')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('이미 존재하는 사용자 이름입니다.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('이미 존재하는 이메일입니다.')

class UpdateStatusForm(FlaskForm):
    status = SelectField('상태', choices=[('완료', '완료'), ('미완료', '미완료')], validators=[DataRequired()])
    submit = SubmitField('업데이트')

class EditActivitiesForm(FlaskForm):
    submit = SubmitField('활동 상태 업데이트')

class SurveyForm(FlaskForm):
    answer_value = RadioField('답변을 선택하세요', choices=[
        ('-3', '-3'),
        ('-2', '-2'),
        ('-1', '-1'),
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3')
    ], validators=[DataRequired(message="답변을 선택해주세요.")])
    
    submit = SubmitField('다음')
