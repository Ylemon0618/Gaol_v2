import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
msg = db["messages"]

def save_message(content: str, author: int, channel: int, message: int, guild: int, timestamp: str):
    message_data = {
        "content": content,
        "author": author,
        "channel": channel,
        "message_id": message,
        "guild_id": guild,
        "timestamp": timestamp
    }
    msg.insert_one(message_data)
