import datetime
import requests
import re
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any, Union
from ..clients.gdrive_client import GDriveClient

class SaveService:
    def __init__(self, gdrive_client: GDriveClient):
        self.gdrive = gdrive_client

    def generate_title(self, user_text: Optional[str], content_type: str) -> str:
        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d_%H%M")
        
        # 處理不同類型的類型標籤
        type_tag = content_type.capitalize()
        if content_type == "text":
            type_tag = "Doc"
        elif content_type == "file":
            type_tag = "File"
            
        if user_text:
            # 去除字串中不適合做檔名的字元，並限長度
            clean_text = re.sub(r'[\\/*?:"<>|]', "", user_text).strip()[:30]
            return f"{date_str}_{type_tag}_{clean_text}"
        
        return f"{date_str}_{type_tag}_備份"

    def process_save(self, 
                    platform: str, 
                    context: str, 
                    content_type: str, 
                    text: Optional[str] = None, 
                    file_content: Optional[bytes] = None, 
                    filename: Optional[str] = None) -> str:
        
        print(f"💾 [Service] 正在處理儲存請求: Type={content_type}, Context={context}", flush=True)
        
        # 1. 抽出所有 URL
        urls = []
        if text:
            # Simple regex for http/https URLs
            urls = re.findall(r'https?://[^\s]+', text)
            # Unique URLs while preserving order
            urls = list(dict.fromkeys(urls))

        # 2. 抓取備份 (多個 URL)
        url_backups = []
        for url in urls:
            print(f"🔍 [Service] 發現網址，正在抓取備份: {url[:30]}...", flush=True)
            meta = self._fetch_url_content(url)
            if meta.get("title"):
                print(f"🔗 [Service] 備份成功: {meta['title'][:30]}...", flush=True)
                # Store full URL for linking
                meta['original_url'] = url
                url_backups.append(meta)

        timestamp = datetime.datetime.now().isoformat()
        
        # Title logic: Use first URL title if available and no user text (or if text IS the url)
        generated_title_base = None
        if content_type == "text":
            # If text is basically just one URL, use its title
            if len(urls) == 1 and text.strip() == urls[0]:
                generated_title_base = url_backups[0].get("title") if url_backups else None
            else:
                generated_title_base = text

        title = self.generate_title(generated_title_base, content_type)
        
        # Build structured content items
        content_items: List[Union[str, Dict[str, Any]]] = []
        
        metadata_text = (
            f"Title: {title}\n\n"
            f"Source:\n"
            f"- Platform: {platform}\n"
            f"- Chat Context: {context}\n"
            f"- Timestamp: {timestamp}\n\n"
            f"Content:"
        )
        content_items.append(metadata_text)
        
        if text:
            content_items.append("- Original Content: ")
            
            # Smart Split for Mixed Content
            # We want to reconstruct the text but make URLs clickable.
            # Split by URLs capturing the delimiter
            parts = re.split(r'(https?://[^\s]+)', text)
            
            # We need to construct a list of items that form the paragraph.
            # GDriveClient processes items in REVERSE order and inserts at index 1.
            # So to get "A Link B", we must append [A, Link, B] to content_items in that order?
            # Wait, my GDriveClient iterates REVERSE.
            # List: [Item1, Item2, Item3]
            # Iteration: Item3 -> Insert at 1. Doc: [Item3]
            # Item2 -> Insert at 1. Doc: [Item2, Item3]
            # Item1 -> Insert at 1. Doc: [Item1, Item2, Item3]
            # So I should append items in READING ORDER.
            
            # HOWEVER, each item usually forces a newline in current GDriveClient.
            # I need to modify GDriveClient to support inline. 
            # Im saving that for step 2 of this request. 
            # For now, I will use a safe fallback: List them as blocks if possible, or just one block if not.
            # Actually, to support "Multiple Links", I will just list them.
            # But the requirement is "Original Content" has links.
            
            # For this step, I will assume GDriveClient will be updated to support 'newline': False.
            
            paragraph_items = []
            for part in parts:
                if not part: continue
                if part in urls:
                    paragraph_items.append({"type": "link", "text": part, "url": part, "newline": False})
                else:
                    paragraph_items.append({"type": "text", "text": part, "newline": False})
            
            # Add a newline at the end of the paragraph
            if paragraph_items:
                paragraph_items[-1]['newline'] = True
                
            content_items.extend(paragraph_items)

        # 3. Aggregation Strategy: HTML vs Standard
        combined_html = ""
        has_html_backup = False
        
        # Check if we have HTML content to use
        html_chunks = [meta['html_content'] for meta in url_backups if meta.get('html_content')]
        if html_chunks:
            has_html_backup = True
            # Build a simple HTML wrapper
            combined_html = "<html><body>"
            for i, chunk in enumerate(html_chunks):
                if i > 0: combined_html += "<br><hr><br>" # Separator
                combined_html += chunk
            combined_html += "</body></html>"
        
        # If we have HTML backup, we don't need to append backup text to content_items
        # But we still want to append Metadata and Link context at the TOP (which content_items does via create_doc)
        
        if not has_html_backup and url_backups:
             # Fallback to appending details if no HTML (or if failed)
            content_items.append("\n[Comprehensive Content Backup]\n")
            
            for meta in url_backups:
                # Title as Link
                content_items.append({"type": "link", "text": f"Title: {meta['title']}", "url": meta['original_url']})
                
                details = ""
                if meta.get("description"):
                    details += f"Description: {meta['description']}\n"
                
                content_items.append(details)
                
                if meta.get("image"):
                    content_items.append({"type": "image", "uri": meta["image"]})
                
                content_items.append("\n") # Spacer between backups

        file_link = None
        if file_content:
            # 使用產生的 title 作為檔案名稱的主體，並保留副檔名
            ext = ""
            if filename and "." in filename:
                ext = "." + filename.split(".")[-1]
            elif content_type == "image": ext = ".jpg"
            elif content_type == "video": ext = ".mp4"
            elif content_type == "audio": ext = ".m4a"
            
            target_filename = f"{title}{ext}"
            
            # Upload media file first
            mime_type = self._get_mime_type(content_type, filename)
            file_link = self.gdrive.upload_file(file_content, target_filename, mime_type)
            content_items.append(f"- GDrive File Link: {file_link}")

        # 優化：如果是純媒體檔案（沒有額外描述），直接回傳檔案連結，不建立 Doc
        if file_link and not text:
            print(f"📄 [Service] 偵測為純媒體檔案，跳過建立 Google Doc。", flush=True)
            return file_link

        # Determine strategy: New Doc
        # Pass html_content if available
        doc_link = self.gdrive.create_doc(title, content_items, html_content=combined_html if has_html_backup else None)
        return doc_link

    def _fetch_url_content(self, url: str) -> Dict[str, Any]:
        """嘗試抓取網址的 Title, Description, Image 以及完整的 HTML 內容 (用於原生轉換)"""
        summary = {"title": "", "description": "", "image": "", "html_content": ""}
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = response.apparent_encoding
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Title
                og_title = soup.find("meta", property="og:title")
                summary["title"] = og_title["content"] if og_title else (soup.title.string.strip() if soup.title else "")
                
                # Description
                og_desc = soup.find("meta", property="og:description")
                summary["description"] = og_desc["content"] if og_desc else ""
                
                # Image
                og_image = soup.find("meta", property="og:image")
                content = og_image.get("content") if og_image else ""
                if content and not content.startswith("http"):
                    from urllib.parse import urljoin
                    content = urljoin(url, content)
                summary["image"] = content
                
                # Cleanup for HTML Conversion
                # We want to keep formatting (tables, bold, etc) but remove junk.
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "aside"]):
                    tag.decompose()
                
                # Isolate Main Content
                main_content = soup.find('main') or soup.find('article') or soup.body
                
                if main_content:
                    # Simplify some attributes to avoid import errors or weird formatting
                    for tag in main_content.find_all(True):
                        # Remove event handlers
                        attrs = dict(tag.attrs)
                        for attr in attrs:
                            if attr.startswith('on'):
                                del tag.attrs[attr]
                                
                    summary["html_content"] = str(main_content)
                else:
                    summary["html_content"] = "<div>No main content found</div>"
                
                return summary
        except Exception as e:
            print(f"⚠️ [Service] 抓取網址備份失敗: {e}", flush=True)
        return summary

    def _get_mime_type(self, content_type: str, filename: Optional[str]) -> str:
        if content_type == "image":
            return "image/jpeg"
        if content_type == "video":
            return "video/mp4"
        return "application/octet-stream"
