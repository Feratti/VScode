import json
# Import smtplib for the actual sending function
import smtplib
import requests
# Import the email modules we'll need
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from datetime import datetime
from email import encoders

sending_ts = datetime.now()
sub = "Log from HCP |  %s" % sending_ts.strftime('%Y-%m-%d %H:%M:%S')
msg = MIMEMultipart('alternative')
msg['From'] = 'feratti@mail.ru'
msg['To'] = 'kuzin.vadim@outlook.com'
msg['Subject'] = sub
sender = "feratti@mail.ru"
password = "mWc3DC8Py4ZGApyFVsUR"
url = "https://official-joke-api.appspot.com/random_joke"
response = requests.get(url)
message = response.text
with open('data.json', 'w') as f:
    json.dump(message, f)
    f.close()

print (response.status_code)

js_obj = json.loads(message)
jf = json.dumps(js_obj, indent=4)

obj = MIMEBase('application',"octet-stream")
obj.set_payload(jf)
encoders.encode_base64(obj)

body = "This would be the body of the msg"
msg.attach(MIMEText(body, 'plain'))

obj.add_header('Content-Disposition', 'attachment; filename="test.json"')
msg.attach(obj)

s = smtplib.SMTP('smtp.mail.ru', 587)
s.starttls()
s.login(user=sender, password=password)
s.send_message(msg)
s.quit()