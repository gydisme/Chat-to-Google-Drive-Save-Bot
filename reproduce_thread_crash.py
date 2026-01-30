
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

from src.services.save_service import SaveService
from src.clients.gdrive_client import GDriveClient

def worker(service, i):
    print(f"🧵 Worker {i} starting...")
    text = "https://github.com/LiveContainer/LiveContainer"
    try:
        doc_link = service.process_save("TEST", f"Context-{i}", "text", text=text)
        print(f"✅ Worker {i} Success: {doc_link}")
    except Exception as e:
        print(f"❌ Worker {i} Failed: {e}")

def test_concurrent_crash():
    print("🚀 Starting concurrent crash test...")
    gdrive = GDriveClient()
    service = SaveService(gdrive)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in range(5):
            executor.submit(worker, service, i)
            
    print("🏁 All Done.")

if __name__ == "__main__":
    test_concurrent_crash()
