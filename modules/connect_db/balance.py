import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
balance = db["balance"]


def get_user_balance(user_id):
    user = balance.find_one({"user_id": user_id})
    if user:
        return user["balance"]
    else:
        balance.insert_one({"user_id": user_id, "balance": 0})
        return 0

def update_user_balance(user_id, amount):
    user = balance.find_one({"user_id": user_id})
    if user:
        balance.update_one({"user_id": user_id}, {"$set": {"balance": user["balance"] + amount}})
    else:
        balance.insert_one({"user_id": user_id, "balance": amount})

    return balance.find_one({"user_id": user_id})["balance"]

def set_user_balance(user_id, amount):
    user = balance.find_one({"user_id": user_id})
    if user:
        balance.update_one({"user_id": user_id}, {"$set": {"balance": amount}})
    else:
        balance.insert_one({"user_id": user_id, "balance": amount})

    return balance.find_one({"user_id": user_id})["balance"]
