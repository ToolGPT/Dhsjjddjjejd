import socket
import threading
import time
import requests

# Настройки Telegram бота
BOT_TOKEN = "7410613487:AAFZyzvqcQ7Xk_Mj2Lw2Os7c7rFD7Uv8xJs"  # Замените на ваш токен
CHAT_ID = "6749237131"  # Замените на ваш ID чата

# Настройки сервера
HOST = "0.0.0.0"  # Слушаем все интерфейсы
PORT = 8080

# Список разрешенных HWID
ALLOWED_HWIDS = ["HWID1", "HWID2", "HWID3"]

# Максимальное количество одновременных соединений
MAX_CONNECTIONS = 5  # Ограничение на 5 подключений

# Время ожидания ответа
TIMEOUT = 10

# Максимальное количество запросов в секунду от одного IP
MAX_REQUESTS_PER_SECOND = 10

# Словарь для отслеживания количества запросов от каждого IP
request_counts = {}

# Функция проверки HWID
def check_hwid(hwid):
  return hwid in ALLOWED_HWIDS

# Функция отправки сообщения в Telegram
def send_telegram_message(message):
  try:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    response.raise_for_status()  # Проверка статуса ответа
  except requests.exceptions.RequestException as e:
    print(f"Ошибка отправки сообщения в Telegram: {e}")
  except Exception as e:
    print(f"Ошибка при отправке сообщения: {e}")

# Функция обработки запросов
def handle_client(client_socket, address):
  try:
    # Получение данных от клиента
    data = client_socket.recv(1024).decode("utf-8")

    # Разбор данных
    login, password, hwid = data.split("|")

    # Проверка HWID
    if not check_hwid(hwid):
      client_socket.send("Invalid HWID".encode("utf-8"))
      return

    # Проверка логина и пароля (упрощенная)
    if login != "admin" or password != "password":
      client_socket.send("Invalid credentials".encode("utf-8"))
      return

    # Получение внешнего IP адреса
    try:
      external_ip = requests.get('https://api.ipify.org').text
    except requests.exceptions.RequestException as e:
      external_ip = "Не удалось получить IP"

    # Отправка IP в Telegram
    message = f"Новый запрос от {address[0]} с HWID: {hwid}\nIP дедика: {external_ip}"
    send_telegram_message(message)

    # Отправка ответа клиенту
    client_socket.send("OK".encode("utf-8"))
  except Exception as e:
    print(f"Ошибка обработки запроса: {e}")
  finally:
    client_socket.close()

# Функция для ограничения количества запросов от одного IP
def limit_requests(address):
  ip = address[0]
  if ip in request_counts:
    request_counts[ip] += 1
  else:
    request_counts[ip] = 1
  
  # Проверка ограничения
  if request_counts[ip] > MAX_REQUESTS_PER_SECOND:
    print(f"Слишком много запросов от {ip}. Блокировка.")
    return False
  return True

# Создание сокета
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
  server_socket.bind((HOST, PORT))
  server_socket.listen(MAX_CONNECTIONS)
  print(f"Сервер запущен на {HOST}:{PORT}")
  send_telegram_message(f"Сервер запущен на {HOST}:{PORT}")

  # Прием подключений
  while True:
    client_socket, address = server_socket.accept()
    print(f"Подключение от {address}")

    # Ограничение количества запросов
    if not limit_requests(address):
      client_socket.close()  # Закрытие соединения
      continue

    # Создание нового потока для обработки запроса
    thread = threading.Thread(target=handle_client, args=(client_socket, address))
    thread.start()

    # Очистка словаря request_counts каждую секунду
    time.sleep(1)
    request_counts.clear()