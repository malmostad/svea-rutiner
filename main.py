import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Inställningar
CLIENT_ID = os.getenv('SVEA_CLIENT_ID')
CLIENT_SECRET = os.getenv('SVEA_CLIENT_SECRET')
TOKEN_URL = "https://staging.sveagpt.se/oauth/token"
BASE_URL = "https://staging.sveagpt.se/api/v1"
LOCAL_FOLDER = "./filer_att_ladda_upp"

def get_access_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    try:
        response = requests.post(TOKEN_URL, data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
    except Exception:
        return None
    return None

def upload_file(token, file_path):
    file_name = os.path.basename(file_path)
    url = f"{BASE_URL}/files"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    with open(file_path, 'rb') as f:
        files = [
            ('files[]', (file_name, f, 'application/pdf'))
        ]
        
        print(f" Skickar: {file_name}...")
        response = requests.post(url, headers=headers, files=files)
        
    if response.status_code in [200, 201]:
        data = response.json()
        # Hantera både lista och enskilt objekt i svaret
        if isinstance(data, list) and len(data) > 0:
            file_id = data[0].get('id')
        else:
            file_id = data.get('id')
            
        print(f" Lyckades! Fil-ID: {file_id}")
        return file_id
    else:
        print(f" Fel vid uppladdning av {file_name}: {response.status_code}")
        print(f"Meddelande: {response.text}")
        return None

if __name__ == "__main__":
    print("-" * 30)
    print(" SveaGPT Sync-skript startar")
    print("-" * 30)

    # 1. Hämta token och visa status
    token = get_access_token()
    
    if token:
        print(" Autentisering lyckades! Åtkomst beviljad.")
        print("-" * 30)
        
        # 2. Kontrollera att mappen finns
        if not os.path.exists(LOCAL_FOLDER):
            os.makedirs(LOCAL_FOLDER)
            print(f" Mappen {LOCAL_FOLDER} skapad. Lägg dina filer där!")
        else:
            # 3. Ladda upp alla PDF:er i mappen
            files_to_upload = [f for f in os.listdir(LOCAL_FOLDER) if f.endswith('.pdf')]
            
            if not files_to_upload:
                print(" Inga PDF-filer hittades i mappen.")
            else:
                print(f"Hittade {len(files_to_upload)} filer att ladda upp.\n")
                for filename in files_to_upload:
                    full_path = os.path.join(LOCAL_FOLDER, filename)
                    upload_file(token, full_path)
    else:
        print(" Autentisering misslyckades!")
        print("Kontrollera CLIENT_ID och CLIENT_SECRET i din .env-fil.")
    
    print("-" * 30)
    print(" Körning avslutad.")