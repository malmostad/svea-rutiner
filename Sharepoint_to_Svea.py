import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# KONFIGURATION
# ==========================================

# 1. SveaGPT Inställningar
SVEA_CLIENT_ID = os.getenv('SVEA_CLIENT_ID')
SVEA_CLIENT_SECRET = os.getenv('SVEA_CLIENT_SECRET')
SVEA_TOKEN_URL = "https://staging.sveagpt.se/oauth/token"
SVEA_BASE_URL = "https://staging.sveagpt.se/api/v1"
TARGET_FOLDER_ID = 24283  #HVOF/Ordbo/Rutiner

# 2. Microsoft Graph / SharePoint Inställningar
GRAPH_TENANT_ID = os.getenv('GRAPH_TENANT_ID')
GRAPH_CLIENT_ID = os.getenv('GRAPH_CLIENT_ID')
GRAPH_CLIENT_SECRET = os.getenv('GRAPH_CLIENT_SECRET')
SHAREPOINT_HOSTNAME = "cityofmalmo.sharepoint.com"
SITE_PATH = "/sites/hvofandytest"
SHAREPOINT_FOLDER = "SveaGPT-TEST"

# 3. Lokal temporär lagring
LOCAL_FOLDER = "./filer_att_ladda_upp"


# ==========================================
# AUTENTISERING
# ==========================================

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
        print(f"[FEL] Vid hämtning av SveaGPT-token: {e}")
    return None

def get_graph_token():
    url = f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": GRAPH_CLIENT_ID,
        "client_secret": GRAPH_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
    except Exception as e:
        print(f"[FEL] Vid hämtning av Microsoft-token: {e}")
    return None


# ==========================================
# SVEAGPT: RENSNING OCH UPPLADDNING
# ==========================================

def clean_folder_before_upload(svea_token, folder_id):
    print(f"[INFO] Rensar mapp {folder_id} i SveaGPT före ny uppladdning...")
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
            
            files_to_delete = [f for f in all_files if f.get('folder_id') == folder_id]
            
            if not files_to_delete:
                print("[INFO] Mappen är redan tom. Ingen rensning behövs.")
                return True
                
            print(f"[INFO] Hittade {len(files_to_delete)} gamla filer. Raderar...")
            
            for f in files_to_delete:
                file_id = f.get('id')
                file_name = f.get('name', f.get('file_name', 'Okänd fil'))
                
                if file_id:
                    delete_url = f"{SVEA_BASE_URL}/files/{file_id}"
                    del_response = requests.delete(delete_url, headers=headers)
                    
                    if del_response.status_code in [200, 204]:
                        print(f"  - Raderad: {file_name}")
                    else:
                        print(f"  - [FEL] Misslyckades att radera {file_name} (Status: {del_response.status_code})")
                        
            print("[OK] Rensning klar.\n")
            return True
        else:
            print(f"[FEL] Kunde inte hämta fillistan för rensning (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"[FEL] Vid rensning av SveaGPT-mapp: {e}")
        return False

def upload_to_svea(svea_token, file_path, folder_id):
    file_name = os.path.basename(file_path)
    url = f"{SVEA_BASE_URL}/files"
    
    headers = {
        "Authorization": f"Bearer {svea_token}",
        "Accept": "application/json"
    }

    data = {"folder_id": folder_id}

    with open(file_path, 'rb') as f:
        files = [('files[]', (file_name, f, 'application/pdf'))]
        response = requests.post(url, headers=headers, files=files, data=data)
        
    if response.status_code in [200, 201]:
        res_json = response.json()
        file_id = res_json[0].get('id') if isinstance(res_json, list) else res_json.get('id')
        print(f"  - [OK] Uppladdad till SveaGPT (Fil-ID: {file_id})")
        return True
    else:
        print(f"  - [FEL] Vid uppladdning till SveaGPT: {response.status_code} - {response.text}")
        return False


# ==========================================
# HUVUDFLÖDE
# ==========================================

def run_sync():
    print("-" * 50)
    print(" STARTAR SYNKRONISERING: SHAREPOINT -> SVEAGPT")
    print("-" * 50)

    # Säkerställ lokal mapp
    if not os.path.exists(LOCAL_FOLDER):
        os.makedirs(LOCAL_FOLDER)

    graph_token = get_graph_token()
    svea_token = get_svea_token()

    if not graph_token or not svea_token:
        print("[AVBRYTER] Kunde inte autentisera mot alla system.")
        return

    print("[OK] Autentisering mot båda system lyckades.")

    # Rensa målmappen i SveaGPT
    clean_folder_before_upload(svea_token, TARGET_FOLDER_ID)

    # Hämta Site ID från SharePoint
    graph_headers = {"Authorization": f"Bearer {graph_token}", "Accept": "application/json"}
    site_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_HOSTNAME}:{SITE_PATH}"
    site_res = requests.get(site_url, headers=graph_headers)
    
    if site_res.status_code != 200:
        print(f"[FEL] Kunde inte hitta SharePoint-site: {site_res.text}")
        return
    site_id = site_res.json().get('id')

    # Lista filer i SharePoint-mappen
    files_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{SHAREPOINT_FOLDER}:/children"
    files_res = requests.get(files_url, headers=graph_headers)
    
    if files_res.status_code != 200:
        print(f"[FEL] Kunde inte läsa SharePoint-mapp: {files_res.text}")
        return

    items = files_res.json().get('value', [])
    sp_files = [item for item in items if 'file' in item]

    if not sp_files:
        print("[INFO] Inga filer hittades i SharePoint-mappen. Inget att synka.")
        return

    print(f"[INFO] Hittade {len(sp_files)} filer i SharePoint. Påbörjar överföring...\n")

    for f in sp_files:
        file_name = f['name']
        download_url = f.get('@microsoft.graph.downloadUrl')

        if not download_url:
            print(f"[VARNING] Kunde inte hämta nedladdningslänk för {file_name}, hoppar över.")
            continue

        print(f"[BEARBETAR] {file_name}")
        
        file_res = requests.get(download_url)
        if file_res.status_code == 200:
            local_file_path = os.path.join(LOCAL_FOLDER, file_name)
            with open(local_file_path, 'wb') as lf:
                lf.write(file_res.content)
            
            upload_to_svea(svea_token, local_file_path, TARGET_FOLDER_ID)
            
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                print("  - [INFO] Temporär lokal fil raderad.")
        else:
            print(f"  - [FEL] Misslyckades att ladda ner från SharePoint (Kod: {file_res.status_code})")
        print("-" * 50)

    print(" SYNKRONISERING AVSLUTAD!")
    print("-" * 50)


if __name__ == "__main__":
    run_sync()