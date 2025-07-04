import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
custom_playlist = db["balance"]


def get_user_balance(user_id):
    user = custom_playlist.find_one({"user_id": user_id})
    if user:
        return user["balance"]
    else:
        custom_playlist.insert_one({"user_id": user_id, "balance": 0})
        return 0

def update_user_balance(user_id, amount):
    user = custom_playlist.find_one({"user_id": user_id})
    if user:
        custom_playlist.update_one({"user_id": user_id}, {"$set": {"balance": user["balance"] + amount}})
    else:
        custom_playlist.insert_one({"user_id": user_id, "balance": amount})

    return custom_playlist.find_one({"user_id": user_id})["balance"]

def set_user_balance(user_id, amount):
    user = custom_playlist.find_one({"user_id": user_id})
    if user:
        custom_playlist.update_one({"user_id": user_id}, {"$set": {"balance": amount}})
    else:
        custom_playlist.insert_one({"user_id": user_id, "balance": amount})

    return custom_playlist.find_one({"user_id": user_id})["balance"]
