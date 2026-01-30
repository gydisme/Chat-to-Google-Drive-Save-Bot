import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.services.save_service import SaveService

def test_url_backup():
    print("🧪 Starting URL Backup Verification...")
    
    # Mock GDriveClient
    mock_gdrive = MagicMock()
    mock_gdrive.create_doc.return_value = "https://docs.google.com/mock-doc-link"
    
    service = SaveService(mock_gdrive)
    
    # Test Data
    test_url = "https://example.com"
    platform = "TestPlatform"
    context = "TestContext"
    
    # Run process_save
    print(f"▶️ Processing URL: {test_url}")
    doc_link = service.process_save(
        platform=platform,
        context=context,
        content_type="text",
        text=test_url
    )
    
    # Verify calls
    print("✅ process_save executed.")
    
    # Check what was passed to create_doc
    args, kwargs = mock_gdrive.create_doc.call_args
    title = args[0]
    content_items = args[1]
    
    print(f"📄 Generated Title: {title}")
    
    found_backup = False
    found_hyperlink = False
    
    for item in content_items:
        if isinstance(item, str):
            if "[Comprehensive Content Backup]" in item:
                found_backup = True
                print("✅ Found 'Comprehensive Content Backup' section.")
                if "Example Domain" in item:
                     print("✅ Content scraping successful (found 'Example Domain').")
            if f"- Original Content: {test_url}" in item:
                 found_hyperlink = True
                 print(f"✅ Found Original Content preserved: {item.strip()}")

    if found_backup and found_hyperlink:
        print("🎉 Verification SUCCESS: Logic correctly implements URL backup.")
    else:
        print("❌ Verification FAILED: Missing backup or hyperlink section.")
        for item in content_items:
            print(f"Debug Item: {item}")
        sys.exit(1)

if __name__ == "__main__":
    test_url_backup()
