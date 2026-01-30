import os
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# 如果修改了這些 scopes，請刪除 token.json 重新來過
SCOPES = ['https://www.googleapis.com/auth/drive']

def authorize():
    creds = None
    # token.json 儲存使用者的存取與重新整理權杖
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 如果沒有憑證或憑證無效，請登入
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                print("❌ 找不到 client_secrets.json！請從 Google Cloud Console 下載 OAuth 憑證。")
                return
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 儲存憑證供下次使用
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("✅ 授權成功！已產生 token.json，機器人現在將以您的身份執行。")

if __name__ == "__main__":
    authorize()
