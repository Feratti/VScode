import smtplib
import requests
import json

url = "https://api.github.com"
sender = "feratti@mail.ru"
password = "mWc3DC8Py4ZGApyFVsUR"
response = requests.get(url)

message = response.text
with open('data.json', 'w') as f:
    json.dump(message, f, ensure_ascii=False, indent=4)


receivers = "kuzin.vadim@outlook.com"

connection = smtplib.SMTP("smtp.mail.ru", 587)
connection.starttls()
connection.login(user=sender, password=password)
try:
    connection.sendmail(sender, receivers, message)
    print("Success")
except:
    print("Fail to send")

connection.close()