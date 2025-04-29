# apps/add_types.py

from apps.models import db, Type


def add_types():

        # 사용자 유형 정의
        types = [
            Type(name='효과지향 자기주도형', description='명확한 목표를 설정하고 독립적으로 성과를 추구하는 유형.'),
            Type(name='동기중심 준비형', description='내적 동기를 바탕으로 철저히 준비하며 변화에 유연하게 대응하는 유형.'),
            Type(name='정서중심 활력형', description='감정에 민감하고 활력이 넘쳐 대인 관계와 창의성을 중시하는 유형.'),
            Type(name='생활기반 의무형', description='강한 책임감과 실용성을 바탕으로 안정적이고 체계적으로 행동하는 유형.'),
        ]
        
        # 기존 유형 확인 후 추가
        for type_obj in types:
            existing_type = Type.query.filter_by(name=type_obj.name).first()
            if not existing_type:
                db.session.add(type_obj)
        
        db.session.commit()
        print("Type 데이터가 성공적으로 추가되었습니다.")


