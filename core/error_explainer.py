# -*- coding: utf-8 -*-
"""
Error Explainer Module

Analyzes batch translation errors and produces user-friendly summaries and actionable suggestions.
"""

import re

class ErrorExplainer:
    """
    Analyzes raw error messages/objects and returns a structured summary.
    """
    
    # Categories
    CAT_AUTH = "AUTH"
    CAT_RATE_LIMIT = "RATE_LIMIT"
    CAT_NETWORK = "NETWORK"
    CAT_SERVER = "SERVER"
    CAT_INVALID = "INVALID_REQUEST"
    CAT_EMPTY = "EMPTY_RESPONSE"
    CAT_UNKNOWN = "UNKNOWN"

    @classmethod
    def analyze(cls, errors: list) -> dict:
        """
        Analyze a list of errors and return the most significant one summary.
        
        Args:
            errors: List of error strings or objects
            
        Returns:
            dict: {
                'category': str,
                'title': str,
                'message': str,
                'suggestions': list[str],
                'raw_sample': str,
                'status_code': int|None,
                'provider': str|None
            }
        """
        if not errors:
            return None
            
        # Prioritize errors: Auth > Rate Limit > Network > Server
        # We scan all errors and pick the "highest priority" category to report.
        
        best_candidate = None
        best_priority = -1 # Higher is better
        
        # Priority map
        PRIORITY = {
            cls.CAT_AUTH: 100,
            cls.CAT_RATE_LIMIT: 90,
            cls.CAT_NETWORK: 80,
            cls.CAT_SERVER: 70,
            cls.CAT_INVALID: 60,
            cls.CAT_EMPTY: 50,
            cls.CAT_UNKNOWN: 0
        }
        
        for err in errors:
            err_obj = err
            err_str = err
            
            if isinstance(err, dict):
                err_str = err.get('message', '')
            elif not isinstance(err, str):
                err_str = str(err)
            
            # Skip empty errors
            if not err_str:
                continue
                
            cat, code, provider = cls._classify_single(err_str)
            prio = PRIORITY.get(cat, 0)
            
            if prio > best_priority:
                best_priority = prio
                best_candidate = (cat, code, provider, err_obj)
                
        if not best_candidate:
            return cls._build_summary(cls.CAT_UNKNOWN, None, None, str(errors[0]))
            
        cat, code, provider, raw_err = best_candidate
        return cls._build_summary(cat, code, provider, raw_err)

    @classmethod
    def _classify_single(cls, error_str: str):
        """Classify a single error string into a category."""
        error_lower = error_str.lower()
        
        # 1. Extract Status Code (e.g. "401 Unauthorized" or "code=429")
        status_code = None
        match = re.search(r'\b(401|403|429|500|502|503|504|400)\b', error_str)
        if match:
            status_code = int(match.group(1))
            
        # 2. Extract Provider (heuristic)
        provider = None
        if "gemini" in error_lower:
            provider = "Gemini"
        elif "google" in error_lower:
            provider = "Google Translate"
        elif "openai" in error_lower or "gpt" in error_lower:
            provider = "OpenAI"
            
        # 3. Determine Category
        category = cls.CAT_UNKNOWN
        
        # Auth
        if status_code in [401, 403] or any(k in error_lower for k in ["invalid api key", "unauthorized", "permission denied", "api key not found"]):
            category = cls.CAT_AUTH
                
        # Rate Limit
        elif status_code == 429 or any(k in error_lower for k in ["rate limit", "too many requests", "resource exhausted", "quota exceeded"]):
            category = cls.CAT_RATE_LIMIT
            
        # Network
        elif any(k in error_lower for k in ["timeout", "connection", "dns", "unreachable", "network", "socket", "eof"]):
            category = cls.CAT_NETWORK
            
        # Server
        elif status_code in [500, 502, 503, 504] or any(k in error_lower for k in ["internal server error", "service unavailable", "bad gateway"]):
            category = cls.CAT_SERVER
            
        # Empty / No Result
        elif any(k in error_lower for k in ["empty result", "empty response", "returned empty", "no candidates", "none result"]):
            category = cls.CAT_EMPTY
            
        # Invalid
        elif status_code == 400 or any(k in error_lower for k in ["bad request", "invalid argument", "model not found", "not supported"]):
            category = cls.CAT_INVALID
            
        return category, status_code, provider

    @classmethod
    def _build_summary(cls, category, code, provider, raw_sample):
        """Construct the localized summary dict."""
        
        ctx = f" ({provider})" if provider else ""
        code_str = f" [Kod: {code}]" if code else ""
        
        # Handle structured raw sample
        row_id = None
        file_line = None
        
        if isinstance(raw_sample, dict):
            row_id = raw_sample.get('row_id')
            file_line = raw_sample.get('file_line')
            raw_sample_text = raw_sample.get('message', str(raw_sample))
            # Append code if present
            if raw_sample.get('code'):
                raw_sample_text += f" (Code: {raw_sample.get('code')})"
        else:
            raw_sample_text = str(raw_sample)
            # Try to extract line number from string if not provided
            # e.g. "Line 151: Error..."
            if file_line is None:
                match = re.search(r'Line (\d+)', raw_sample_text)
                if match:
                    file_line = int(match.group(1))

        summary = {
            'category': category,
            'title': "Bilinmeyen Hata",
            'message': f"Toplu çeviri sırasında beklenmedik bir hata oluştu.{ctx}",
            'suggestions': ["Log sekmesindeki detayları inceleyin.", "İşlemi tekrar deneyin."],
            'raw_sample': raw_sample_text,
            'status_code': code,
            'provider': provider,
            'row_id': row_id,
            'file_line': file_line
        }
        
        if category == cls.CAT_AUTH:
            summary['title'] = "Kimlik Doğrulama Hatası"
            summary['message'] = f"API anahtarınız geçersiz veya yetkiniz yok.{ctx}{code_str}"
            summary['suggestions'] = [
                "Ayarlar > API Anahtarı menüsünü kontrol edin.",
                "Anahtarın doğru kopyalandığından ve boşluk içermediğinden emin olun.",
                "Servis sağlayıcı kotanızın bitip bitmediğini kontrol edin."
            ]
            
        elif category == cls.CAT_RATE_LIMIT:
            summary['title'] = "İstek Sınırı Aşıldı (Rate Limit)"
            summary['message'] = f"Çok fazla istek gönderildiği için servis yanıt vermiyor.{ctx}{code_str}"
            summary['suggestions'] = [
                "Bir süre (1-2 dakika) bekleyip 'Hatalıları Yeniden Dene' butonuna basın.",
                "Ayarlardan çeviri hızını düşürmeyi deneyin (varsa).",
                "Daha yüksek kotalı bir model veya API anahtarı kullanın."
            ]
            
        elif category == cls.CAT_NETWORK:
            summary['title'] = "Ağ Bağlantı Hatası"
            summary['message'] = f"İnternet bağlantınız koptu veya sunucuya ulaşılamıyor.{ctx}"
            summary['suggestions'] = [
                "İnternet bağlantınızı kontrol edin.",
                "VPN veya Proxy kullanıyorsanız ayarlarını gözden geçirin.",
                "Kısa bir süre bekleyip tekrar deneyin."
            ]
            
        elif category == cls.CAT_SERVER:
            summary['title'] = "Sunucu Hatası"
            summary['message'] = f"Karşı sunucuda geçici bir sorun oluştu.{ctx}{code_str}"
            summary['suggestions'] = [
                "Bu genellikle geçici bir durumdur.",
                "Birkaç dakika bekleyip işlemi tekrarlayın.",
                "Sorun devam ederse model veya sağlayıcı değiştirmeyi deneyin."
            ]
            
        elif category == cls.CAT_EMPTY:
            summary['title'] = "Boş Sonuç Döndü"
            summary['message'] = f"Model geçerli bir yanıt üretemedi (boş içerik).{ctx}"
            summary['suggestions'] = [
                "Satır çok kısa veya tek kelime olabilir; tekrar deneyin.",
                "Farklı bir model deneyin.",
                "Chunk boyutunu düşürmeyi deneyin."
            ]
            
        elif category == cls.CAT_INVALID:
            summary['title'] = "Geçersiz İstek"
            summary['message'] = f"Gönderilen veriler veya model adı kabul edilmedi.{ctx}{code_str}"
            summary['suggestions'] = [
                "Seçili modelin adını ayarlardan kontrol edin.",
                "Çevrilen metinlerde çok uzun veya bozuk karakterler olabilir.",
                "Farklı bir model seçmeyi deneyin."
            ]
            
        return summary
