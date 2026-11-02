
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "insightminer")
    }

    # Enable SSL for the Aiven cloud database
    if os.getenv("DB_SSL_REQUIRED", "false").lower() == "true":
        config["ssl_disabled"] = False

        ssl_ca = os.getenv("DB_SSL_CA")
        if ssl_ca:
            config["ssl_ca"] = ssl_ca
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

    conn = mysql.connector.connect(**config)
    return conn


def get_connection():
    return get_db_connection()
