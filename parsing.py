from pathlib import Path

import requests

base_url = 'https://dahua.az/catalog/'

base_save_path = Path('./dahua')

r = requests.get(base_url)

print(r.status_code)

html_file_path = base_save_path / 'dahua.html'

with open(str(html_file_path.absolute()), 'wb') as f:
    f.write(r.content)