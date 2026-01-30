[🇹🇼 繁體中文](README.zh-TW.md) | [🇺🇸 English](README.md)

# Chat-to-Google-Drive Save Bot

- Author: Chun-Lung(Gyd) Tseng
- Email: kingterrygyd@gmail.com
- Twitter: @kingterrygyd
- Facebook: facebook.com/barbariangyd
- [![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/ncp/payment/TY3G9Z2WJR2JJ)

This is a chatbot designed for LINE (Discord support coming soon) with a single goal: **to organize and save content marked by the user in chats (text, links, files) directly to Google Drive**.

It is perfect for acting as a data collector for **NotebookLM** or other AI tools.

## 🚀 Core Features

- **Precise Capture**: The bot processes content ONLY when the `/save` command is used, ensuring privacy.
- **Structured Organization**: Automatically generates Google Docs containing titles, sources, timestamps, and content.
- **Multimedia Support**:
  - **Plain Text & Links**: Written directly to Google Docs.
  - **Images/Videos/Files**: Uploaded to a Google Drive folder, with links preserved in the Doc.
- **Auto-Title**: Supports `/save [Your Title]`. If no title is provided, it defaults to a timestamp.

## 🛠️ Technical Architecture

- **Runtime**: Python 3.10+ (FastAPI)
- **Adapter Pattern**: Decouples core logic from communication platforms (LINE/Discord).
- **Google API**: Uses Google Drive & Documents API for highly reliable writing.

## 📦 Installation & Setup

### 1. Google Cloud Platform Basic Setup (Required)
Regardless of the authorization method chosen, you must complete the following preparations:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. **Create New Project**: Click the project selector at the top and create a new project (e.g., `Gyd-Drive-Bot`).
3. **Enable APIs**: Search for and "Enable" the following two services:
   - **Google Drive API**
   - **Google Docs API**

### 2. Choose Authorization Method (Pick One)

#### Option A: Use Personal Account (Recommended, uses personal storage)
This method runs the bot as you, and you own the files.
1. Go to the "Credentials" page, click **"Create Credentials"** > **"OAuth Client ID"**.
2. **Configure Consent Screen (Important)**:
   - Click "Configure Consent Screen", select **External**.
   - Fill in the App Name and your Email.
   - **Add Test Users**: Under the "Test users" section, click **ADD USERS** and enter your own Google Email. *(Failure to add this will result in a 403 access_denied error)*
3. Select Application Type **"Desktop App"**.
4. Download the JSON file, rename it to `client_secrets.json`, and place it in the project root directory.
5. Run the authorization script:
   ```bash
   python scripts/authorize_user.py
   ```
   - *Note: If you see "Google hasn't verified this app", click "Advanced" and select "Go to... (unsafe)" to continue.*

#### Option B: Use Service Account (Suitable for long-running servers)
This method runs the bot as a standalone account, but be aware of the Service Account's storage quota limits.
1. Go to "Service Accounts", create an account named `drive-bot`.
2. Enter details page > "Keys" > "Add Key" > Select **JSON** and download.
3. Rename the downloaded file to `credentials.json` and place it in the project root directory.
4. **Authorize Folder**: Add the `client_email` from the key to the "Share" list of your Google Drive folder and set as "Editor".

### 2. Configure LINE Messaging API
1. Go to [LINE Developers Console](https://developers.line.biz/) and log in.
2. **Create Provider**: Click "Create a new provider", enter a name (e.g., `MyProjects`), and click "Create".
3. **Create Channel (via Official Account)**:
   - Click "Create a Messaging API channel".
   - The system will prompt that you cannot directly create one; click the **"Create a LINE Official Account"** button.
   - This redirects to the [LINE Official Account Manager](https://manager.line.biz/).
4. **Configure Official Account**:
   - Fill in the account name (e.g., `GDrive Save Bot`) and relevant info, then submit.
   - Once inside the account, click "Settings" on the top right > "Messaging API".
   - Click "Enable Messaging API" and select the **Provider** you just created.
5. **Get Keys & Webhook (Back to Developers Console)**:
   - Return to [LINE Developers Console](https://developers.line.biz/) and refresh.
   - Enter the newly generated Channel.
   - **Basic settings**: Get **Channel secret**.
   - **Messaging API**:
     - **Channel access token**: Click "Issue" to get the Token.
     - **Webhook URL**: Enter your URL + `/webhook/line`.
     - Enable **Use webhook** and click "Update".
6. **Response Settings (Important)**:
   - Return to [Official Account Manager](https://manager.line.biz/).
   - "Settings" > "Response settings".
   - Set "Response mode" to "Chatbot".
   - Under "Detailed settings", set **"Webhook"** to **"Enabled"**.
   - Set "Auto-response messages" and "Greeting messages" to "Disabled".

### 3. Environment Variables
Fill in the information obtained above into the `.env` file. Copy `.env.example` and rename it to `.env`:
```env
# From LINE Developers Console -> Basic settings
LINE_CHANNEL_SECRET=Your_Channel_Secret

# From LINE Developers Console -> Messaging API (Long-lived Token from Issue button)
LINE_CHANNEL_ACCESS_TOKEN=Your_Channel_Access_Token

# From Google Drive Folder URL ID
# XXXXXXXXXX from https://drive.google.com/drive/u/0/folders/XXXXXXXXXX or https://drive.google.com/drive/folders/XXXXXXXXXX
TARGET_DRIVE_FOLDER_ID=XXXXXXXXXX

# Credential Path (Default is credentials.json)
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

### 4. Initialize Environment (Recommended)
This script automatically installs required Python packages and verifies environment variables and API permissions:
```bash
python scripts/check_environment.py
```

### 5. Start Service & Auto Webhook Setup
**Now you only need to run one command to start the Bot and automatically handle network connections:**

1. Ensure your `.env` is set with:
   - `USE_NGROK=true`
   - `NGROK_AUTHTOKEN=Your_Authtoken` (Get it from [ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken))
2. Start the service:
   ```bash
   python -m src.main
   ```
- When the Bot starts, it detects `USE_NGROK`, starts the tunnel, and **automatically updates the Webhook URL in LINE Developers Console**.
- Once you see `✅ [Dev] Webhook URL Updated`, your Bot is ready to receive messages!

### 6. Manual Webhook Setup (Optional)
If you do not want to automatically update the Webhook, set `USE_NGROK` to `false` and configure manually:
1. **Start ngrok**: Run `ngrok http 8000`.
2. **Manual Config**: Paste the ngrok URL into the Webhook URL field in LINE Developers Console and click Update.

## 📝 Usage Instructions

In a LINE chat room:

1. **Save Plain Text**
   ```
   /save Meeting notes for today
   ```

2. **Save Link**
   ```
   /save Important reference link
   https://example.com/article
   ```

3. **Save Image / Video / File**
   - **Method A (Direct Send)**: Send the file/media first, the bot processes it immediately (requires `save_service` configuration).
   - **Method B (Reply Mode)**: Long press the image or file you want to save -> "Reply", and enter `/save [Title]`.
   - The bot will automatically upload the file to Google Drive and insert a download/view link into the corresponding Google Doc.

## �️ Roadmap

- [ ] **Multi-Platform Support**
  - [ ] Support Discord (Adapter & Slash Commands)
  - [ ] Support Telegram
- [ ] **Enhanced Content Handling**
  - [ ] **Rich Text**: Better preservation of Markdown/HTML formatting in Google Docs.
  - [ ] **Voice-to-Text**: Transcribe voice messages directly into the Doc.
- [ ] **System Improvements**
  - [ ] **Multi-User Support**: Allow multiple users to bind their own Google Drive folders.
  - [ ] **Docker Support**: Provide `Dockerfile` and `docker-compose.yml` for easy deployment.

## �🔒 Privacy & Security
- **No Long-Term Data Storage**: The Bot acts only as a relay; it does not save your chat content in a local database.
- **Group Privacy Warning (Important)**: Please **avoid inviting the Bot to large groups**. Since it uses a folder-binding design, any member in the group entering `/save` will push data to your configured Google Drive. To protect your storage space and information security, it is recommended to use it only in 1:1 private messages.
- **Least Privilege**: It is recommended to configure the Service Account with write permissions only for specific folders.

---
*Developed with ❤️ for knowledge management enthusiasts.*
