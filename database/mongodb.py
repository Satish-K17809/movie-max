# database/mongodb.py
# MongoDB connection for Movie Max. app.py imports "users" and "bookings" from here.
#
# Database : movie_max
# Collections (created automatically):
#   users     - registered customers
#   bookings  - confirmed ticket bookings
#   movies    - movies added by the admin (created by app.py)

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()   # reads the .env file in the project folder

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["movie_max"]

users = db["users"]
bookings = db["bookings"]

try:
    client.admin.command("ping")        # is MongoDB reachable?

    # One account per email
    users.create_index("email", unique=True)

    # A seat can be booked only ONCE for the same movie + date + show time.
    # (seats is a list, so MongoDB checks every seat inside it)
    bookings.create_index(
        [("movie_title", 1), ("show_date", 1), ("show_time", 1), ("seats", 1)],
        unique=True
    )
    bookings.create_index("booking_id", unique=True)

except PyMongoError as error:
    print("[MONGODB] Could not connect to MongoDB (or create indexes):", error)
    print("[MONGODB] Start MongoDB or fix MONGO_URI in the .env file.")
