import requests
import hashlib
import hmac
import base64
import time
import json
import smtplib
import os
import re
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# Email configuration
sender = "feratti@mail.ru"
password = "mWc3DC8Py4ZGApyFVsUR"
recipient = "feratti@mail.ru"

# API configuration
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

# Получаем список дверей
door_payload = {"pageNo": 1, "pageSize": 100}
headers_doors = generate_signature(url_door_list, door_payload)
response_doors = requests.post(f'{endpoint}{url_door_list}', headers=headers_doors, json=door_payload, verify=False)

door_index_codes = []
if response_doors.status_code == 200:
    door_data = response_doors.json()
    door_index_codes = [door["doorIndexCode"] for door in door_data.get("data", {}).get("list", [])]
    if not door_index_codes:
        print("Ошибка: Список дверей пуст.")
        exit(1)
else:
    print("Ошибка получения списка дверей:", response_doors.text)
    exit(1)

print(f"Получены doorIndexCodes: {door_index_codes}")  # Логирование

# Добавляем словарь для соответствия названий событий и их кодов
event_mapping = {
    "face": 196893,
    "card": 196894,  # Пример другого события
    # Добавьте другие события по необходимости
}

# Запрашиваем у пользователя название события
event_name = input("Enter event name (face/card/fingerprint): ")

# Получаем eventCode на основе введенного названия события
eventCode = event_mapping.get(event_name)
if eventCode is None:
    print("Ошибка: введено неизвестное название события.")
    exit(1)

# Функция для преобразования даты в формат API
def format_datetime(user_input):
    try:
        dt = datetime.strptime(user_input, "%d/%m/%Y %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:%S+04:00"), dt  # Возвращаем строку и объект datetime
    except ValueError:
        print("Ошибка: введите дату в формате ДД/ММ/ГГГГ ЧЧ:ММ")
        exit(1)

# Запрашиваем время у пользователя
start_time_str = input("Enter start date (DD/MM/YYYY HH:MM): ")
end_time_str = input("Enter end date (DD/MM/YYYY HH:MM): ")

start_time_iso, start_time_dt = format_datetime(start_time_str)
end_time_iso, _ = format_datetime(end_time_str)

# Конфигурация запроса с учетом введенного eventCode
command_payload = {
    "startTime": start_time_iso,
    "endTime": end_time_iso,
    "eventType": eventCode,
    "personName": "",
    "doorIndexCodes": door_index_codes,  # Используем динамически полученные данные
    "pageNo": 1,
    "pageSize": 500
}

# Функция для очистки строки base64
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

# API Calls
headers_events = generate_signature(url_events, command_payload)
response_events = requests.post(f'{endpoint}{url_events}', headers=headers_events, json=command_payload, verify=False)

email_body = "Hikvision event log system:\n\n"

if response_events.status_code == 200:
    event_data = response_events.json()
    total_events = event_data['data']['total']
    values = event_data['data']['list']
    email_body += f'Total events - {total_events} \nSelected event period: {start_time_str} to {end_time_str} \nSelected event type: Access granted by {event_name}\n\n'
    results = []
    attached_person_ids = set()  # Множество для personId с уже прикрепленными фото
    
    for entry in values:
        # Проверяем, соответствует ли событие введенному типу
        if entry.get('eventType') != eventCode:
            continue  # Пропускаем события, которые не соответствуют введенному типу
        
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
                
                if person_info["personId"] not in attached_person_ids:
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
                                image_filename = f"{name}_ID{person_info['personId']}_photo.jpg"
                                
                                # Сохранение фото в текущей директории
                                with open(image_filename, "wb") as image_file:
                                    image_file.write(image_data)
                                
                                print(f"Файл сохранен: {image_filename}")  # Логирование
                                person_info["image_filename"] = image_filename
                                attached_person_ids.add(person_info["personId"])  # Добавляем personId в множество
                            except Exception as e:
                                print(f"Ошибка обработки изображения: {e}")  # Логирование
                                person_info["image_filename"] = "Error processing image"
                        else:
                            person_info["image_filename"] = "No image data"
                    else:
                        person_info["image_filename"] = "Failed to fetch picture data"
        
        record = {
            "Name": person_info.get("personGivenName"),
            "Surname": person_info.get("personFamilyName"),
            "Check in time": format_event_time(entry['eventTime']),  # Теперь в удобном формате
            "Check point name": entry['doorName'],
            "Temperature": entry.get('temperatureData', ''),
            "Person Id": person_info.get("personId"),
            "Person Code": person_info.get("personCode"),
            "Card No": entry['cardNo'],
            "Person Photo": person_info.get("personPhoto"),
            "Phone number": person_info.get("phoneNo"),
            "Email": person_info.get("email"),
            "Remark": person_info.get("remark"),
            "Event type": 'Access granted by ' + event_name,  # Используем введенное название события
            "Image Filename": person_info.get("image_filename", "N/A")
        }
        results.append(record)
        
        # email_body += f"Name: {name}\nCheck in time: {format_event_time(entry['eventTime'])}\nCheck point: {entry['doorName']}\n"
        # email_body += f"Person Id: {person_info.get('personId')}\nPerson Code: {person_info.get('personCode')}\nPerson Photo: {person_info.get('personPhoto')}\n\n"

    filename = "total_results.csv"

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())  # Заголовки из ключей словаря
        writer.writeheader()  # Записываем заголовок
        writer.writerows(results)  # Записываем строки


    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = f"Event log from HCP | Access granted by {event_name}"
    msg.attach(MIMEText(email_body, 'plain'))
    
    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(filename, "rb").read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    msg.attach(part)

    # Прикрепляем изображения
    for entry in results:
        image_filename = entry.get("Image Filename")
        if image_filename and os.path.exists(image_filename):
            print(f"Прикрепляю фото: {image_filename}")
            with open(image_filename, "rb") as image_file:
                image_part = MIMEBase('image', 'jpeg')
                image_part.set_payload(image_file.read())
                encoders.encode_base64(image_part)
                image_part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(image_filename)}"')
                msg.attach(image_part)
        else:
            print(f"Файл отсутствует или ошибка: {image_filename}")

    s = smtplib.SMTP('smtp.mail.ru', 587)
    s.starttls()
    s.login(user=sender, password=password)
    s.send_message(msg)
    s.quit()
    print("Command executed successfully, email sent.")
else:
    print("Failed to execute command:", response_events.text)