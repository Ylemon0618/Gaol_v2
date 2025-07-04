import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
custom_playlist = db["custom_playlist"]


def insert_song(user_id: int, url: str, title: str):
    return custom_playlist.find_one_and_update({"user_id": user_id}, {"$push": {"playlist": url, "title": title}})


def delete_song(user_id: int, url: str, title: str):
    return custom_playlist.find_one_and_update({"user_id": user_id}, {"$pull": {"playlist": url, "title": title}})