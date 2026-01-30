import os
import sys
import json
import subprocess

def install_dependencies():
    print("📦 正在檢查並安裝開發環境所需的套件...")
    try:
        # 第一嘗試：標準安裝
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 套件安裝完成。")
    except Exception:
        print("⚠️ 標準安裝失敗，正在嘗試使用鏡像站 (Mirror)...")
        try:
            # 第二嘗試：使用鏡像站
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt", 
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
            ])
            print("✅ 透過鏡像站安裝成功。")
        except Exception as e:
            print(f"❌ 套件安裝完全失敗: {e}")
            print("💡 建議：請手動執行 'pip install pyngrok' 看看是否有更詳細的錯誤訊息。")
            sys.exit(1)

# Check for dependencies before importing other modules
try:
    from dotenv import load_dotenv
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from linebot import LineBotApi
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    import datetime
    import requests
    from pyngrok import ngrok
except ImportError:
    install_dependencies()
    # Now try again after installation
    from dotenv import load_dotenv
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from linebot import LineBotApi
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    import datetime
    import requests
    from pyngrok import ngrok

def check_env():
    print("🔍 開始檢查環境設定...")
    load_dotenv()
    
    all_passed = True
    
    # 1. 檢查 LINE 設定
    line_secret = os.getenv('LINE_CHANNEL_SECRET')
    line_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    if not line_secret or line_secret == '你的_Channel_Secret':
        print("❌ LINE_CHANNEL_SECRET 未設定或為預設值")
        all_passed = False
    else:
        print("✅ LINE_CHANNEL_SECRET 已讀取")
        
    if not line_token or line_token == '你的_Channel_Access_Token':
        print("❌ LINE_CHANNEL_ACCESS_TOKEN 未設定或為預設值")
        all_passed = False
    else:
        try:
            line_bot_api = LineBotApi(line_token)
            # 嘗試讀取 Bot info 驗證 token
            bot_info = line_bot_api.get_bot_info()
            print(f"✅ LINE Token 驗證成功 (Bot Name: {bot_info.display_name})")
        except Exception as e:
            print(f"❌ LINE Token 驗證失敗: {e}")
            all_passed = False

    # 2. 檢查 Google 憑證 (優先使用 token.json 或啟動 OAuth)
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("✅ 找到個人帳號授權檔案 (token.json)")
    elif os.path.exists('client_secrets.json'):
        print("💡 偵測到 client_secrets.json，但尚未授權。正在啟動授權流程...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ 授權成功！已產生 token.json")
        except Exception as e:
            print(f"❌ 授權流程失敗: {e}")
            all_passed = False
    else:
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        if not os.path.exists(creds_path):
            print("❌ 找不到 token.json, client_secrets.json 或 credentials.json")
            all_passed = False
        else:
            print(f"✅ 找到 Service Account 憑證檔案: {creds_path}")
            try:
                creds = service_account.Credentials.from_service_account_file(
                    creds_path, 
                    scopes=SCOPES
                )
                print("✅ Service Account 憑證格式正確")
            except Exception as e:
                print(f"❌ Google 憑證驗證失敗: {e}")
                all_passed = False

    if creds:
        try:
            # 3. 檢查 Google Drive 權限與 Folder ID
            folder_id = os.getenv('TARGET_DRIVE_FOLDER_ID')
            if not folder_id or folder_id == 'XXXXXXXXXX':
                print("❌ TARGET_DRIVE_FOLDER_ID 未設定或為預設值")
                all_passed = False
            else:
                try:
                    drive_service = build('drive', 'v3', credentials=creds)
                    
                    # 檢查機器人目前的空間配額
                    about = drive_service.about().get(fields="storageQuota").execute()
                    quota = about.get('storageQuota', {})
                    limit = int(quota.get('limit', 0)) / (1024**3)
                    usage = int(quota.get('usage', 0)) / (1024**3)
                    print(f"📊 機器人空間狀態: 已使用 {usage:.2f} GB / 總額 {limit:.2f} GB")

                    # 加入 supportsAllDrives=True 以支援共用雲端硬碟
                    folder = drive_service.files().get(
                        fileId=folder_id, 
                        fields='name, capabilities',
                        supportsAllDrives=True
                    ).execute()
                    print(f"✅ 成功存取 Google Drive 資料夾: {folder.get('name')}")
                    
                    # 4. 測試建立/存取 Google 文件
                    test_doc_name = "test-doc-bot"
                    
                    # 搜尋是否已有同名文件
                    query = f"name = '{test_doc_name}' and '{folder_id}' in parents and trashed = false"
                    results = drive_service.files().list(
                        q=query, 
                        spaces='drive', 
                        fields='files(id, name)',
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    ).execute()
                    files = results.get('files', [])
                    
                    if not files:
                        print(f"🚀 正在目標資料夾建立測試文件: {test_doc_name}...")
                        doc_metadata = {
                            'name': test_doc_name,
                            'mimeType': 'application/vnd.google-apps.document',
                            'parents': [folder_id]
                        }
                        test_doc = drive_service.files().create(
                            body=doc_metadata,
                            fields='id',
                            supportsAllDrives=True
                        ).execute()
                        print(f"✅ Google 文件建立成功！ (Doc ID: {test_doc.get('id')})")
                    else:
                        print(f"✅ 測試文件 '{test_doc_name}' 已存在，驗證寫入權限...")
                        file_id = files[0]['id']
                        # 更新文件描述以驗證寫入權限，避免產生重複文件
                        drive_service.files().update(
                            fileId=file_id,
                            body={'description': f'Last environment check at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'},
                            supportsAllDrives=True
                        ).execute()
                        print(f"✅ 測試文件更新成功，寫入權限正常。")
                    
                    if limit > 0:
                        print("✨ 檢查通過！您的帳號具備足夠空間，支援儲存文字、圖片及影片檔案。")
                    else:
                        print("⚠️ 警告：偵測到儲存配額為 0。這代表您可能無法上傳圖片或影片，但仍可建立 Google 文件儲存文字。")
                        print("💡 建議：若需支援多媒體，請參考 README 改用『個人帳號授權』以使用您的主要空間。")
                        
                except Exception as e:
                    print(f"❌ 存取或上傳測試失敗: {e}")
                    if "storageQuotaExceeded" in str(e):
                        print("\n💡 診斷建議: 儲存配額已滿或為 0。")
                        print("1. 請清理雲端硬碟空間。")
                        print("2. 若使用 Service Account，請參考 README 改用『個人帳號授權』以使用您的主要空間。")
                    all_passed = False
        except Exception as e:
            print(f"❌ Google 憑證驗證失敗: {e}")
            all_passed = False

    print("\n" + "="*30)
    if all_passed:
        print("🎉 所有設定檢查完成！您可以啟動 Bot 了。")
    else:
        print("再檢查一下上面的錯誤訊息並修正 .env 檔案。")
    print("="*30)

    if all_passed:
        print("\n✨ 檢查完成！")
        print("💡 提示：您現在可以執行 'python -m src.main' 來啟動 Bot。")
        print("� 提示：若需在本地自動啟動 ngrok，請確保 .env 中 USE_NGROK=true。")

if __name__ == "__main__":
    check_env()
