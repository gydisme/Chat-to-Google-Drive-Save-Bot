import os
import re
import json
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, ImageMessage, VideoMessage, FileMessage, TextSendMessage
from concurrent.futures import ThreadPoolExecutor
from ..services.save_service import SaveService

class LineAdapter:
    def __init__(self, save_service: SaveService):
        self.line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
        self.handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
        self.save_service = save_service
        self.auto_save_file = "auto_save_settings.json"
        self._load_auto_save_settings()
        
        # 建立單一執行緒池處理後台任務 (防止 Webhook 逾時與改善回應速度)
        self.executor = ThreadPoolExecutor(max_workers=10) # 增加 worker 數量
        self.queue_count = 0  # 追蹤當前排隊中的任務數

        from linebot.models import StickerMessage, LocationMessage, AudioMessage
        @self.handler.add(MessageEvent, message=(TextMessage, ImageMessage, VideoMessage, FileMessage, StickerMessage, LocationMessage, AudioMessage))
        def handle_message(event):
            self._on_message(event)

    def _load_auto_save_settings(self):
        if os.path.exists(self.auto_save_file):
            with open(self.auto_save_file, 'r') as f:
                self.auto_save_settings = json.load(f)
        else:
            self.auto_save_settings = {}

    def _save_auto_save_settings(self):
        with open(self.auto_save_file, 'w') as f:
            json.dump(self.auto_save_settings, f)

    def handle_request(self, body: str, signature: str):
        # 預先解析原始 Payload 以提取 SDK 可能遺漏的欄位 (如 quotedMessageId)
        try:
            payload = json.loads(body)
            self._temp_quoted_ids = {} # msg_id -> quoted_msg_id
            for event in payload.get('events', []):
                if event.get('type') == 'message':
                    msg = event.get('message', {})
                    msg_id = msg.get('id')
                    quoted_id = msg.get('quotedMessageId')
                    if msg_id and quoted_id:
                        self._temp_quoted_ids[msg_id] = quoted_id
                        print(f"🔧 [Fix] 手動提取 Quoted ID: {quoted_id} for Msg {msg_id}", flush=True)
        except Exception as e:
            print(f"⚠️ [Fix] 預解析失敗: {e}", flush=True)

        self.handler.handle(body, signature)
        
        # 清理 (雖然 handle 是同步的，但為了保險起見)
        self._temp_quoted_ids = {}

    def _on_message(self, event: MessageEvent):
        user_id = event.source.user_id
        context = self._get_context_name(event)
        
        if isinstance(event.message, TextMessage):
            text = event.message.text.strip()
            print(f"📝 收到文字訊息來自 {context}: {text}", flush=True)
            
            # 1. 處理指令 (優先)
            
            # 處理 /auto_save
            if text.startswith('/auto_save'):
                self._handle_auto_save_command(event, text)
                return

            # 處理 /save
            if text.startswith('/save'):
                self._handle_save_command(event, text)
                return

            # 處理 /help
            if text.startswith('/help'):
                self._handle_help_command(event)
                return
            
            # 處理未知指令
            if text.startswith('/'):
                print(f"❓ 收到未知指令: {text}", flush=True)
                return

        # 2. 處理自動備份 (僅限啟用了 auto_save 的 DM)
        user_id = event.source.user_id
        if event.source.type == 'user' and self.auto_save_settings.get(user_id):
            self.queue_count += 1
            
            # 立即回覆告知已進入隊列，並使用引用功能 (quoteToken)
            queue_msg = "📥 已收到媒體，正在排隊處理中..." if not isinstance(event.message, TextMessage) else "📝 已收到文字，正在處理中..."
            
            # 獲取 quoteToken (如果有的話)
            quote_token = getattr(event.message, 'quote_token', None)
            
            # 建立回傳訊息
            msg = TextSendMessage(
                text=f"{queue_msg}\n(當前隊列剩餘: {self.queue_count} 件)",
                quote_token=quote_token
            )
            
            self.line_bot_api.reply_message(event.reply_token, msg)
            
            # 使用執行緒池非同步處理
            print(f"⏩ [Queue] 任務入隊 (Queue Size: {self.queue_count})", flush=True)
            self.executor.submit(self._handle_auto_backup, event)
            return

    def _handle_auto_save_command(self, event: MessageEvent, text: str):
        if event.source.type != 'user':
            self.line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ /auto_save 功能僅限 1:1 私訊使用。")
            )
            return

        user_id = event.source.user_id
        current_state = self.auto_save_settings.get(user_id, False)
        
        # 解析指令內容
        parts = text.split()
        if len(parts) > 1:
            cmd = parts[1].lower()
            if cmd == 'on':
                new_state = True
            elif cmd == 'off':
                new_state = False
            else:
                new_state = not current_state
        else:
            new_state = not current_state

        self.auto_save_settings[user_id] = new_state
        self._save_auto_save_settings()
        
        status_msg = "開啟" if new_state else "關閉"
        self.line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"🔄 Auto-Save 已{status_msg}。")
        )

    def _handle_help_command(self, event: MessageEvent):
        help_text = (
            "📌 可用指令列表：\n\n"
            "1️⃣ /save [標題]\n"
            "   立即儲存當前文字或回覆的媒體。如果是回覆媒體，標題可選。\n\n"
            "2️⃣ /auto_save [on/off]\n"
            "   切換自動儲存模式 (僅限 1:1 私訊)。當開啟時，所有訊息都會被儲存。\n\n"
            "3️⃣ /help\n"
            "   顯示此幫助訊息。"
        )
        self.line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_text)
        )

    def _handle_save_command(self, event: MessageEvent, text: str):
        # 提取標題
        match = re.match(r'^/save\s*(.*)', text)
        user_title = match.group(1).strip() if match else ""
        chat_context = self._get_context_name(event)
        
        try:
            # 偵測回覆 (Debug)
            msg_dict = {}
            if hasattr(event.message, 'as_json_dict'):
                msg_dict = event.message.as_json_dict()
                print(f"🔍 [Debug] Message JSON: {msg_dict}", flush=True)

            quoted_msg_id = getattr(event.message, 'quoted_message_id', None)
            if not quoted_msg_id:
                # 嘗試從 Manual Extraction 找
                if hasattr(self, '_temp_quoted_ids'):
                    quoted_msg_id = self._temp_quoted_ids.get(event.message.id)
            
            if not quoted_msg_id:
                # 嘗試從 message.as_json_dict 找
                if hasattr(event.message, 'as_json_dict'):
                    quoted_msg_id = event.message.as_json_dict().get('quotedMessageId')
            
            if not quoted_msg_id:
                # 最後嘗試從 event.as_json_dict 找 (針對 SDK 解析不完整的情況)
                if hasattr(event, 'as_json_dict'):
                    evt_dict = event.as_json_dict()
                    quoted_msg_id = evt_dict.get('message', {}).get('quotedMessageId')

            if quoted_msg_id:
                print(f"🎯 [Manual-Save] 偵測到回覆儲存 (Quoted ID: {quoted_msg_id})", flush=True)
                self._handle_save_by_id(event, quoted_msg_id, user_title, chat_context)
            else:
                # 處理當前訊息內容 (純文字)
                doc_link = self.save_service.process_save(
                    platform="LINE",
                    context=chat_context,
                    content_type="text",
                    text=user_title or None
                )
                self._reply_success(event.reply_token, doc_link)
        except Exception as e:
            print(f"❌ Error saving: {e}", flush=True)
            self._reply_error(event.reply_token)

    def _handle_auto_backup(self, event: MessageEvent):
        chat_context = self._get_context_name(event)
        user_id = event.source.user_id
        try:
            doc_link = ""
            file_info = ""
            
            if isinstance(event.message, TextMessage):
                doc_link = self.save_service.process_save(
                    platform="LINE",
                    context=chat_context,
                    content_type="text",
                    text=event.message.text
                )
            else:
                # 處理媒體與其他訊息
                doc_link, file_info = self._process_media_message(event, chat_context, user_id)
            
            # 推播處理結果，同樣附上引用
            if doc_link:
                quote_token = getattr(event.message, 'quote_token', None)
                msg = TextSendMessage(
                    text=f"✅ 備份成功！{file_info}\n連結：{doc_link}",
                    quote_token=quote_token
                )
                self.line_bot_api.push_message(user_id, msg)
                
        except Exception as e:
            print(f"❌ Auto-save error: {e}", flush=True)
            self.line_bot_api.push_message(
                user_id,
                TextSendMessage(text=f"❌ 備份失敗，請檢查網路或服務狀態。")
            )
        finally:
            self.queue_count = max(0, self.queue_count - 1)
            print(f"📉 [Queue] 任務完成 (Remaining: {self.queue_count})", flush=True)

    def _process_media_message(self, event: MessageEvent, context: str, user_id: str, custom_title: str = None, msg_id: str = None) -> (str, str):
        """統一處裡媒體內容的下載與儲存，支援直接訊息或回覆訊息"""
        from linebot.models import StickerMessage, LocationMessage, AudioMessage, FileMessage, ImageMessage, VideoMessage
        from tqdm import tqdm
        
        target_msg_id = msg_id or event.message.id
        msg_obj = event.message if not msg_id else None # 如果是回覆，則不知道對象類型
        
        print(f"📦 [Process] 正在處理內容 (ID: {target_msg_id})...", flush=True)
        
        content_bytes = None
        content_type = "file"
        text_content = custom_title
        filename = f"auto_{target_msg_id}"
        file_info = ""
        # 1. 嘗試下載媒體內容
        try:
            resp = self.line_bot_api.get_message_content(target_msg_id)
            
            # 從 Header 偵測 Content-Type (用於解決回覆時不知道類型的問題)
            content_header = ""
            if hasattr(resp, 'headers'):
                content_header = resp.headers.get('Content-Type', '').lower()
            
            if 'image' in content_header: content_type = "image"
            elif 'video' in content_header: content_type = "video"
            elif 'audio' in content_header: content_type = "audio"
            
            # 獲取檔案大小
            total_size = None
            if hasattr(resp, 'headers') and 'Content-Length' in resp.headers:
                total_size = int(resp.headers['Content-Length'])
            elif hasattr(resp, 'content_length'):
                total_size = int(resp.content_length)
            
            if total_size:
                size_mb = round(total_size / (1024 * 1024), 2)
                file_info = f" (大小: {size_mb} MB)"
            
            content_bytes = bytearray()
            pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc=f"📥 Downloading {target_msg_id[:8]}")
            
            try:
                if hasattr(resp, 'iter_content'):
                    last_line_progress = 0
                    downloaded = 0
                    for chunk in resp.iter_content(chunk_size=128*1024):
                        content_bytes.extend(chunk)
                        downloaded += len(chunk)
                        pbar.update(len(chunk))
                        if total_size:
                            progress = int((downloaded / total_size) * 100)
                            if progress >= last_line_progress + 25 and progress < 100:
                                last_line_progress = (progress // 25) * 25
                                try: self.line_bot_api.push_message(user_id, TextSendMessage(text=f"⏳ 下載進度: {last_line_progress}% ..."))
                                except: pass
                else:
                    content_bytes = resp.content
                    if total_size: pbar.update(total_size)
            finally:
                pbar.close()
                if hasattr(resp, 'close'): resp.close()
            
            content_bytes = bytes(content_bytes)

            # 判定類型 (優先使用 Header，如果有 msg_obj 則作為補強)
            if msg_obj:
                if isinstance(msg_obj, ImageMessage): content_type = "image"
                elif isinstance(msg_obj, VideoMessage): content_type = "video"
                elif isinstance(msg_obj, AudioMessage): content_type = "audio"
                elif isinstance(msg_obj, FileMessage):
                    content_type = "file"
                    filename = getattr(msg_obj, 'file_name', filename)
            elif content_type == "file" and 'image' not in content_header and 'video' not in content_header:
                # 如果是回覆且沒偵測到特定類型，嘗試從 SDK 報錯中學習 (這裡通常已經下載完成)
                pass 
            
        except Exception as e:
            # 如果下載失敗且不是媒體訊息，可能是貼圖或位置
            print(f"⚠️ [Process] 無法作為媒體下載: {e}", flush=True)
            if msg_obj and isinstance(msg_obj, StickerMessage):
                content_type = "sticker"
                text_content = f"{custom_title + ': ' if custom_title else ''}Sticker ID: {msg_obj.sticker_id}"
            elif msg_obj and isinstance(msg_obj, LocationMessage):
                content_type = "location"
                text_content = f"{custom_title + ': ' if custom_title else ''}Location: {msg_obj.address}"
            else:
                # 重要：如果既下載失敗又不是已知可處理對象，則不應建立空 Doc
                raise Exception("該訊息類型不支援下載儲存 (或是內容已過期)。")
        
        # 2. 儲存至雲端 (確保有內容可用)
        if not content_bytes and not text_content:
             raise Exception("無效的儲存內容。")
        doc_link = self.save_service.process_save(
            platform="LINE",
            context=context,
            content_type=content_type,
            text=text_content,
            file_content=content_bytes,
            filename=filename
        )
        return doc_link, file_info

    def _handle_save_by_id(self, event: MessageEvent, msg_id: str, title: str, context: str):
        # 使用執行緒池非同步處理
        user_id = event.source.user_id
        
        def task():
            try:
                # 告知處理中 (引用該訊息)
                quote_token = getattr(event.message, 'quote_token', None)
                self.line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text="🚀 正在處理您標記的內容...", quote_token=quote_token)
                )

                doc_link, file_info = self._process_media_message(
                    event=event,
                    context=context,
                    user_id=user_id,
                    custom_title=title,
                    msg_id=msg_id
                )
                
                # 回傳成功
                self.line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=f"✅ 標記儲存成功！{file_info}\n連結：{doc_link}", quote_token=quote_token)
                )
            except Exception as e:
                print(f"❌ Manual save error: {e}", flush=True)
                self.line_bot_api.push_message(
                    user_id, 
                    TextSendMessage(text="❌ 無法儲存該標記內容。提示：目前回覆模式僅支援媒體檔案 (圖片/影片/檔案) 或位置貼圖。如果是文字訊息，請直接轉傳並開啟 /auto_save。")
                )

        self.executor.submit(task)

    def _reply_success(self, reply_token: str, doc_link: str):
        self.line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"✅ 儲存成功！\n文件連結：{doc_link}")
        )

    def _reply_error(self, reply_token: str):
        self.line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="❌ 儲存失敗，請稍後再試。")
        )

    def _get_context_name(self, event: MessageEvent) -> str:
        source_type = event.source.type
        if source_type == 'user':
            try:
                profile = self.line_bot_api.get_profile(event.source.user_id)
                return f"1:1 ({profile.display_name})"
            except:
                return f"1:1 ({event.source.user_id})"
        elif source_type == 'group':
            # This requires the bot to be in the group and have appropriate permissions
            try:
                summary = self.line_bot_api.get_group_summary(event.source.group_id)
                return f"Group ({summary.group_name})"
            except:
                return f"Group ({event.source.group_id})"
        return source_type
