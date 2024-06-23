import socket
import threading
import time
import requests
from functools import wraps
import sqlite3

BOT_TOKEN = "7410613487:AAFZyzvqcQ7Xk_Mj2Lw2Os7c7rFD7Uv8xJs"
CHAT_ID = "6749237131"
HOST = "0.0.0.0"
PORT = 8080
MAX_CONNECTIONS = 5
TIMEOUT = 10
DATABASE_NAME = "hwid_database.db"  
  

def create_database():

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hwid_data (
        key TEXT PRIMARY KEY,
        hwid TEXT DEFAULT '0'
    )
""")
    conn.commit()
    conn.close()

def get_hwid(key):

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hwid FROM hwid_data WHERE key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None



def add_hwid(key, hwid):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE hwid_data SET hwid = ? WHERE key = ?", (hwid, key))
    conn.commit()
    conn.close()


def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")


def handle_client(client_socket, address):
    try:
        data = client_socket.recv(1024).decode("utf-8")
        key, hwid = data.split("|")
        try:
            external_ip = requests.get('https://api.ipify.org').text
        except requests.exceptions.RequestException as e:
            external_ip = "Failed to get IP"


        db_hwid = get_hwid(key)

        if db_hwid == 0: 
            add_hwid(key, hwid)
            send_telegram_message(f"New key registered: {key} with HWID: {hwid}")


        elif db_hwid == hwid: 
            client_socket.send("True".encode("utf-8"))

        else: 
            return

    except Exception as e:
        print(f"Error handling request: {e}")
    finally:
        client_socket.close()


create_database()  
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen(MAX_CONNECTIONS)
    print(f"Server started on {HOST}:{PORT}")
    send_telegram_message(f"Server started on {HOST}:{PORT}")

    while True:
        client_socket, address = server_socket.accept()
        print(f"Connection from {address}")

        thread = threading.Thread(target=handle_client, args=(client_socket, address))
        thread.start()

        time.sleep(1)
        
