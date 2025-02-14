from bs4 import BeautifulSoup
from pathlib import Path
import requests
import json

base_url = 'https://dahua.az/catalog/ip__1/'

r = requests.get(base_url)

soap = BeautifulSoup(r.text, "lxml")

#msgs = soap.find_all('a', {"class":"name name_P_S name_js"})
with open ('siteoutput.txt', 'w') as file:
    for wrapper in soap.find_all(True, {"class":['name name_P_S name_js', 'price']}):
        for p in soap.select('span'):
            p.extract()
        file.write(wrapper.text.strip() + '\n')
file.close()

print(len(soap), type(soap))