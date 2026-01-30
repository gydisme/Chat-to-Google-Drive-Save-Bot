
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Mock adapters
from src.services.save_service import SaveService
from src.clients.gdrive_client import GDriveClient

def test_crash():
    print("🚀 Starting crash reproduction test...")
    
    # Initialize
    gdrive = GDriveClient()
    service = SaveService(gdrive)
    
    context = "Debug Context"
    # This URL was in the user's log
    text = "https://github.com/LiveContainer/LiveContainer"
    
    print(f"💾 Processing save for: {text}")
    try:
        doc_link = service.process_save("LINE", context, "text", text=text)
        print(f"✅ Success! Doc Link: {doc_link}")
    except Exception as e:
        print(f"❌ Caught exception: {e}")
    except BaseException as e:
        print(f"❌ Caught BaseException: {e}")

if __name__ == "__main__":
    test_crash()
