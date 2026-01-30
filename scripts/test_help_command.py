import os
from unittest.mock import MagicMock
from src.adapters.line_adapter import LineAdapter
from linebot.models import MessageEvent, TextMessage, TextSendMessage

def test_help_command():
    # Mock SaveService
    mock_save_service = MagicMock()
    
    # Mock LineBotApi
    os.environ['LINE_CHANNEL_ACCESS_TOKEN'] = 'fake_token'
    os.environ['LINE_CHANNEL_SECRET'] = 'fake_secret'
    
    adapter = LineAdapter(mock_save_service)
    adapter.line_bot_api = MagicMock()
    
    # Create a mock event
    event = MagicMock()
    event.reply_token = 'test_reply_token'
    event.message = MagicMock(spec=TextMessage)
    event.message.text = '/help'
    event.source.type = 'user'
    event.source.user_id = 'user123'
    
    # Trigger message handler
    adapter._on_message(event)
    
    # Verify reply_message was called with help text
    adapter.line_bot_api.reply_message.assert_called_once()
    args, kwargs = adapter.line_bot_api.reply_message.call_args
    
    reply_token = args[0]
    message_obj = args[1]
    
    assert reply_token == 'test_reply_token'
    assert isinstance(message_obj, TextSendMessage)
    assert "可用指令列表" in message_obj.text
    print("Test passed: /help command triggers correctly.")

if __name__ == "__main__":
    test_help_command()
