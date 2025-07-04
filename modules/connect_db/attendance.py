import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient

load_dotenv()

client = MongoClient(os.environ.get('MONGO_URI'))

db = client["gaol"]
attendance = db["attendance"]


def get_attendance(user_id: int):
    user = attendance.find_one({"user_id": user_id})
    if user:
        return {"user_id": user["user_id"], "date": datetime.strptime(user["date"], "%Y-%m-%d"), "streak": user["streak"]}
    else:
        return None

def update_attendance(user_id: int):
    user = get_attendance(user_id)

    if user:
        if user["date"].date() == datetime.now().date():
            return {"error": "Already checked in today.\n이미 출석 체크를 했습니다."}
        elif user["date"].date() == (datetime.now() - timedelta(days=1)).date():
            new_streak = user["streak"] + 1
            attendance.update_one({"user_id": user_id}, {"$set": {"date": datetime.now().strftime("%Y-%m-%d"), "streak": new_streak}})
            return {"user_id": user_id, "date": datetime.now(), "streak": new_streak}
        else:
            attendance.update_one({"user_id": user_id}, {"$set": {"date": datetime.now().strftime("%Y-%m-%d"), "streak": 1}})
    else:
        attendance.insert_one({"user_id": user_id, "date": datetime.now().strftime("%Y-%m-%d"), "streak": 1})

    return {"user_id": user_id, "date": datetime.now(), "streak": 1}
