import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Selvaraj@1981",
        database="medical_system"
    )
    return connection


try:
    connection = get_connection()
    print("Database connected successfully!")
    connection.close()
except Exception as e:
    print("Database connection failed:", e)
