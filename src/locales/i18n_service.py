import json
import os
from typing import Dict, Any, Optional

class I18nService:
    _instance: Any = None
    default_lang: str = 'zh-TW'
    locales: Dict[str, Dict[str, str]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(I18nService, cls).__new__(cls)
            cls._instance.load_locales()
        return cls._instance

    def load_locales(self):
        self.default_lang = os.getenv('DEFAULT_LANGUAGE', 'zh-TW') or 'zh-TW'
        self.locales = {}
        
        # Load from JSON file relative to this script
        base_path = os.path.dirname(__file__)
        file_path = os.path.join(base_path, 'strings.json')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.locales = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load locales: {e}")
            self.locales = {}

    def get(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        target_lang = lang or self.default_lang
        
        # Fallback to default if target not found
        if target_lang not in self.locales:
            target_lang = self.default_lang
            
        # Fallback to 'en' if default not found
        if target_lang not in self.locales:
            target_lang = 'en'
            
        lang_dict = self.locales.get(target_lang, {})
        text_template = lang_dict.get(key, key) # Return key if not found
        
        try:
            return text_template.format(**kwargs)
        except KeyError:
            return text_template

# Global instance
i18n = I18nService()

def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    return i18n.get(key, lang, **kwargs)
