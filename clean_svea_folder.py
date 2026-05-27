import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Inställningar
SVEA_CLIENT_ID = os.getenv('SVEA_CLIENT_ID')
SVEA_CLIENT_SECRET = os.getenv('SVEA_CLIENT_SECRET')
SVEA_TOKEN_URL = "https://staging.sveagpt.se/oauth/token"
SVEA_BASE_URL = "https://staging.sveagpt.se/api/v1"
TARGET_FOLDER_ID = 24283 

def get_svea_token():
    payload = {
        "grant_type": "client_credentials",
        "client_id": SVEA_CLIENT_ID,
        "client_secret": SVEA_CLIENT_SECRET
    }
    try:
        response = requests.post(SVEA_TOKEN_URL, data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
    except Exception as e:
        print(f"Fel vid hämtning av SveaGPT-token: {e}")
    return None

def clean_specific_folder(svea_token, folder_id):
    print(f"Startar rensning av mapp {folder_id}...")
    
    headers = {
        "Authorization": f"Bearer {svea_token}",
        "Accept": "application/json"
    }
    
    url = f"{SVEA_BASE_URL}/files"
    params = {"folder_id": folder_id} 
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            all_files = data if isinstance(data, list) else data.get('data', [])
            
            # Säkerhetsfiltrering: Radera endast filer som faktiskt har rätt folder_id
            files_to_delete = [f for f in all_files if f.get('folder_id') == folder_id]
            
            if not files_to_delete:
                print("Mappen är redan tom. Ingen rensning behövs.")
                return
                
            print(f"Hittade {len(files_to_delete)} filer. Raderar...")
            
            for f in files_to_delete:
                file_id = f.get('id')
                file_name = f.get('name', f.get('file_name', 'Okänd fil'))
                
                if file_id:
                    delete_url = f"{SVEA_BASE_URL}/files/{file_id}"
                    del_response = requests.delete(delete_url, headers=headers)
                    
                    if del_response.status_code in [200, 204]:
                        print(f" - Raderad: {file_name}")
                    else:
                        print(f" - Misslyckades att radera {file_name} (Status: {del_response.status_code})")
                        
            print("Rensning avslutad.")
        else:
            print(f"Kunde inte hämta fillistan (Status: {response.status_code})")
            print(f"Svar från servern: {response.text}")
            
    except Exception as e:
        print(f"Ett oväntat fel uppstod: {e}")

if __name__ == "__main__":
    print("-" * 40)
    print(" SVEAGPT - MANUELL MAPPRENSNING")
    print("-" * 40)
    
    token = get_svea_token()
    if token:
        clean_specific_folder(token, TARGET_FOLDER_ID)
    else:
        print("Kunde inte starta på grund av autentiseringsfel.")
        
    print("-" * 40)