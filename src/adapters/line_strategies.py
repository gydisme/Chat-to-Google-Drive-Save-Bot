import re
from linebot.models import TextSendMessage
from ..commands.abstraction import Command, CommandContext
from ..locales.i18n_service import t

class LineHelpCommand(Command):
    def match(self, text: str) -> bool:
        return text.startswith('/help')

    def execute(self, context: CommandContext) -> None:
        help_text = t("help_text")
        context.adapter.reply_message(
            context.event.reply_token,
            TextSendMessage(text=help_text)
        )

class LineAutoSaveCommand(Command):
    def match(self, text: str) -> bool:
        return text.startswith('/auto_save')

    def execute(self, context: CommandContext) -> None:
        event = context.event
        adapter = context.adapter
        text = context.message_text

        if event.source.type != 'user':
            adapter.reply_message(
                event.reply_token,
                TextSendMessage(text=t("auto_save_dm_only"))
            )
            return

        user_id = event.source.user_id
        current_state = adapter.auto_save_settings.get(user_id, False)
        
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

        adapter.auto_save_settings[user_id] = new_state
        adapter.save_auto_save_settings()
        
        status_key = "auto_save_on" if new_state else "auto_save_off"
        status_msg = t(status_key)
        adapter.reply_message(
            event.reply_token,
            TextSendMessage(text=t("auto_save_status", status=status_msg))
        )

class LineSaveCommand(Command):
    def match(self, text: str) -> bool:
        return text.startswith('/save')

    def execute(self, context: CommandContext) -> None:
        event = context.event
        adapter = context.adapter
        text = context.message_text
        
        # 提取標題
        match = re.match(r'^/save\s*(.*)', text)
        user_title = match.group(1).strip() if match else ""
        chat_context = adapter.get_context_name(event)
        
        try:
            # 偵測回覆 (Refactored logic to use adapter methods if needed, but logic is mostly inspecting event)
            quoted_msg_id = getattr(event.message, 'quoted_message_id', None)
            
            # 嘗試從 Manual Extraction 找 (accessing protected member via public property or friend class assumption)
            # In python protected is just convention. We'll access it directly or via accessor.
            # Assuming adapter has `get_quoted_msg_id` or exposes `_temp_quoted_ids`
            if not quoted_msg_id:
                quoted_msg_id = adapter.get_manual_quoted_id(event.message.id)
            
            if not quoted_msg_id:
                if hasattr(event.message, 'as_json_dict'):
                    quoted_msg_id = event.message.as_json_dict().get('quotedMessageId')
            
            if not quoted_msg_id:
                if hasattr(event, 'as_json_dict'):
                    evt_dict = event.as_json_dict()
                    quoted_msg_id = evt_dict.get('message', {}).get('quotedMessageId')

            if quoted_msg_id:
                print(f"🎯 [Manual-Save] 偵測到回覆儲存 (Quoted ID: {quoted_msg_id})", flush=True)
                adapter.handle_save_by_id(event, quoted_msg_id, user_title, chat_context)
            else:
                # 處理當前訊息內容 (純文字)
                doc_link = adapter.save_service.process_save(
                    platform="LINE",
                    context=chat_context,
                    content_type="text",
                    text=user_title or None
                )
                adapter.reply_message(
                    event.reply_token,
                    TextSendMessage(text=t("save_success", link=doc_link))
                )
        except Exception as e:
            print(f"❌ Error saving: {e}", flush=True)
            adapter.reply_message(
                event.reply_token,
                TextSendMessage(text=t("save_error"))
            )
