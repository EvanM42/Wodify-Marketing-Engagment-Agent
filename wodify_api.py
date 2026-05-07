import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.wodify.com/v1"
API_KEY = os.getenv("WODIFY_PUBLIC_API_KEY", "")


def _headers():
    return {"x-api-key": API_KEY}


def get_clients(params=None):
    resp = requests.get(f"{BASE_URL}/clients", headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def send_email(client_id: str, subject: str, body: str):
    payload = {"client_id": client_id, "subject": subject, "body": body}
    resp = requests.post(f"{BASE_URL}/communications/email", headers=_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()
