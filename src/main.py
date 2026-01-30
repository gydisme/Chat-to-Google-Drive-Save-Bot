import os
from fastapi import FastAPI, Request, Header, HTTPException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 強專禁用系統代理設定，避免 Windows 環境下的 [SSL: WRONG_VERSION_NUMBER] 錯誤
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

print(f"🛠️ [Init] 環境變數已讀取，已排除系統代理干擾，當前目錄: {os.getcwd()}", flush=True)

from .adapters.line_adapter import LineAdapter
from .services.save_service import SaveService
from .clients.gdrive_client import GDriveClient

def setup_ngrok():
    """啟動 ngrok 並自動更新 LINE Webhook (僅用於本地開發)"""
    use_ngrok = os.getenv("USE_NGROK", "false").lower()
    print(f"🔍 [Debug] USE_NGROK 設定值為: '{use_ngrok}'", flush=True)
    if use_ngrok != "true":
        return

    try:
        from pyngrok import ngrok
        from linebot import LineBotApi
        
        # 1. 設定 Authtoken
        authtoken = os.getenv("NGROK_AUTHTOKEN")
        if authtoken:
            ngrok.set_auth_token(authtoken)
            
        # 2. 啟動隧道
        port = int(os.getenv("PORT", 8000))
        print(f"🚀 [Dev] 正在啟動 ngrok 隧道 (Port: {port})...", flush=True)
        public_url = ngrok.connect(port).public_url
        webhook_url = f"{public_url}/webhook/line"
        print(f"✅ [Dev] ngrok 已啟動: {public_url}", flush=True)
        
        # 3. 更新 LINE Webhook
        print(f"🔄 [Dev] 正在自動更新 LINE Webhook URL...", flush=True)
        line_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        line_bot_api = LineBotApi(line_token)
        line_bot_api.set_webhook_endpoint(webhook_url)
        print(f"✅ [Dev] Webhook URL 已更新為: {webhook_url}", flush=True)
        
    except Exception as e:
        print(f"⚠️ [Dev] 自動啟動 ngrok 或更新 Webhook 失敗: {e}", flush=True)
        print("💡 提示：您可以手動在 LINE Developers Console 設定 Webhook。", flush=True)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # 在啟動時嘗試啟動隧道 (僅用於本地開發)
    setup_ngrok()

# Initialize components
gdrive_client = GDriveClient()
save_service = SaveService(gdrive_client)
line_adapter = LineAdapter(save_service)

@app.post("/webhook/line")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    body_decoded = body.decode('utf-8')
    print(f"📩 收到 Webhook 請求! Signature: {x_line_signature}", flush=True)
    print(f"🔍 [Debug Raw Body]: {body_decoded}", flush=True)
    
    if not x_line_signature:
        print("⚠️ 錯誤：找不到 X-Line-Signature Header", flush=True)
    
    try:
        line_adapter.handle_request(body_decoded, x_line_signature)
        print("✅ 請求處理完成", flush=True)
    except Exception as e:
        print(f"❌ 處理 Webhook 時發生錯誤: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return {"status": "ok"}

@app.get("/")
def health_check():
    return {"status": "active", "service": "Chat-to-Google-Drive Save Bot"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
