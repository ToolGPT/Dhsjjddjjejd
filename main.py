 import socket
import threading
import time
import requests
import sqlite3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# Замените эти ключи на свои собственные
ENCRYPTION_KEY = b'9205689291bbc93d6daedcc328c605ea3721352f214982acb1c41ce50af11477'  # Ваш секретный ключ шифрования
BOT_TOKEN = "7410613487:AAFZyzvqcQ7Xk_Mj2Lw2Os7c7rFD7Uv8xJs"
CHAT_ID = 6749237131
HOST = "0.0.0.0"
PORT = 8080
MAX_CONNECTIONS = 5
TIMEOUT = 10
DATABASE_NAME = "hwid_database.db"

# Создаем базу данных, если ее нет
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

# Получаем HWID по ключу из базы данных
def get_hwid(key):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hwid FROM hwid_data WHERE key=?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Добавляем или обновляем HWID в базе данных
def add_hwid(key, hwid):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO hwid_data (key, hwid) VALUES (?, ?)", (key, hwid))
    conn.commit()
    conn.close()

# Отправляем сообщение в Telegram
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")

# Шифруем данные AES
def encrypt_data(data, key):
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return iv + ct

# Дешифруем данные AES
def decrypt_data(data, key):
    data = base64.b64decode(data)
    iv = data[:AES.block_size]
    ct = data[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')

# Обрабатываем запрос от клиента
def handle_client(client_socket, address):
    try:
        data = client_socket.recv(1024)
        decrypted_data = decrypt_data(data, ENCRYPTION_KEY)
        key, hwid = decrypted_data.split("|")

        try:
            external_ip = requests.get('https://api.ipify.org').text
        except requests.exceptions.RequestException as e:
            external_ip = "Failed to get IP"

        db_hwid = get_hwid(key)

        if db_hwid == '0':
            add_hwid(key, hwid)
            send_telegram_message(f"New key registered: {key} with HWID: {hwid}")
            client_socket.send("True".encode("utf-8"))
        elif db_hwid == hwid:
            client_socket.send("True".encode("utf-8"))
        else:
            return

    except Exception as e:
        print(f"Error handling request: {e}")
    finally:
        client_socket.close()

# Запускаем сервер
if name == "main":
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
