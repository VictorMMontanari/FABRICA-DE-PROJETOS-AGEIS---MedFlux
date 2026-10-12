from app import create_app
from models import User, db

SEED_USERS = [
    {'name': 'Marina Santos', 'email': 'marina.santos@medflux.com', 'password': '123456', 'city': 'Marília, SP'},
]

if __name__ == '__main__':
    with create_app().app_context():
        for data in SEED_USERS:
            if User.query.filter_by(email=data['email']).first():
                print(f"já existe: {data['email']}")
                continue
            user = User(name=data['name'], email=data['email'], city=data['city'])
            user.set_password(data['password'])
            db.session.add(user)
            print(f"criado: {data['email']}")
        db.session.commit()
