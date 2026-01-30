# Chat-to-Google-Drive Save Bot

- Author: Chun-Lung(Gyd) Tseng
- Email: kingterrygyd@gmail.com
- Twitter: @kingterrygyd
- Facebook: facebook.com/barbariangyd
- [![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/ncp/payment/TY3G9Z2WJR2JJ)



這是一個專為 LINE（未來支援 Discord）設計的聊天機器人，其唯一目標是：**將使用者在聊天中標記的內容（文字、連結、檔案），整理後直接存入 Google Drive**。

這非常適合作為 **NotebookLM** 或其他 AI 工具的資料收集器。

## 🚀 核心功能

- **精確捕捉**：只有在輸入 `/save` 指令時，Bot 才會處理內容，保護隱私。
- **結構化整理**：自動產生包含標題、來源、時間戳記與內容的 Google Doc。
- **多媒體支援**：
  - **純文字 & 連結**：直接寫入 Google Doc。
  - **圖片/影片/檔案**：上傳至 Google Drive 檔案夾，並在 Doc 中保留連結。
- **自動標題**：支援 `/save [你的標題]`，若未提供則自動以時間命名。

## 🛠️ 技術架構

- **Runtime**: Python 3.10+ (FastAPI)
- **Adapter 模式**：核心邏輯與通訊平台（LINE/Discord）解耦。
- **Google API**: 使用 Google Drive & Documents API 進行高可靠性寫入。

## 📦 安裝與設定

### 1. Google 雲端平台基礎設定 (必要)
無論選擇哪種授權方式，都必須先完成以下準備：
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)。
2. **建立新專案**：點擊上方專案選擇器，建立一個新專案（如 `Gyd-Drive-Bot`）。
3. **啟用 API**：在搜尋列搜尋並點擊「啟用」以下兩個服務：
   - **Google Drive API**
   - **Google Docs API**

### 2. 選擇授權方式 (二選一)

#### 方案 A: 使用個人帳號 (推薦，可使用個人空間)
此方式讓機器人以您的身份執行，檔案擁有者為您自己。
1. 前往「憑證」頁面，點擊 **「建立憑證」** > **「OAuth 用戶端 ID」**。
2. **設定同意畫面 (重要)**：
   - 點擊「設定同意畫面」，選擇 **External**。
   - 填寫 App 名稱及您的 Email。
   - **新增測試使用者**：在「Test users」區塊點擊 **ADD USERS**，輸入您自己的 Google Email。*（未加入將會導致 403 access_denied 錯誤）*
3. 應用程式類型選擇 **「桌面應用程式 (Desktop App)」**。
4. 下載 JSON 檔案，更名為 `client_secrets.json` 並放在專案根目錄。
5. 執行授權腳本：
   ```bash
   python scripts/authorize_user.py
   ```
   - *注意：若出現「Google 尚未驗證此應用程式」，請點擊「進階」並選擇「前往... (不安全)」以繼續。*

#### 方案 B: 使用 Service Account (適合伺服器長期執行)
此方式機器人為獨立帳號，但需注意 Service Account 本身空間配額限制。
1. 前往「服務帳戶」，建立名稱為 `drive-bot` 的帳戶。
2. 進入詳情頁 > 「金鑰」 > 「新增金鑰」 > 選擇 **JSON** 並下載。
3. 下載後更名為 `credentials.json` 並放在專案根目錄。
4. **授權資料夾**：將金鑰中的 `client_email` 加入您 Google Drive 資料夾的「共用」名單，並設定為「編輯者」。

### 2. 設定 LINE Messaging API
1. 前往 [LINE Developers Console](https://developers.line.biz/) 並登入。
2. **建立 Provider**：點擊「Create a new provider」，輸入名稱（如 `MyProjects`）後點擊「Create」。
3. **建立 Channel (透過官方帳號)**：
   - 點擊「Create a Messaging API channel」。
   - 系統會提示您無法直接建立，請點擊 **"Create a LINE Official Account"** 按鈕。
   - 這會導向 [LINE Official Account Manager](https://manager.line.biz/)。
4. **設定官方帳號**：
   - 填寫帳號名稱（如 `GDrive Save Bot`）及相關資訊並提交。
   - 進入帳號後，點擊右上角的「設定」 > 「Messaging API」。
   - 點擊「啟用 Messaging API」，並選擇您剛才建立的 **Provider**。
5. **取得金鑰與 Webhook (回到 Developers Console)**：
   - 回到 [LINE Developers Console](https://developers.line.biz/) 重新整理。
   - 進入剛產生的 Channel。
   - **Basic settings**：取得 **Channel secret**。
   - **Messaging API**：
     - **Channel access token**：點擊「Issue」取得 Token。
     - **Webhook URL**：輸入您的網址 + `/webhook/line`。
     - 開啟 **Use webhook** 並點擊「Update」。
6. **回應設定 (重要)**：
   - 回到 [Official Account Manager](https://manager.line.biz/)。
   - 「設定」 > 「回應設定」。
   - 將「回應模式」設為「聊天機器人」。
   - 在下方「詳細設定」中，將 **「Webhook」** 設為 **「啟用」**。
   - 將「自動回應訊息」與「招呼訊息」設為「停用」。

### 3. 環境變數
將上述步驟取得的資訊填入 `.env` 檔案中。複製 `.env.example` 並更名為 `.env`：
```env
# 來自 LINE Developers Console -> Basic settings
LINE_CHANNEL_SECRET=你的_Channel_Secret

# 來自 LINE Developers Console -> Messaging API (點擊 Issue 產生的長效 Token)
LINE_CHANNEL_ACCESS_TOKEN=你的_Channel_Access_Token

# 來自 Google Drive 資料夾的網址列 ID
# https://drive.google.com/drive/u/0/folders/XXXXXXXXXX 或 https://drive.google.com/drive/folders/XXXXXXXXXX 中的 XXXXXXXXXX
TARGET_DRIVE_FOLDER_ID=XXXXXXXXXX

# 憑證路徑 (預設為 credentials.json)
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

### 4. 初始化環境 (推薦)
此腳本會自動安裝所需的 Python 套件，並確認環境變數與 API 權限：
```bash
python scripts/check_environment.py
```

### 5. 啟動服務與自動 Webhook 設定
**現在您只需執行一條指令即可啟動 Bot 並自動處理網路連線：**

1. 確保您的 `.env` 中設定了：
   - `USE_NGROK=true`
   - `NGROK_AUTHTOKEN=您的_Authtoken` (請至 [ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken) 取得)
2. 啟動服務：
   ```bash
   python -m src.main
   ```
- Bot 啟動時會自動偵測 `USE_NGROK`，啟動隧道並**自動更新 LINE Developers Console 中的 Webhook URL**。
- 看到 `✅ [Dev] Webhook URL 已更新` 後，您的 Bot 就已經準備好接收訊息了！

### 6. 手動 Webhook 設定 (選用)
如果您不希望自動更新 Webhook，請將 `USE_NGROK` 設為 `false` 並手動設定：
1. **啟動 ngrok**：執行 `ngrok http 8000`。
2. **手動設定**：將 ngrok 網址填入 LINE Developers Console 的 Webhook URL 欄位並點擊 Update。

## 📝 使用說明

在 LINE 聊天室中：

1. **儲存純文字**
   ```
   /save 今天的會議紀錄
   ```

2. **儲存連結**
   ```
   /save 重要的參考連結
   https://example.com/article
   ```

3. **儲存圖片 / 影片 / 檔案**
   - **方式 A (直接發送)**：先上傳檔案及多媒體，bot 會即時處理（需配合 `save_service` 配置）。
   - **方式 B (回覆模式)**：對著想要儲存的圖片或檔案「長按 -> 回覆」，並輸入 `/save [標題]`。
   - Bot 會自動將檔案上傳至 Google Drive，並在對應的 Google Doc 中插入檔案下載/檢視連結。

## 🔒 隱私與安全
- **無長期資料暫存**：Bot 只負責轉接，不會在本地資料庫保存您的聊天內容。
- **群組隱私警示 (重要)**：請**避免將 Bot 邀請至多人群組**。由於目前採用綁定資料夾的設計，群組內任何成員輸入 `/save` 指令時，資料皆會被推送至您設定的 Google Drive。為了保護您的儲存空間與資訊安全，建議僅在 1:1 私訊中使用。
- **最小權限**：建議設定 Service Account 只具備特定資料夾的寫入權限。

---
*Developed with ❤️ for knowledge management enthusiasts.*
