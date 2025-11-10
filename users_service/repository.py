from db import Database 

db = Database()

def create_user(data:dict):
    return db.add_user(
        username=data['username'],
        name=data['name'],
        role=data.get('role', 'user'),
        phone_number=data['phone_number'],
        password=data['password'],
        email=data['email']
    )
def get_user(user_id:int):
    return db.get_user_by_id(user_id)

def get_users():
    return db.get_all_users()

def get_user_by_email(email:str):
    return db.get_user_by_email(email)