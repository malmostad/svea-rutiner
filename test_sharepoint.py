import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Inställningar för Microsoft Graph
TENANT_ID = os.getenv('GRAPH_TENANT_ID')
CLIENT_ID = os.getenv('GRAPH_CLIENT_ID')
CLIENT_SECRET = os.getenv('GRAPH_CLIENT_SECRET')

SHAREPOINT_HOSTNAME = "cityofmalmo.sharepoint.com"
SITE_PATH = "/sites/hvofandytest"
FOLDER_NAME = "SveaGPT-TEST"

def get_graph_token():
    print(" Hämtar token från Microsoft...")
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print(" Autentisering OK!")
        return response.json().get('access_token')
    else:
        print(" Autentisering misslyckades!")
        print("Felmeddelande:", response.text)
        return None

def list_sharepoint_files(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # 1. Hämta det unika ID:t för siten
    print(f"\n Söker efter siten: {SITE_PATH}...")
    site_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_HOSTNAME}:{SITE_PATH}"
    site_response = requests.get(site_url, headers=headers)

    if site_response.status_code != 200:
        print(" Kunde inte hitta siten eller saknar behörighet.")
        print("Felmeddelande:", site_response.text)
        return

    site_id = site_response.json().get('id')
    print(" Site ID hittat!")

    # 2. Hämta filerna inuti mappen "SveaGPT-TEST"
    print(f"\n Letar efter filer inuti mappen '{FOLDER_NAME}'...")
    
    files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{FOLDER_NAME}:/children"
    files_response = requests.get(files_url, headers=headers)

    if files_response.status_code == 200:
        items = files_response.json().get('value', [])
        files = [item for item in items if 'file' in item]
        
        if not files:
            print(f" Mappen '{FOLDER_NAME}' hittades, men den verkar vara tom på filer.")
        else:
            print(f" Hittade {len(files)} filer i mappen:")
            for f in files:
                print(f"  {f['name']}")
    else:
        print(f" Kunde inte läsa mappen '{FOLDER_NAME}'.")
        print("Felmeddelande:", files_response.text)

if __name__ == "__main__":
    print("-" * 40)
    print(" TESTAR SHAREPOINT-KOPPLING")
    print("-" * 40)
    
    token = get_graph_token()
    if token:
        list_sharepoint_files(token)
        
    print("-" * 40)