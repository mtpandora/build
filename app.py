from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from models import User, Material, db
import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})  # Разрешаем запросы только с этого источника
app.config.from_object('config.Config')  # Убедитесь, что ваш файл конфигурации корректно настроен
db.init_app(app)

# Создание всех таблиц
with app.app_context():
    db.create_all()  # Создаем таблицы при запуске приложения

jwt = JWTManager(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'msg': 'Email already registered'}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    # Создаем токен сразу после регистрации
    access_token = create_access_token(identity=new_user.id, expires_delta=datetime.timedelta(hours=1))
    return jsonify({'access_token': access_token}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'msg': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=user.id, expires_delta=datetime.timedelta(hours=1))
    return jsonify({'access_token': access_token}), 200

@app.route('/materials', methods=['POST'])
@jwt_required()
def add_material():
    data = request.get_json()
    name = data.get('name')
    quantity = data.get('quantity')
    price = data.get('price')
    unit = data.get('unit')

    current_user_id = get_jwt_identity()  # Получаем ID текущего пользователя
    new_material = Material(name=name, quantity=quantity, price=price, unit=unit, user_id=current_user_id)
    db.session.add(new_material)
    db.session.commit()

    return jsonify({'msg': 'Material added successfully'}), 201

@app.route('/materials/<int:id>', methods=['PUT'])
@jwt_required()
def update_material(id):
    data = request.get_json()
    material = Material.query.filter_by(id=id, user_id=get_jwt_identity()).first_or_404()

    material.name = data.get('name', material.name)  # Добавлено обновление названия
    material.quantity = data.get('quantity', material.quantity)
    material.price = data.get('price', material.price)
    material.unit = data.get('unit', material.unit)  # Добавлено обновление единицы измерения
    db.session.commit()

    return jsonify({'msg': 'Material updated successfully'}), 200

@app.route('/materials/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_material(id):
    material = Material.query.filter_by(id=id, user_id=get_jwt_identity()).first_or_404()
    db.session.delete(material)
    db.session.commit()

    return jsonify({'msg': 'Material deleted successfully'}), 200

@app.route('/materials', methods=['GET'])
@jwt_required()
def get_materials():
    current_user_id = get_jwt_identity()
    materials = Material.query.filter_by(user_id=current_user_id).all()
    return jsonify([{
        'id': material.id,
        'name': material.name,
        'quantity': material.quantity,
        'price': material.price,
        'unit': material.unit
    } for material in materials]), 200


@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'email': user.email
    }), 200


@app.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not check_password_hash(user.password, old_password):
        return jsonify({'msg': 'Invalid old password'}), 400

    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()

    return jsonify({'msg': 'Password changed successfully'}), 200

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
