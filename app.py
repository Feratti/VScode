from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import requests
import hashlib
import hmac
import base64
import time
import json
import re
from datetime import datetime
from slugify import slugify

app = Flask(__name__)

# Папка для сохранения фотографий
UPLOAD_FOLDER = '/Users/vadimkuzin/Documents/VScode/static/images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Маршрут для отдачи статических файлов (фотографий)
@app.route('/static/images/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404

# Конфигурация API
endpoint = 'https://172.18.59.69'
app_key = '21225955'
access_token = 'Q4hUC71yQfqNI141LOoS'
url_events = '/artemis/api/acs/v1/door/events'
url_person = '/artemis/api/resource/v1/person/advance/personList'
url_picture_data = '/artemis/api/resource/v1/person/picture_data'
url_door_list = '/artemis/api/resource/v1/acsDoor/acsDoorList'

def generate_signature(url, payload):
    timestamp = str(int(time.time()))
    body = json.dumps(payload)
    string_to_sign = f'POST\napplication/json\napplication/json;charset=UTF-8\n{url}'
    signature = base64.b64encode(hmac.new(access_token.encode(), string_to_sign.encode(), hashlib.sha256).digest()).decode()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json;charset=UTF-8',
        'X-Ca-Key': app_key,
        'X-Ca-Signature': signature,
        'X-Ca-Timestamp': timestamp
    }
    return headers

def clean_base64(base64_string):
    if base64_string.startswith("data:image/jpeg;base64,"):
        base64_string = base64_string[len("data:image/jpeg;base64,"):]  
    return re.sub(r"[^a-zA-Z0-9+/=]", "", base64_string)    

def format_event_time(iso_time):
    try:
        dt = datetime.strptime(iso_time[:19], "%Y-%m-%dT%H:%M:%S")  # Убираем смещение `+04:00`
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return "Invalid date"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-events', methods=['POST'])
def get_events():
    data = request.json
    event_name = data.get('eventName')
    start_time_str = data.get('startTime')
    end_time_str = data.get('endTime')

    # Преобразование даты
    def format_datetime(user_input):
        try:
            dt = datetime.strptime(user_input, "%d/%m/%Y %H:%M")
            return dt.strftime("%Y-%m-%dT%H:%M:%S+04:00"), dt
        except ValueError:
            return None, None

    start_time_iso, start_time_dt = format_datetime(start_time_str)
    end_time_iso, _ = format_datetime(end_time_str)

    if not start_time_iso or not end_time_iso:
        return jsonify({'error': 'Invalid date format'}), 400

    # Получаем список дверей
    door_payload = {"pageNo": 1, "pageSize": 100}
    headers_doors = generate_signature(url_door_list, door_payload)
    response_doors = requests.post(f'{endpoint}{url_door_list}', headers=headers_doors, json=door_payload, verify=False)

    door_index_codes = []
    if response_doors.status_code == 200:
        door_data = response_doors.json()
        door_index_codes = [door["doorIndexCode"] for door in door_data.get("data", {}).get("list", [])]
        if not door_index_codes:
            return jsonify({'error': 'Door list is empty'}), 400
    else:
        return jsonify({'error': 'Failed to fetch door list'}), 400

    # Словарь для соответствия названий событий и их кодов
    event_mapping = {
        "face": 196893,
        "card": 196894,
    }

    eventCode = event_mapping.get(event_name)
    if eventCode is None:
        return jsonify({'error': 'Unknown event name'}), 400

    # Конфигурация запроса
    command_payload = {
        "startTime": start_time_iso,
        "endTime": end_time_iso,
        "eventType": eventCode,
        "personName": "",
        "doorIndexCodes": door_index_codes,
        "pageNo": 1,
        "pageSize": 500
    }

    # Запрос событий
    headers_events = generate_signature(url_events, command_payload)
    response_events = requests.post(f'{endpoint}{url_events}', headers=headers_events, json=command_payload, verify=False)

    if response_events.status_code == 200:
        event_data = response_events.json()
        results = []
        for entry in event_data['data']['list']:
            if entry.get('eventType') != eventCode:
                continue

            name = entry['personName']
            person_payload = {
                "pageNo": 1,
                "pageSize": 10,
                "personName": name,
                "cardNo": ""
            }

            headers_person = generate_signature(url_person, person_payload)
            response_person = requests.post(f'{endpoint}{url_person}', headers=headers_person, json=person_payload, verify=False)

            person_info = {}
            if response_person.status_code == 200:
                person_data = response_person.json()
                if person_data['data']['list']:
                    person = person_data['data']['list'][0]
                    person_info = {
                        "personGivenName": person.get("personGivenName", "N/A").strip('"'),
                        "personFamilyName": person.get("personFamilyName", "N/A").strip('"'),
                        "personId": person.get("personId", "N/A").strip('"'),
                        "personCode": person.get("personCode", "N/A").strip('"'),
                        "phoneNo": person.get("phoneNo", "N/A").strip('"'),
                        "email": person.get("email", "N/A").strip('"'),
                        "remark": person.get("remark", "N/A").strip('"'),
                        "personPhoto": person.get("personPhoto", {}).get("picUri", "N/A").strip('"')
                    }

                    # Загрузка фотографии
                    picture_payload = {
                        "personId": person_info["personId"],
                        "picUri": person_info["personPhoto"]
                    }
                    headers_picture = generate_signature(url_picture_data, picture_payload)
                    response_picture = requests.post(f'{endpoint}{url_picture_data}', headers=headers_picture, json=picture_payload, verify=False)

                    if response_picture.status_code == 200:
                        cleaned_base64 = clean_base64(response_picture.text)

                        if cleaned_base64:
                            try:
                                image_data = base64.b64decode(cleaned_base64, validate=True)
                                safe_name = slugify(name, lowercase=True)  # Преобразуем имя в безопасный формат
                                image_filename = f"{safe_name}_id{person_info['personId']}_photo.jpg"
                                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

                                # Сохранение фото
                                with open(image_path, "wb") as image_file:
                                    image_file.write(image_data)
                                    print(f"Файл сохранен: {image_path}")
                                    print(f"Полный путь к файлу: {os.path.abspath(image_path)}")

                                person_info["image_filename"] = image_filename
                            except Exception as e:
                                print(f"Ошибка обработки изображения: {e}")
                                person_info["image_filename"] = "Error processing image"
                        else:
                            person_info["image_filename"] = "No image data"
                    else:
                        person_info["image_filename"] = "Failed to fetch picture data"

            record = {
                "Name": person_info.get("personGivenName"),
                "Surname": person_info.get("personFamilyName"),
                "Check in time": format_event_time(entry['eventTime']),
                "Check point name": entry['doorName'],
                "Temperature": entry.get('temperatureData', ''),
                "Person Id": person_info.get("personId"),
                "Person Code": person_info.get("personCode"),
                "Card No": entry['cardNo'],
                "Phone number": person_info.get("phoneNo"),
                "Email": person_info.get("email"),
                "Remark": person_info.get("remark"),
                "Event type": 'Access granted by ' + event_name,
                "Image Filename": person_info.get("image_filename", "N/A")
            }
            results.append(record)

        return jsonify(results)
    else:
        return jsonify({'error': 'Failed to fetch events'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)