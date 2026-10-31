
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "insightminer")
    )
    return conn
def get_connection():
    return get_db_connection()