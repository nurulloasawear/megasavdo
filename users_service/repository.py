from db import UserDatabase

db = UserDatabase()

def create_user(data: dict):
    return db.create_user(
        username=data['username'],
        name=data['name'],
        email=data['email'],
        phone_number=data['phone_number'],
        password=data['password'],
        role=data.get('role', 'customer')
    )

def get_user(user_id: int):
    return db.get_user_by_id(user_id)

def get_user_by_email(email: str):
    return db.get_user_by_email(email)

def get_users():
    return db.get_all_users()

def add_to_wishlist(user_id: int, product_id: int):
    db.add_user_activity(user_id, product_id, 'wishlist_add')
    db.log_action(user_id, 'wishlist_add', 'products', product_id)

def get_wishlist(user_id: int):
    return db.get_wishlist(user_id)

def add_points(user_id: int, points: int):
    db.add_points(user_id, points)
    db.log_action(user_id, 'add_points', 'loyalty', user_id, f"+{points} ball")