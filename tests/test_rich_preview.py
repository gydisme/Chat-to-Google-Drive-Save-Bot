
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.save_service import SaveService
from src.clients.gdrive_client import GDriveClient

class TestRichPreview(unittest.TestCase):
    def setUp(self):
        self.mock_gdrive = MagicMock(spec=GDriveClient)
        self.service = SaveService(self.mock_gdrive)

    @patch('src.services.save_service.requests.get')
    def test_link_expansion(self, mock_get):
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <meta property="og:title" content="Test Page Title" />
                <meta property="og:description" content="This is a test description." />
                <meta property="og:image" content="http://example.com/image.jpg" />
                <title>Fallback Title</title>
            </head>
            <body></body>
        </html>
        """
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        # Execute
        context = "Test Context"
        text = "https://example.com/article"
        self.service.process_save("LINE", context, "text", text=text)

        # Verify
        self.mock_gdrive.create_doc.assert_called_once()
        args, _ = self.mock_gdrive.create_doc.call_args
        title = args[0]
        content = args[1]

        # Check content structure
        print("\nGenerated Content Items:")
        for item in content:
            print(item)

        # Assertions
        self.assertTrue(any("Test Page Title" in item for item in content if isinstance(item, str)))
        self.assertTrue(any("This is a test description" in item for item in content if isinstance(item, str)))
        
        # Check image item
        image_item = next((item for item in content if isinstance(item, dict) and item.get('type') == 'image'), None)
        self.assertIsNotNone(image_item)
        self.assertEqual(image_item['uri'], "http://example.com/image.jpg")

    @patch('src.services.save_service.requests.get')
    def test_link_expansion_no_image(self, mock_get):
         # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <meta property="og:title" content="No Image Title" />
            </head>
        </html>
        """
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        self.service.process_save("LINE", "Context", "text", text="http://noimage.com")
        
        args, _ = self.mock_gdrive.create_doc.call_args
        content = args[1]
        
        self.assertTrue(any("No Image Title" in item for item in content if isinstance(item, str)))
        # Ensure NO image item
        image_item = next((item for item in content if isinstance(item, dict) and item.get('type') == 'image'), None)
        self.assertIsNone(image_item)

if __name__ == '__main__':
    unittest.main()
