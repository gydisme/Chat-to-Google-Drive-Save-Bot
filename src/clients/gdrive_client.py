import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseUpload
import io
import datetime
from typing import Optional, List, Any

class GDriveClient:
    def __init__(self):
        self.creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        self.folder_id = os.getenv('TARGET_DRIVE_FOLDER_ID')
        self.scopes = ['https://www.googleapis.com/auth/drive']
        
        if os.path.exists('token.json'):
            from google.oauth2.credentials import Credentials
            self.creds = Credentials.from_authorized_user_file('token.json', self.scopes)
        else:
            self.creds = service_account.Credentials.from_service_account_file(
                self.creds_path, 
                scopes=self.scopes
            )
        
        # 建立服務
        self.drive_service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
        self.docs_service = build('docs', 'v1', credentials=self.creds, cache_discovery=False)
        
        # Thread lock for API calls to prevent SSL race conditions
        import threading
        self._lock = threading.Lock()

    def upload_file(self, content: bytes, filename: str, mime_type: str) -> str:
        from tqdm import tqdm
        file_metadata = {
            'name': filename,
            'parents': [self.folder_id] if self.folder_id else []
        }
        
        file_size = len(content)
        fh = io.BytesIO(content)
        # 設定明確的 chunksize (1MB) 提高在大檔案上的穩定性
        media = MediaIoBaseUpload(fh, mimetype=mime_type, chunksize=1024*1024, resumable=True)
        
        request = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        )
        
        response = None
        # 使用 tqdm 顯示上傳進度
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"📤 Uploading {filename[:20]}")
        
        try:
            while response is None:
                # 這裡可能發生 SSL 錯誤，加入重試機制
                with self._lock:
                    status, response = request.next_chunk()
                if status:
                    pbar.n = int(status.resumable_progress)
                    pbar.refresh()
            
            pbar.n = file_size
            pbar.refresh()
            pbar.close()
            print(f"✅ [GDrive] 檔案上傳完成: {filename}", flush=True)
            return response.get('webViewLink')
        except Exception as e:
            pbar.close()
            print(f"❌ [GDrive] 上傳失敗: {e}", flush=True)
            raise e

    def create_doc(self, title: str, content_items: list, html_content: Optional[str] = None) -> str:
        """
        Create a new Google Doc with mixed content.
        If html_content is provided, it creates the doc from that HTML (converted),
        and then prepends the content_items.
        """
        # Create a new Google Doc
        with self._lock:
            if html_content:
                file_metadata = {
                    'name': title,
                    'mimeType': 'application/vnd.google-apps.document',
                    'parents': [self.folder_id] if self.folder_id else []
                }
                fh = io.BytesIO(html_content.encode('utf-8'))
                media = MediaIoBaseUpload(fh, mimetype='text/html', resumable=True)
                
                doc = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            else:
                doc = self.drive_service.files().create(
                    body={
                        'name': title,
                        'mimeType': 'application/vnd.google-apps.document',
                        'parents': [self.folder_id] if self.folder_id else []
                    },
                    fields='id'
                ).execute()
        
        doc_id = doc.get('id')
        
        requests = []
        # We process items in reverse order to insert at index 1 effectively, keeping the order correct in the doc.
        # But efficiently, we can just append to the end relative to the current doc length? 
        # Actually, Docs API 'index': 1 pushes existing content down. 
        # So if we insert the last item at index 1, then the second to last at index 1... 
        # The first item will end up at the top.
        # Let's iterate in REVERSE order and always insert at index 1.
        
        for item in reversed(content_items):
            if isinstance(item, str):
                requests.append({
                    'insertText': {
                        'location': {'index': 1},
                        'text': item + "\n"
                    }
                })
            elif isinstance(item, dict):
                if item.get('type') == 'text':
                    text_content = item.get('text', '')
                    if item.get('newline', True):
                        text_content += "\n"
                        
                    requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': text_content
                        }
                    })
                elif item.get('type') == 'link':
                    # Insert Link
                    text_content = item.get('text', '')
                    if item.get('newline', True):
                        text_content_full = text_content + "\n"
                    else:
                        text_content_full = text_content
                        
                    url = item.get('url', '')
                    # Insert the text first
                    requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': text_content_full
                        }
                    })
                    # Apply link style to the text (excluding the newline if present)
                    # The text is at index 1. Length is len(text_content).
                    if url:
                        requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': 1,
                                    'endIndex': 1 + len(text_content)
                                },
                                'textStyle': {
                                    'link': {
                                        'url': url
                                    }
                                },
                                'fields': 'link'
                            }
                        })
                elif item.get('type') in ['heading_1', 'heading_2', 'heading_3']:
                    text_content = item.get('text', '') + "\n"
                    style = item.get('type').upper() # HEADING_1, HEADING_2...
                    
                    requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': text_content
                        }
                    })
                    requests.append({
                        'updateParagraphStyle': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': 1 + len(text_content)
                            },
                            'paragraphStyle': {
                                'namedStyleType': style
                            },
                            'fields': 'namedStyleType'
                        }
                    })

                elif item.get('type') == 'list_item':
                    text_content = item.get('text', '') + "\n"
                    requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': text_content
                        }
                    })
                    requests.append({
                        'createParagraphBullets': {
                            'range': {
                                'startIndex': 1,
                                'endIndex': 1 + len(text_content)
                            },
                            'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                        }
                    })

                elif item.get('type') == 'image':
                    # Insert image
                    uri = item.get('uri')
                    if uri:
                        requests.append({
                            'insertInlineImage': {
                                'location': {'index': 1},
                                'uri': uri,
                                'objectSize': {
                                    'width': {'magnitude': 400, 'unit': 'PT'}
                                }
                            }
                        })
                        requests.append({
                            'insertText': {
                                'location': {'index': 1}, 
                                'text': "\n"
                            }
                        })

        if requests:
            with self._lock:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
        
        # Get the link
        with self._lock:
            file = self.drive_service.files().get(fileId=doc_id, fields='webViewLink').execute()
        return file.get('webViewLink')

    def append_to_doc(self, doc_id: str, content_blocks: list):
        full_text = "\n" + "\n".join(content_blocks)
        requests = [{
            'insertText': {
                'endOfSegmentLocation': {'segmentId': ''},
                'text': full_text
            }
        }]
        with self._lock:
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

    def get_doc_by_name(self, name: str) -> Optional[str]:
        query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.document' and trashed = false"
        if self.folder_id:
            query += f" and '{self.folder_id}' in parents"
        
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        return str(files[0].get('id')) if files else None

