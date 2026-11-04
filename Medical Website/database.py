import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT

def get_connection():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )

    return connection
