import sys
import json
import urllib.request
import uuid
from pathlib import Path
sys.path.insert(0, "/opt/signalforge-newspaper-telegram/v2.1")
from newspaper_telegram_transport import _credentials
token, chat = _credentials()
path = Path("/tmp/S01-Chinese-News-Review-84-20261016.pdf")
boundary = "s01-" + uuid.uuid4().hex
head = (f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="S01-84-Chinese-Review.pdf"\r\n'
        'Content-Type: application/pdf\r\n\r\n').encode()
body = head + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendDocument",
    data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST")
response = json.load(urllib.request.urlopen(req, timeout=150))
print("pdf_message_id", response["result"]["message_id"], flush=True)
