# -*- coding: utf-8 -*-
"""
RenForge Localization Module
Supports Turkish and English UI languages.
"""

SUPPORTED_UI_LANGUAGES = {
    "tr": "Türkçe",
    "en": "English"
}

DEFAULT_UI_LANGUAGE = "tr"
_current_language = DEFAULT_UI_LANGUAGE


def set_language(lang_code: str):
    """Set the current UI language."""
    global _current_language
    if lang_code in SUPPORTED_UI_LANGUAGES:
        _current_language = lang_code
        print(f"UI language set to: {lang_code}")
    else:
        print(f"Warning: Unsupported language code '{lang_code}'. Using default.")


def get_language() -> str:
    """Get the current UI language code."""
    return _current_language


def tr(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.
    
    Args:
        key: Translation key
        **kwargs: Format parameters for the translated string
        
    Returns:
        Translated string, or the key itself if not found
    """
    translations = TRANSLATIONS.get(_current_language, TRANSLATIONS.get("en", {}))
    text = translations.get(key, key)
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            print(f"Warning: Missing format key {e} for translation '{key}'")
    
    return text


# =============================================================================
# TRANSLATIONS DICTIONARY
# =============================================================================

TRANSLATIONS = {
    "tr": {
        # ---------------------------------------------------------------------
        # GENEL / ORTAK
        # ---------------------------------------------------------------------
        "ready": "Hazır",
        "error": "Hata",
        "warning": "Uyarı",
        "info": "Bilgi",
        "success": "Başarılı",
        "cancel": "İptal",
        "ok": "Tamam",
        "yes": "Evet",
        "no": "Hayır",
        "save": "Kaydet",
        "close": "Kapat",
        "apply": "Uygula",
        "delete": "Sil",
        "edit": "Düzenle",
        "open": "Aç",
        "file": "Dosya",
        "project": "Proje",
        "settings": "Ayarlar",
        "about": "Hakkında",
        "help": "Yardım",
        "exit": "Çıkış",
        "loading": "Yükleniyor...",
        "saving": "Kaydediliyor...",
        "processing": "İşleniyor...",
        
        # ---------------------------------------------------------------------
        # ANA PENCERE
        # ---------------------------------------------------------------------
        "window_title": "RenForge - Ren'Py betik düzenleyici v{version}",
        "no_open_files": "Açık dosya yok",
        "active_tab_data_error": "Aktif sekme veri hatası",
        
        # Menü - Dosya
        "menu_file": "&Dosya",
        "menu_open_project": "&Proje Aç...",
        "menu_open_file": "&Dosya Aç...",
        "menu_save": "&Kaydet",
        "menu_save_as": "Farklı &Kaydet...",
        "menu_save_all": "&Tümünü Kaydet",
        "menu_close_tab": "Sekmeyi &Kapat",
        "menu_exit": "&Çıkış",
        
        # Menü - Düzenle
        "menu_edit": "&Düzenle",
        "menu_revert_item": "Öğeyi &Geri Al",
        "menu_revert_selected": "&Seçilenleri Geri Al",
        "menu_revert_all": "&Tümünü Geri Al",
        "menu_insert_line": "Satır &Ekle (Direct)",
        "menu_delete_line": "Satır &Sil (Direct)",
        
        # Menü - Çeviri
        "menu_translate": "Çe&viri",
        "menu_translate_google": "&Google Translate ile Çevir",
        "menu_batch_translate": "&Toplu Google Translate",
        "menu_edit_ai": "&AI ile Düzenle (Gemini)",
        "menu_batch_ai": "Toplu &AI Çeviri",
        
        # Menü - Navigasyon
        "menu_navigation": "&Gezinme",
        "menu_prev_item": "&Önceki Öğe",
        "menu_next_item": "&Sonraki Öğe",
        "menu_toggle_breakpoint": "&İşaretçi Ekle/Kaldır",
        "menu_next_breakpoint": "Sonraki İşaretçi&ye Git",
        "menu_clear_breakpoints": "Tüm &İşaretçileri Temizle",
        "menu_find_next": "&Sonrakini Bul",
        "menu_replace": "&Değiştir",
        "menu_replace_all": "Tümünü De&ğiştir",
        
        # Menü - Görünüm
        "menu_view": "&Görünüm",
        "menu_toggle_project_panel": "&Proje Paneli",
        
        # Menü - Ayarlar
        "menu_settings": "A&yarlar",
        "menu_main_settings": "&Ana Ayarlar...",
        "menu_api_key": "&API Anahtarı Ayarla...",
        "menu_refresh_models": "&Model Listesini Yenile",
        
        # Menü - Yardım
        "menu_help": "&Yardım",
        "menu_about": "&Hakkında",
        
        # Araç Çubuğu
        "toolbar_mode": "Mod:",
        "toolbar_source": "Kaynak:",
        "toolbar_target": "Hedef:",
        "toolbar_model": "Gemini Model:",
        "toolbar_find": "Bul:",
        "toolbar_replace_with": "İle değiştir:",
        "toolbar_search_placeholder": "Aranacak metin",
        "toolbar_replace_placeholder": "Değiştirilecek metin",
        "toolbar_regex": "Regex",
        "toolbar_case_sensitive": "Büyük/Küçük Harf",
        
        # Butonlar
        "btn_find_next": "Sonrakini Bul",
        "btn_replace": "Değiştir",
        "btn_replace_all": "Tümünü Değiştir",
        "btn_prev": "◄ Önceki",
        "btn_next": "Sonraki ►",
        "btn_google_translate": "Google Çevir",
        "btn_batch_translate": "Toplu Çevir",
        "btn_ai_edit": "AI Düzenle",
        "btn_batch_ai": "Toplu AI",
        
        # Durum Çubuğu
        "status_no_open_files": "Açık dosya yok",
        "status_project": "Proje: {name}",
        "status_file": "Dosya: {name}",
        "status_mode": "Mod: {mode}",
        "status_mode_direct": "Doğrudan",
        "status_mode_translate": "Çeviri",
        "status_mode_unknown": "Bilinmiyor",
        "status_items": "Öğeler: {count}",
        "status_selected": "Seçili: {current}/{total}",
        "status_line": "(Satır {num})",
        "status_character": "Karakter: {tag}",
        "status_type": "Tip: {type}",
        "status_marker": "İŞARET",
        "status_modified": "DEĞİŞTİRİLDİ",
        "status_no_selection": "(Seçim yok)",
        "status_no_internet": "İnternet bağlantısı yok.",
        
        # ---------------------------------------------------------------------
        # DOSYA İŞLEMLERİ
        # ---------------------------------------------------------------------
        "file_opening_cancelled": "Dosya açma iptal edildi.",
        "file_opening_cancelled_mode": "Dosya açma iptal edildi. Mod ayarı seçilmeli.",
        "project_opening_cancelled": "Proje açma iptal edildi.",
        "project_opened": "Proje açıldı: {name}",
        "preparing_project": "Proje dosyaları hazırlanıyor (rpa/rpyc)... Lütfen bekleyin.",
        "project_prep_errors": "Proje hazırlama hata/uyarı ile tamamlandı.",
        "project_prep_success": "Proje dosya hazırlama başarıyla tamamlandı.",
        "project_prep_skipped": "Otomatik hazırlama atlandı (ayarlarda kapalı).",
        "project_prep_error": "Proje dosya hazırlama hatası: {error}",
        "auto_prep_disabled": "Otomatik hazırlama ayarlarda kapalı.",
        
        "loading_file": "{name} yükleniyor ({mode})...",
        "file_loaded": "{name} dosyası yüklendi ({count} öğe). Mod: '{mode}'.",
        "error_loading_file": "{name} yüklenirken hata: {error}",
        
        "no_active_tab_save": "Kaydedilecek aktif sekme yok.",
        "saving_file": "{name} kaydediliyor...",
        "file_saved": "Dosya kaydedildi: {path}",
        "file_save_error": "Dosya kaydetme hatası: {error}",
        "no_unsaved_files": "Kaydedilecek değişiklik yok.",
        "all_files_saved": "Tüm değişiklikler kaydedildi.",
        "save_all_errors": "{failed}/{total} dosya kaydedilemedi.",
        
        # Dosya Dialogları
        "dialog_open_project": "Proje Klasörü Seç",
        "dialog_open_file": "Ren'Py Dosyası Aç",
        "dialog_save_as": "Farklı Kaydet",
        "rpy_files": "Ren'Py Dosyaları",
        "all_files": "Tüm Dosyalar",
        
        # ---------------------------------------------------------------------
        # SEKME YÖNETİMİ
        # ---------------------------------------------------------------------
        "no_active_tab_close": "Kapatılacak aktif sekme yok.",
        "tab_close_cancelled": "Sekme kapatma iptal edildi.",
        "tab_save_failed": "Kaydetme başarısız. Sekme kapatma iptal edildi.",
        
        # Kaydedilmemiş Değişiklikler Dialogu
        "unsaved_changes_title": "Kaydedilmemiş Değişiklikler",
        "unsaved_changes_message": "'{name}' dosyasında kaydedilmemiş değişiklikler var.\nNe yapmak istersiniz?",
        "unsaved_changes_exit": "Kaydedilmemiş değişiklikler içeren açık dosyalar var.\nNe yapmak istersiniz?",
        "btn_save_all": "Tümünü Kaydet",
        "btn_exit_without_saving": "Kaydetmeden Çık",
        "exit_cancelled": "Çıkış iptal edildi.",
        "save_failed_exit_cancelled": "Tüm dosyalar kaydedilemedi. Çıkış iptal edildi.",
        
        # ---------------------------------------------------------------------
        # TABLO YÖNETİMİ
        # ---------------------------------------------------------------------
        "error_formatting_line": "{line} satırı biçimlendirilirken hata!",
        "error_formatting_revert": "Geri alma sırasında {line} satırı biçimlendirme hatası",
        "changes_reverted_item": "{num}. öğe için değişiklikler geri alındı.",
        "no_changes_to_revert_item": "{num}. öğe için geri alınacak değişiklik yok.",
        "select_item_to_revert": "Geri almak için bir öğe seçin.",
        "no_active_table_revert": "Geri almak için aktif tablo yok.",
        "no_selected_items_revert": "Geri almak için seçili öğe yok.",
        "changes_reverted_count": "{count} öğe için değişiklikler geri alındı.",
        "no_changes_selected_items": "Seçili öğelerde geri alınacak değişiklik yok.",
        "no_active_tab_revert": "Geri almak için aktif sekme yok.",
        "no_text_changes_revert": "Geri alınacak metin değişikliği yok.",
        "all_changes_reverted": "Tüm {count} metin değişikliği geri alındı.",
        "revert_failed_internal": "Değişiklikler geri alınamadı (iç hata?).",
        
        # Tablo Sütunları
        "col_char": "Karakter",
        "col_original": "Orijinal",
        "col_translation": "Çeviri",
        "col_type": "Tip",
        "col_text": "Metin",
        
        # ---------------------------------------------------------------------
        # AI / ÇEVİRİ DİYALOGLARI
        # ---------------------------------------------------------------------
        # AI Düzenleme
        "dialog_ai_edit": "AI ile Düzenle (Gemini)",
        "ai_item_info": "Öğe {current} / {total} (Mod: {mode})",
        "ai_instruction_label": "Metni nasıl değiştirmek istediğinizi açıklayın:",
        "ai_instruction_placeholder": "Örn: Daha günlük konuşma diliyle yaz, dilbilgisini düzelt, kısalt vb. Varsayılan iyileştirme için boş bırakın.",
        "ai_result_placeholder": "Gemini sonucu burada görünecek...",
        "btn_send_request": "Gemini'ye Gönder",
        "btn_sending": "Gönderiliyor...",
        "btn_apply_result": "Sonucu Uygula",
        "ai_no_result": "Uygulanacak metin yok.",
        
        # Google Çeviri
        "dialog_google_translate": "Google Translate ile Çevir",
        "translate_source": "Kaynak: {lang}",
        "translate_target": "Hedef: {lang}",
        "translate_result_placeholder": "Çeviri burada görünecek...",
        "btn_translate": "Çevir",
        "btn_translating": "Çevriliyor...",
        "btn_apply_translation": "Çeviriyi Uygula",
        "translate_no_result": "Uygulanacak çeviri yok.",
        "translate_lib_unavailable": "deep-translator kütüphanesi kullanılamıyor.",
        "translate_no_target": "Hedef dil belirtilmemiş.",
        
        # Değişken Uyarısı
        "variable_warning_title": "Değişken Uyarısı",
        "variable_warning_message": "Çeviride bazı değişkenler kaybolmuş veya değişmiş olabilir:\n{vars}\n\nYine de uygulamak istiyor musunuz?",
        
        # Hata Mesajları
        "error_data": "Veri Hatası",
        "error_data_item": "{index}. öğe için veri alınamadı.",
        "error_data_file": "{index}. öğe için dosya verisi alınamadı.",
        "error_gemini": "Gemini Hatası",
        "error_gemini_critical": "Kritik Gemini Hatası",
        "error_google_translate": "Google Translate Hatası",
        "error_formatting": "Biçimlendirme Hatası",
        "error_formatting_message": "Düzenlenen metin için satır biçimlendirilemedi.",
        "error_line_data": "Satır Veri Hatası",
        "error_line_data_message": "Orijinal satır {line} dosyada bulunamadı veya güncelleme başarısız.",
        
        # ---------------------------------------------------------------------
        # API ANAHTARI DİYALOĞU
        # ---------------------------------------------------------------------
        "dialog_api_key": "Google Gemini API Anahtarı Ayarları",
        "api_key_info": "Bu uygulama AI özelliklerini kullanmak için Google Gemini API anahtarı gerektirir.<br>Anahtarınızı <a href='https://aistudio.google.com/app/apikey'>Google AI Studio</a> adresinden alabilirsiniz.",
        "api_key_current": "Mevcut kayıtlı anahtar: {key}",
        "api_key_not_saved": "API anahtarı henüz kaydedilmedi.",
        "api_key_new": "Yeni API Anahtarı:",
        "api_key_placeholder": "AI...",
        "btn_show_key": "Anahtarı Göster",
        "btn_hide_key": "Anahtarı Gizle",
        "btn_save_close": "Kaydet ve Kapat",
        "api_key_delete_confirm": "Anahtarı Sil?",
        "api_key_delete_message": "Kaydedilmiş API anahtarını silmek istediğinizden emin misiniz?",
        "api_key_save_error": "API anahtarı kaydedilemedi/silinemedi.",
        
        # ---------------------------------------------------------------------
        # MOD SEÇİM DİYALOĞU
        # ---------------------------------------------------------------------
        "dialog_mode_select": "Çalışma Modu Seç",
        "mode_file": "Dosya: <b>{name}</b>",
        "mode_path": "Yol: {path}",
        "mode_direct": "Doğrudan Mod",
        "mode_direct_desc": "Dosyayı doğrudan düzenler (diyalog, menü seçenekleri, ekran metinleri)",
        "mode_translate": "Çeviri Modu", 
        "mode_translate_desc": "Çeviri bloklarını düzenler (orijinal → yeni)",
        
        # ---------------------------------------------------------------------
        # SATIR EKLEME DİYALOĞU
        # ---------------------------------------------------------------------
        "dialog_insert_line": "Yeni Satır Ekle (Direct Mod)",
        "insert_line_label": "Yeni Ren'Py satırını girin:",
        "insert_line_examples": "Örnekler:<br><code>karakter \"metin\"</code><br><code>\"anlatı metni\"</code><br><code>\"Menü seçeneği\":jump hedef</code>",
        "insert_line_placeholder": "Örn: char \"metin\" veya \"anlatı\"",
        
        # ---------------------------------------------------------------------
        # ANA AYARLAR DİYALOĞU
        # ---------------------------------------------------------------------
        "dialog_main_settings": "Ana Ayarlar",
        
        # Mod Seçimi Grubu
        "settings_mode_selection": "Dosya Açma Modu Seçimi",
        "settings_mode_auto": "Otomatik (dosya adına göre)",
        "settings_mode_manual": "Her zaman sor",
        
        # Dil Ayarları Grubu
        "settings_language": "Dil Ayarları",
        "settings_use_detected_lang": "Çeviri modunda hedef dili otomatik algıla",
        
        # Proje Ayarları Grubu
        "settings_project": "Proje Ayarları",
        "settings_auto_prepare": "Proje açıldığında RPA/RPYC dosyalarını otomatik hazırla",
        
        # Varsayılanlar Grubu
        "settings_defaults": "Varsayılan Değerler",
        "settings_source_lang": "Kaynak Dil:",
        "settings_target_lang": "Hedef Dil:",
        "settings_gemini_model": "Gemini Model:",
        
        # UI Dili Grubu
        "settings_ui_language": "Arayüz Dili",
        "settings_ui_lang_label": "Dil:",
        "settings_ui_lang_restart": "Dil değişikliği uygulamanın yeniden başlatılmasını gerektirir.",
        
        "settings_save_error": "Ayarlar kaydedilemedi.",
        "settings_saved": "Ayarlar kaydedildi.",
        
        # ---------------------------------------------------------------------
        # TOPLU ÇEVİRİ
        # ---------------------------------------------------------------------
        "batch_translate_title": "Toplu Çeviri",
        "batch_select_items": "Çevrilecek öğeleri seçin (Ctrl+Click veya Shift+Click).",
        "batch_no_selection": "Toplu çeviri için öğe seçilmedi.",
        "batch_cancel_confirm": "Toplu Çeviri İptal",
        "batch_cancel_message": "Toplu çeviriyi iptal etmek istediğinizden emin misiniz?",
        "batch_progress": "Çevriliyor: {current}/{total}",
        "batch_cancelled": "Toplu çeviri iptal edildi.",
        "batch_result_title": "Toplu Çeviri Sonucu",
        "batch_result_message": "Çeviri tamamlandı.\n\nBaşarılı: {success}/{total}\nHata: {errors}\nUyarı: {warnings}",
        
        # ---------------------------------------------------------------------
        # GEMİNİ DURUM MESAJLARI
        # ---------------------------------------------------------------------
        "gemini_no_internet": "AI kullanılamıyor: İnternet bağlantısı yok.",
        "gemini_no_api_key": "AI kullanılamıyor: API anahtarı bulunamadı.",
        "gemini_no_model": "AI kullanılamıyor: Model seçilmedi.",
        "gemini_init_error": "Gemini başlatma hatası ({model}). Anahtarı/konsolu kontrol edin.",
        "gemini_initialized": "Gemini ({model}) başlatıldı.",
        "gemini_critical_error": "Kritik Gemini başlatma hatası.",
        
        # ---------------------------------------------------------------------
        # HATA BAŞLIKLARI (QMessageBox)
        # ---------------------------------------------------------------------
        "import_error_title": "İçe Aktarma Hatası",
        "network_error_title": "Ağ Hatası",
        "network_error_gemini": "Gemini Ağ Hatası",
        "network_error_gemini_msg": "Gemini model nesnesi oluşturulamadı.\nİnternet bağlantınızı kontrol edin.",
        
        # ---------------------------------------------------------------------
        # BREAKPOINT/İŞARETÇİ
        # ---------------------------------------------------------------------
        "breakpoint_added": "{num}. öğeye işaretçi eklendi.",
        "breakpoint_removed": "{num}. öğeden işaretçi kaldırıldı.",
        "no_more_breakpoints": "Başka işaretçi yok.",
        "all_breakpoints_cleared": "Tüm işaretçiler ({count}) temizlendi.",
        "no_breakpoints": "Temizlenecek işaretçi yok.",
        
        # ---------------------------------------------------------------------
        # BUL/DEĞİŞTİR
        # ---------------------------------------------------------------------
        "find_no_match": "Eşleşme bulunamadı.",
        "find_match_found": "Eşleşme bulundu: {num}. öğe.",
        "find_wrapped": "Başa döndü, devam ediyor...",
        "replace_success": "'{old}' → '{new}' değiştirildi ({num}. öğe).",
        "replace_no_match": "Seçili öğede eşleşme bulunamadı.",
        "replace_all_count": "{count} değişiklik yapıldı.",
        "replace_all_none": "Eşleşme bulunamadı.",
        
        # ---------------------------------------------------------------------
        # PROJE HAZIRLAMA (project_utils.py)
        # ---------------------------------------------------------------------
        "unrpa_found_path": "INFO: 'unrpa' komutu sistem PATH'inde bulundu.",
        "unrpa_found_module": "INFO: 'unrpa' modülü 'python -m unrpa' ile kullanılabilir.",
        "unrpa_not_found": "UYARI: 'unrpa' komutu PATH'te bulunamadı ve 'python -m unrpa' ile erişilemiyor. *.rpa çıkarma kullanılamayacak.",
        "unrpa_check_install": "         'unrpa' kurulumunu (pip install unrpa) ve PATH değişkenini kontrol edin.",
        "unrpa_return_code": "         (python -m unrpa --version dönüş kodu: {code}, stderr: {stderr}...)",
        "python_not_found": "UYARI: Python yorumlayıcısı '{exe}' bulunamadı. 'python -m unrpa' kontrol edilemiyor.",
        "unrpa_check_timeout": "UYARI: 'python -m unrpa' kontrolü çok uzun sürdü.",
        "unrpa_check_error": "UYARI: 'python -m unrpa' kontrol hatası: {error}",
        
        "unrpyc_missing_decompiler": "UYARI: '{script}' betiği bulundu, ancak 'decompiler' klasörü '{dir}' içinde yok.",
        "unrpyc_copy_all": "         unrpyc'nin TÜM içeriğini 'unrpyc_lib' klasörüne kopyaladığınızdan emin olun.",
        "unrpyc_found": "INFO: Dekompile betiği '{script}' ve 'decompiler' klasörü '{dir}' içinde bulundu.",
        "unrpyc_not_found": "UYARI: Dekompile betiği '{script}' '{dir}' içinde bulunamadı.",
        "unrpyc_unavailable": "         *.rpyc dekompilasyonu kullanılamayacak.",
        "unrpyc_place_lib": "         unrpyc kütüphanesini (decompiler klasörü dahil) 'utils/unrpyc_lib' klasörüne yerleştirin.",
        
        "rpa_already_extracted": "'{name}' arşivi daha önce çıkarılmış (işaretçi bulundu).",
        "rpa_extract_attempt": "INFO: Arşiv çıkarma deneniyor: {path} (CWD: {cwd})",
        "rpa_game_not_found": "UYARI: 'game' klasörü {path} içinde bulunamadı. Çıkarma CWD={path} ile yapılacak.",
        "rpa_command_debug": "DEBUG: Komut çalıştırılıyor: {cmd}",
        "rpa_cwd_debug": "DEBUG: CWD dizini: {cwd}",
        "rpa_success": "'{name}' arşivi başarıyla işlendi.",
        "rpa_error_no_file": "unrpa '{name}' için 'No such file' hatası verdi.",
        "rpa_error_with_output": "unrpa '{name}' için hata verdi (Kod: 0, ancak çıktıda hata var).",
        "rpa_error_code": "unrpa '{name}' için hata (Kod: {code}).",
        "rpa_timeout": "'{name}' çıkarma işlemi çok uzun sürdü (>5 dakika).",
        "rpa_command_not_found": "'{cmd}' komutu bulunamadı.",
        "rpa_unexpected_error": "'{name}' için beklenmeyen hata: {error}",
        "rpa_unavailable": "unrpa komutu kullanılamıyor.",
        
        "rpyc_already_decompiled": "'{name}' zaten dekompile edilmiş ('{rpy}' bulundu).",
        "rpyc_attempt": "INFO: runpy ile dekompilasyon deneniyor: {path}",
        "rpyc_success": "'{name}' başarıyla dekompile edildi.",
        "rpyc_no_output": "runpy '{name}' için başarılı (Kod 0), ancak {rpy} dosyası bulunamadı. Dosya boş veya sadece python bloğu içeriyor olabilir.",
        "rpyc_error": "'{name}' dekompilasyon hatası (Kod: {code}).",
        "rpyc_unavailable": "unrpyc dekompile betiği bulunamadı.",
        
        "project_path_invalid": "Proje yolu bulunamadı veya klasör değil: {path}",
        "auto_prep_disabled_settings": "INFO: Otomatik proje hazırlama ayarlarda kapalı.",
    
        # ---------------------------------------------------------------------
        # AKSİYON İŞLEYİCİ (gui_action_handler.py)
        # ---------------------------------------------------------------------
        "batch_error_deep_translator_not_found": "KRİTİK: deep-translator kütüphanesi bulunamadı.",
        "batch_error_google_translator_init_failed": "KRİTİK: GoogleTranslator oluşturulamadı: {error}",
        "batch_task_canceled": "İşlem kullanıcı tarafından iptal edildi.",
        "batch_skipped_invalid_index": "Geçersiz indeks atlandı: {index}",
        "batch_variable_mismatch": "Değişken uyuşmazlığı: {item}",
        "file_line_label": "dosya satırı {line}",
        "batch_empty_translation": "{item} için boş çeviri",
        "batch_translation_error": "{item} için çeviri hatası",
        "edit_ai_failed_init": "Gemini hazırlanamadı. Ayarları/ağ bağlantısını kontrol edin.",
        "edit_ai_gemini_unavailable": "Gemini kullanılamıyor. API anahtarını ve model seçimini kontrol edin.",
        "edit_ai_gemini_error_title": "Gemini Hatası",
        "edit_ai_gemini_error_msg": "Gemini başlatılamadı.\n\nOlası nedenler:\n- Geçersiz veya aktif olmayan API anahtarı.\n- Gemini modeli seçilmemiş veya erişilemiyor.\n- İnternet bağlantı sorunları.\n\nAyarlar -> Gemini API Anahtarı ve model seçimini kontrol edin.",
        "edit_ai_select_item": "AI ile düzenlemek için bir öğe seçin.",
        "edit_ai_data_error": "AI düzenlemesi için veri hatası.",
        "edit_ai_success": "{item}. öğe AI kullanılarak değiştirildi.",
        "edit_ai_update_error": "AI sonrası veri güncelleme hatası.",
        
        # ---------------------------------------------------------------------
        # RENFORGE ÇEKİRDEK (renforge_core.py)
        # ---------------------------------------------------------------------
        "core_file_not_found": "Dosya bulunamadı: {path}",
        "core_error": "Hata: {error}",
        "core_read_error": "'{path}' dosyası okunurken hata: {error}",
        "core_file_loaded": "{path} dosyası yüklendi ({lines} satır). {breakpoints} işaretçi bulundu.",
        "core_parser_start": "Dosya için bağlamsal ayrıştırıcı başlatılıyor...",
        "core_parser_process": "'translate' modu için ayrıştırıcı sonuçları işleniyor...",
        "core_lang_found": "Çeviri dili algılandı: {lang}",
        "core_lang_warning": "Uyarı: Başka bir blok dili bulundu ({line}. satırda '{detected}' sonra '{lang}'). İlk bulunan '{detected}' kullanılıyor.",
        "core_type_mismatch_warning": "Uyarı Çekirdek S{line}: Orijinal türü ('{orig_type}', tag: {orig_tag}) çeviri satırı türüyle ('{trans_type}', tag: {trans_tag}) uyuşmuyor. Satır atlandı.",
        "core_type_unknown_warning": "Uyarı Çekirdek S{line}: Orijinal yorumda diyalog/anlatım türü belirlenemedi: '# {comment}'. Çeviri satırı '{text}...' atlandı.",
        "core_process_complete": "İşlem tamamlandı. 'translate' modunda düzenlenecek {count} öğe bulundu.",
        "core_no_pairs_warning": "Uyarı: 'translate' blokları bulundu, ancak düzenleme için orijinal/çeviri çiftleri bulunamadı.",
        "core_save_success": "Değişiklikler dosyaya kaydedildi: {path}",
        "core_save_error": "'{path}' dosyası kaydedilirken hata: {error}",
        "core_filter_direct": "'direct' modu için ayrıştırıcı sonuçları filtreleniyor...",
        "core_direct_found": "'direct' modunda düzenleme için {count} satır bulundu.",
        "core_direct_none": "Düzenlenecek satır bulunamadı.",
        "core_rebuild_saving": "Dosya yeniden oluşturuluyor ve {path} yoluna kaydediliyor...",
        "core_reformat_warning": "Uyarı: {line}. satır yeniden biçimlendirilemedi. Bellekteki sürüm kullanılıyor: '{content}'",
        "core_save_success_count": "Dosya başarıyla kaydedildi. Değiştirilen metin satırı sayısı: {count}",
        
        "google_trans_unavailable_net": "Google Translate kullanılamıyor: internet bağlantısı yok.",
        "error_no_network_title": "Ağ Yok",
        "error_no_network_msg_google": "Google Translate kullanmak için internet bağlantısı gereklidir.",
        "google_trans_unavailable_lib": "Google Translate kullanılamıyor (deep-translator kütüphanesi).",
        "error_library_not_found_title": "Kütüphane Hatası",
        "error_library_not_found_msg": "'deep-translator' kütüphanesi bulunamadı.\nGoogle Translate fonksiyonu kullanılamaz.\n\nYüklemek için: pip install deep-translator",
        "google_trans_select_item": "Google Translate için bir öğe seçin.",
        "google_trans_data_error": "Google Translate için veri hatası.",
        "google_trans_success": "{item}. öğe Google ile çevrildi.",
        "google_trans_update_error": "Google Translate sonrası veri güncelleme hatası.",
        
        "batch_google_unavailable_net": "Toplu çeviri kullanılamıyor: internet bağlantısı yok.",
        "error_no_network_msg_batch": "Toplu Google Translate için internet bağlantısı gereklidir.",
        "batch_google_unavailable_lib": "Google Translate kullanılamıyor (deep-translator kütüphanesi).",
        "error_library_not_found_msg_shorter": "'deep-translator' kütüphanesi bulunamadı.\nYüklemek için: pip install deep-translator",
        "batch_no_active_tab": "Toplu çeviri için aktif sekme yok.",
        "batch_no_selected_rows": "Toplu çeviri için seçili satır yok.",
        "batch_data_error": "Toplu çeviri için veri hatası.",
        "batch_lang_required_title": "Dil Gerekli",
        "batch_target_lang_required_msg": "Hedef çeviri dilini belirtin.",
        "batch_source_lang_required_msg": "Kaynak çeviri dilini belirtin.",
        "batch_google_title": "Toplu Google Translate",
        "batch_confirm_msg": "{count} satırı Google Translate ile çevirmek istiyor musunuz?\nDiller: '{source}' ({source_code}) -> '{target}' ({target_code})\n\nUYARI: Bu işlem seçili satırlardaki mevcut metni/çeviriyi üzerine yazacaktır!\n(Dil seçiminin doğru olduğundan emin olun)",
        "batch_canceled": "Toplu çeviri iptal edildi.",
        "batch_progress_msg": "Satırlar çevriliyor...",
        "batch_starting": "Toplu çeviri başlatılıyor...",
        
        "marker_select_line": "İşaretçi için bir satır seçin.",
        "marker_data_error": "İşaretçi ayarlamak için veri hatası.",
        "marker_line_idx_error": "{item}. öğe için dosya satır numarası belirlenemedi.",
        "marker_removed": "{line}. satırdan işaretçi kaldırıldı.",
        "marker_set": "{line}. satıra işaretçi eklendi.",
        "marker_nav_no_markers": "Gidilecek işaretçi yok.",
        "marker_nav_first": "İlk işaretçiye gidiliyor.",
        "marker_nav_not_found": "İşaretçiler bulunamadı (hata?).",
        "marker_clear_no_data": "İşaretçileri temizlemek için veri yok.",
        "marker_clear_none_set": "Ayarlanmış işaretçi yok.",
        "confirmation": "Onay",
        "marker_clear_confirm_msg": "{file} dosyasındaki tüm işaretçileri ({count}) kaldırmak istiyor musunuz?",
        "marker_clear_success": "Tüm işaretçiler kaldırıldı.",
        
        "insert_line_mode_error": "Satır ekleme sadece 'Doğrudan' modda kullanılabilir.",
        "insert_line_data_error": "Ekleme için veri hatası.",
        "insert_line_canceled": "Ekleme iptal edildi (boş satır).",
        "parsing_error": "Ayrıştırma Hatası",
        "insert_line_parse_error_msg": "Satır düzenlenebilir bir tür olarak tanınmadı:\n'{line}'\n(İzin verilen türler: {types})",
        "insert_line_format_error": "Ekleme için satır biçimlendirilemedi.",
        "insert_line_success": "Satır eklendi.",
        
        "delete_line_mode_error": "Satır silme sadece 'Doğrudan' modda kullanılabilir.",
        "delete_line_select_error": "Silinecek bir satır seçin.",
        "delete_line_confirm_title": "Silmeyi Onayla",
        "delete_line_confirm_msg": "{file} dosyasından {line}. satırı silmek istiyor musunuz?\n\nMetin: \"{text}\"",
        "delete_line_success": "Satır silindi",
        "marker_removed_short": "işaretçi kaldırıldı",
        "delete_line_error_title": "Silme Hatası",
        "delete_line_index_error": "Silme sırasında kritik indeks hatası: {error}\nVeri bozulmuş olabilir!",
        "delete_line_unexpected_error": "Silme sırasında beklenmeyen hata: {error}",
        "delete_line_canceled": "Satır silme iptal edildi.",
        
        "search_enter_text_error": "Aranacak metni girin ve bir dosya açın.",
        "search_regex_error": "Regex Hatası: {error}",
        "search_no_data": "Aranacak veri yok.",
        "search_restarted": "'{text}' araması baştan başlatıldı.",
        "search_found": "'{text}' {line}. satırda bulundu.",
        "search_not_found": "'{text}' bulunamadı.",
        
        "replace_enter_text_error": "Aranacak metni girin ve değiştirmek için bir satır seçin.",
        "replace_data_error": "Değiştirme için veri veya indeks hatası.",
        "replace_format_error_title": "Biçimlendirme Hatası",
        "replace_format_error_msg": "Değiştirme işleminden sonra {line}. satır güncellenemedi.\nTablodaki değişiklikler uygulandı ancak kayıtta kaybolabilir.",
        "replace_success_finding_next": "{line}. satırda değiştirildi. Sonraki aranıyor...",
        "replace_failed": "Değiştirme işlemi başarısız (re.subn hatası).",
        "replace_regex_error": "Değiştirme sırasında Regex hatası: {error}",
        "replace_no_match": "Seçili satırda eşleşme yok. Sonraki aranıyor...",
        
        "replace_all_enter_text_error": "Aranacak/değiştirilecek metni girin ve bir dosya açın.",
        "replace_all_no_data": "Değiştirilecek veri yok.",
        "replace_all_title": "Tümünü Değiştir?",
        "replace_all_confirm_msg": "Geçerli dosyadaki tüm {search_mode}'{search}' öğelerini '{replace}' ile değiştirmek istiyor musunuz?\nBu işlem geri alınamaz.",
        "replace_all_canceled": "Tümünü değiştirme iptal edildi.",
        "replace_all_starting": "Tümünü değiştirme işlemi yapılıyor...",
        "replace_all_regex_error": "Satır {line}: Değiştirme sırasında Regex hatası: {error}",
        "replace_all_format_error": "Satır {line} (dosya {file_line}): Satır biçimlendirme hatası.",
        "replace_all_update_error": "Satır {line}: Dosya satırı güncelleme hatası (indeks/veri).",
        "replace_all_finished": "Tamamlandı. Toplam {count} değişiklik yapıldı ({lines} satırda).",
        "replace_all_errors": "Hatalar: {count}.",
        "replace_all_error_title": "'Tümünü Değiştir' Sırasında Hatalar",
        "replace_all_error_msg_header": "Tümünü değiştirme sırasında hatalar oluştu:",

        # EMPTY FILE WARNINGS
        "warning_empty_translate_mode_title": "Çevrilebilir Öğe Bulunamadı",
        "warning_empty_translate_mode_msg": "Dosya 'Translate' modunda yüklendi, ancak düzenlenebilir orijinal/çeviri çifti bulunamadı.\n\nOlası nedenler:\n1. Dosya standart Ren'Py çeviri yorumlarını (comments) içermiyor.\n2. Dosya boş veya diyalog dışı kodlar içeriyor.\n3. Dosya içeriğini kontrol edin veya 'Direct' modunda açmayı deneyin.",
        "warning_empty_direct_mode_title": "Düzenlenebilir Satır Bulunamadı",
        "warning_empty_direct_mode_msg": "'Direct' modunda yüklendi, ancak düzenlenebilir diyalog satırı bulunamadı.",

        # UI BUTTONS & GROUPS
        "btn_ai": "AI",
        "btn_gtranslate": "GÇeviri",
        "btn_batch_gtranslate": "Toplu GÇeviri",
        "btn_revert": "Geri Al",
        "btn_revert_all": "Tümünü Geri Al",
        "btn_marker": "İşaretçi",
        "btn_next_marker": "Sonraki İşaretçi",
        "btn_clear_markers": "İşaretçileri Temizle",
        "btn_add": "Ekle",
        "btn_delete": "Sil",
        "group_tools_nav": "Araçlar ve Gezinme",
        "group_global_settings": "Genel Ayarlar",

        # MENU TITLES
        "menu_tools": "Araçlar",
        "menu_settings": "Ayarlar",
        "menu_view": "Görünüm",
        "menu_toggle_marker": "İşaretçi Ekle/Kaldır",
        "menu_clear_markers": "Tüm İşaretçileri Temizle",
        "menu_insert_line": "Satır Ekle (Doğrudan)",
        "menu_delete_line": "Satır Sil (Doğrudan)",
        "menu_settings_general": "Genel...",
        "menu_settings_apikey": "Gemini API Anahtarı...",
        "menu_view_project": "Proje Paneli",
        "menu_view_search": "Arama Paneli",
    },
    
    # =========================================================================
    # ENGLISH TRANSLATIONS
    # =========================================================================
    "en": {
        # ---------------------------------------------------------------------
        # GENERAL / COMMON
        # ---------------------------------------------------------------------
        "ready": "Ready",
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "success": "Success",
        "cancel": "Cancel",
        "ok": "OK",
        "yes": "Yes",
        "no": "No",
        "save": "Save",
        "close": "Close",
        "apply": "Apply",
        "delete": "Delete",
        "edit": "Edit",
        "open": "Open",
        "file": "File",
        "project": "Project",
        "settings": "Settings",
        "about": "About",
        "help": "Help",
        "exit": "Exit",
        "loading": "Loading...",
        "saving": "Saving...",
        "processing": "Processing...",
        
        # ---------------------------------------------------------------------
        # MAIN WINDOW
        # ---------------------------------------------------------------------
        "window_title": "RenForge - Ren'Py scripts editor v{version}",
        "no_open_files": "No open files",
        "active_tab_data_error": "Active tab data error",
        
        # Menu - File
        "menu_file": "&File",
        "menu_open_project": "&Open Project...",
        "menu_open_file": "Open &File...",
        "menu_save": "&Save",
        "menu_save_as": "Save &As...",
        "menu_save_all": "Save A&ll",
        "menu_close_tab": "&Close Tab",
        "menu_exit": "E&xit",
        
        # Menu - Edit
        "menu_edit": "&Edit",
        "menu_revert_item": "&Revert Item",
        "menu_revert_selected": "Revert &Selected",
        "menu_revert_all": "Revert &All",
        "menu_insert_line": "&Insert Line (Direct)",
        "menu_delete_line": "&Delete Line (Direct)",
        
        # Menu - Translate
        "menu_translate": "&Translate",
        "menu_translate_google": "Translate via &Google",
        "menu_batch_translate": "&Batch Google Translate",
        "menu_edit_ai": "Edit with &AI (Gemini)",
        "menu_batch_ai": "Batch A&I Translate",
        
        # Menu - Navigation
        "menu_navigation": "&Navigation",
        "menu_prev_item": "&Previous Item",
        "menu_next_item": "&Next Item",
        "menu_toggle_breakpoint": "&Toggle Breakpoint",
        "menu_next_breakpoint": "Go to Next &Breakpoint",
        "menu_clear_breakpoints": "&Clear All Breakpoints",
        "menu_find_next": "&Find Next",
        "menu_replace": "&Replace",
        "menu_replace_all": "Replace A&ll",
        
        # Menu - View
        "menu_view": "&View",
        "menu_toggle_project_panel": "&Project Panel",
        
        # Menu - Settings
        "menu_settings": "&Settings",
        "menu_main_settings": "&Main Settings...",
        "menu_api_key": "Set &API Key...",
        "menu_refresh_models": "&Refresh Model List",
        
        # Menu - Help
        "menu_help": "&Help",
        "menu_about": "&About",
        
        # Toolbar
        "toolbar_mode": "Mode:",
        "toolbar_source": "Source:",
        "toolbar_target": "Target:",
        "toolbar_model": "Gemini Model:",
        "toolbar_find": "Find:",
        "toolbar_replace_with": "Replace with:",
        "toolbar_search_placeholder": "Text to search",
        "toolbar_replace_placeholder": "Replacement text",
        "toolbar_regex": "Regex",
        "toolbar_case_sensitive": "Case Sensitive",
        
        # Buttons
        "btn_find_next": "Find Next",
        "btn_replace": "Replace",
        "btn_replace_all": "Replace All",
        "btn_prev": "◄ Prev",
        "btn_next": "Next ►",
        "btn_google_translate": "Google Translate",
        "btn_batch_translate": "Batch Translate",
        "btn_ai_edit": "AI Edit",
        "btn_batch_ai": "Batch AI",
        
        # Status Bar
        "status_no_open_files": "No open files",
        "status_project": "Project: {name}",
        "status_file": "File: {name}",
        "status_mode": "Mode: {mode}",
        "status_mode_direct": "Direct",
        "status_mode_translate": "Translate",
        "status_mode_unknown": "Unknown",
        "status_items": "Items: {count}",
        "status_selected": "Selected: {current}/{total}",
        "status_line": "(Line {num})",
        "status_character": "Character: {tag}",
        "status_type": "Type: {type}",
        "status_marker": "MARKER",
        "status_modified": "MODIFIED",
        "status_no_selection": "(No selection)",
        "status_no_internet": "No internet connection.",
        
        # ---------------------------------------------------------------------
        # FILE OPERATIONS
        # ---------------------------------------------------------------------
        "file_opening_cancelled": "File opening cancelled.",
        "file_opening_cancelled_mode": "File opening cancelled. Mode setting must be selected.",
        "project_opening_cancelled": "Project opening cancelled.",
        "project_opened": "Project opened: {name}",
        "preparing_project": "Preparing project files (rpa/rpyc)... Please wait.",
        "project_prep_errors": "Project preparation finished with errors/warnings.",
        "project_prep_success": "Project file preparation completed successfully.",
        "project_prep_skipped": "Auto-preparation skipped (disabled in settings).",
        "project_prep_error": "Error during project file preparation: {error}",
        "auto_prep_disabled": "Auto-preparation disabled in settings.",
        
        "loading_file": "Loading {name} ({mode})...",
        "file_loaded": "File {name} loaded ({count} items). Mode: '{mode}'.",
        "error_loading_file": "Error loading {name}: {error}",
        
        "no_active_tab_save": "No active tab to save.",
        "saving_file": "Saving {name}...",
        "file_saved": "File saved: {path}",
        "file_save_error": "File save error: {error}",
        "no_unsaved_files": "No unsaved changes.",
        "all_files_saved": "All changes saved.",
        "save_all_errors": "{failed}/{total} files could not be saved.",
        
        # File Dialogs
        "dialog_open_project": "Select Project Folder",
        "dialog_open_file": "Open Ren'Py File",
        "dialog_save_as": "Save As",
        "rpy_files": "Ren'Py Files",
        "all_files": "All Files",
        
        # ---------------------------------------------------------------------
        # TAB MANAGEMENT
        # ---------------------------------------------------------------------
        "no_active_tab_close": "No active tab to close.",
        "tab_close_cancelled": "Tab closing cancelled.",
        "tab_save_failed": "Save failed. Tab closing cancelled.",
        
        # Unsaved Changes Dialog
        "unsaved_changes_title": "Unsaved Changes",
        "unsaved_changes_message": "'{name}' has unsaved changes.\nWhat would you like to do?",
        "unsaved_changes_exit": "There are open files with unsaved changes.\nWhat would you like to do?",
        "btn_save_all": "Save All",
        "btn_exit_without_saving": "Exit Without Saving",
        "exit_cancelled": "Exit cancelled.",
        "save_failed_exit_cancelled": "Failed to save all files. Exit cancelled.",
        
        # ---------------------------------------------------------------------
        # TABLE MANAGEMENT
        # ---------------------------------------------------------------------
        "error_formatting_line": "Error formatting line {line}!",
        "error_formatting_revert": "Error formatting line {line} on revert",
        "changes_reverted_item": "Changes for item {num} reverted.",
        "no_changes_to_revert_item": "No changes to revert for item {num}.",
        "select_item_to_revert": "Select an item to revert changes.",
        "no_active_table_revert": "No active table to revert.",
        "no_selected_items_revert": "No selected items to revert.",
        "changes_reverted_count": "Changes reverted for {count} items.",
        "no_changes_selected_items": "No changes to revert in selected items.",
        "no_active_tab_revert": "No active tab to revert.",
        "no_text_changes_revert": "No text changes to revert.",
        "all_changes_reverted": "All {count} text changes reverted.",
        "revert_failed_internal": "Failed to revert changes (internal error?).",
        
        # Table Columns
        "col_char": "Character",
        "col_original": "Original",
        "col_translation": "Translation",
        "col_type": "Type",
        "col_text": "Text",
        
        # ---------------------------------------------------------------------
        # AI / TRANSLATE DIALOGS
        # ---------------------------------------------------------------------
        # AI Edit
        "dialog_ai_edit": "Edit with AI (Gemini)",
        "ai_item_info": "Item {current} / {total} (Mode: {mode})",
        "ai_instruction_label": "Describe how you want to change the text:",
        "ai_instruction_placeholder": "E.g.: Make it more conversational, fix grammar, shorten, etc. Leave empty for default improvement.",
        "ai_result_placeholder": "Gemini's result will appear here...",
        "btn_send_request": "Send Request to Gemini",
        "btn_sending": "Sending...",
        "btn_apply_result": "Apply Result",
        "ai_no_result": "No text to apply.",
        
        # Google Translate
        "dialog_google_translate": "Translate via Google Translate",
        "translate_source": "Source: {lang}",
        "translate_target": "Target: {lang}",
        "translate_result_placeholder": "Translation will appear here...",
        "btn_translate": "Translate",
        "btn_translating": "Translating...",
        "btn_apply_translation": "Apply Translation",
        "translate_no_result": "No translation to apply.",
        "translate_lib_unavailable": "The deep-translator library is unavailable.",
        "translate_no_target": "Target language is not specified.",
        
        # Variable Warning
        "variable_warning_title": "Variable Warning",
        "variable_warning_message": "Some variables may be missing or changed in the translation:\n{vars}\n\nDo you still want to apply?",
        
        # Error Messages
        "error_data": "Data Error",
        "error_data_item": "Failed to retrieve data for item {index}.",
        "error_data_file": "Failed to retrieve file data for item {index}.",
        "error_gemini": "Gemini Error",
        "error_gemini_critical": "Critical Gemini Error",
        "error_google_translate": "Google Translate Error",
        "error_formatting": "Formatting Error",
        "error_formatting_message": "Could not format line for edited text.",
        "error_line_data": "Line Data Error",
        "error_line_data_message": "Original line {line} not found in file or update failed.",
        
        # ---------------------------------------------------------------------
        # API KEY DIALOG
        # ---------------------------------------------------------------------
        "dialog_api_key": "Google Gemini API Key Setup",
        "api_key_info": "This application requires a Google Gemini API key for AI features.<br>Get your key at <a href='https://aistudio.google.com/app/apikey'>Google AI Studio</a>.",
        "api_key_current": "Current saved key: {key}",
        "api_key_not_saved": "API key has not been saved yet.",
        "api_key_new": "New API Key:",
        "api_key_placeholder": "AI...",
        "btn_show_key": "Show Key",
        "btn_hide_key": "Hide Key",
        "btn_save_close": "Save and Close",
        "api_key_delete_confirm": "Delete Key?",
        "api_key_delete_message": "Are you sure you want to delete the saved API key?",
        "api_key_save_error": "Failed to save/delete API key.",
        
        # ---------------------------------------------------------------------
        # MODE SELECTION DIALOG
        # ---------------------------------------------------------------------
        "dialog_mode_select": "Select Working Mode",
        "mode_file": "File: <b>{name}</b>",
        "mode_path": "Path: {path}",
        "mode_direct": "Direct Mode",
        "mode_direct_desc": "Edit file directly (dialogues, menu options, screen texts)",
        "mode_translate": "Translate Mode",
        "mode_translate_desc": "Edit translation blocks (original → new)",
        
        # ---------------------------------------------------------------------
        # INSERT LINE DIALOG
        # ---------------------------------------------------------------------
        "dialog_insert_line": "Insert New Line (Direct Mode)",
        "insert_line_label": "Enter the new Ren'Py line:",
        "insert_line_examples": "Examples:<br><code>character \"text\"</code><br><code>\"narration text\"</code><br><code>\"Menu option\":jump target</code>",
        "insert_line_placeholder": "E.g.: char \"text\" or \"narration\"",
        
        # ---------------------------------------------------------------------
        # MAIN SETTINGS DIALOG
        # ---------------------------------------------------------------------
        "dialog_main_settings": "Main Settings",
        
        # Mode Selection Group
        "settings_mode_selection": "File Open Mode Selection",
        "settings_mode_auto": "Automatic (based on filename)",
        "settings_mode_manual": "Always ask",
        
        # Language Settings Group
        "settings_language": "Language Settings",
        "settings_use_detected_lang": "Auto-detect target language in translate mode",
        
        # Project Settings Group
        "settings_project": "Project Settings",
        "settings_auto_prepare": "Auto-prepare RPA/RPYC files when opening project",
        
        # Defaults Group
        "settings_defaults": "Default Values",
        "settings_source_lang": "Source Language:",
        "settings_target_lang": "Target Language:",
        "settings_gemini_model": "Gemini Model:",
        
        # UI Language Group
        "settings_ui_language": "Interface Language",
        "settings_ui_lang_label": "Language:",
        "settings_ui_lang_restart": "Language change requires application restart.",
        
        "settings_save_error": "Failed to save settings.",
        "settings_saved": "Settings saved.",
        
        # ---------------------------------------------------------------------
        # BATCH TRANSLATE
        # ---------------------------------------------------------------------
        "batch_translate_title": "Batch Translation",
        "batch_select_items": "Select items to translate (Ctrl+Click or Shift+Click).",
        "batch_no_selection": "No items selected for batch translation.",
        "batch_cancel_confirm": "Cancel Batch Translation",
        "batch_cancel_message": "Are you sure you want to cancel batch translation?",
        "batch_progress": "Translating: {current}/{total}",
        "batch_cancelled": "Batch translation cancelled.",
        "batch_result_title": "Batch Translation Result",
        "batch_result_message": "Translation completed.\n\nSuccessful: {success}/{total}\nErrors: {errors}\nWarnings: {warnings}",
        
        # ---------------------------------------------------------------------
        # GEMINI STATUS MESSAGES
        # ---------------------------------------------------------------------
        "gemini_no_internet": "AI unavailable: no internet connection.",
        "gemini_no_api_key": "AI unavailable: API key not found.",
        "gemini_no_model": "AI unavailable: model not selected.",
        "gemini_init_error": "Gemini initialization error ({model}). Check key/console.",
        "gemini_initialized": "Gemini ({model}) initialized.",
        "gemini_critical_error": "Critical Gemini initialization error.",
        
        # ---------------------------------------------------------------------
        # ERROR TITLES (QMessageBox)
        # ---------------------------------------------------------------------
        "import_error_title": "Import Error",
        "network_error_title": "Network Error",
        "network_error_gemini": "Gemini Network Error",
        "network_error_gemini_msg": "Could not create Gemini model object.\nCheck your internet connection.",
        
        # ---------------------------------------------------------------------
        # BREAKPOINT/MARKER
        # ---------------------------------------------------------------------
        "breakpoint_added": "Breakpoint added to item {num}.",
        "breakpoint_removed": "Breakpoint removed from item {num}.",
        "no_more_breakpoints": "No more breakpoints.",
        "all_breakpoints_cleared": "All breakpoints ({count}) cleared.",
        "no_breakpoints": "No breakpoints to clear.",
        
        # ---------------------------------------------------------------------
        # FIND/REPLACE
        # ---------------------------------------------------------------------
        "find_no_match": "No match found.",
        "find_match_found": "Match found: item {num}.",
        "find_wrapped": "Wrapped to beginning, continuing...",
        "replace_success": "Replaced '{old}' → '{new}' (item {num}).",
        "replace_no_match": "No match found in selected item.",
        "replace_all_count": "{count} replacements made.",
        "replace_all_none": "No matches found.",
        
        # ---------------------------------------------------------------------
        # PROJECT PREPARATION (project_utils.py)
        # ---------------------------------------------------------------------
        "unrpa_found_path": "INFO: 'unrpa' command found in system PATH.",
        "unrpa_found_module": "INFO: 'unrpa' module available via 'python -m unrpa'.",
        "unrpa_not_found": "WARNING: 'unrpa' command not found in PATH and not available via 'python -m unrpa'. *.rpa extraction will be unavailable.",
        "unrpa_check_install": "         Check 'unrpa' installation (pip install unrpa) and PATH variable.",
        "unrpa_return_code": "         (python -m unrpa --version return code: {code}, stderr: {stderr}...)",
        "python_not_found": "WARNING: Python interpreter '{exe}' not found. Cannot check 'python -m unrpa'.",
        "unrpa_check_timeout": "WARNING: 'python -m unrpa' check timed out.",
        "unrpa_check_error": "WARNING: 'python -m unrpa' check error: {error}",
        
        "unrpyc_missing_decompiler": "WARNING: '{script}' script found, but 'decompiler' folder missing in '{dir}'.",
        "unrpyc_copy_all": "         Make sure you copied ALL contents of unrpyc to 'unrpyc_lib' folder.",
        "unrpyc_found": "INFO: Decompiler script '{script}' and 'decompiler' folder found in '{dir}'.",
        "unrpyc_not_found": "WARNING: Decompiler script '{script}' not found in '{dir}'.",
        "unrpyc_unavailable": "         *.rpyc decompilation will be unavailable.",
        "unrpyc_place_lib": "         Place the full unrpyc library (including decompiler folder) in 'utils/unrpyc_lib'.",
        
        "rpa_already_extracted": "Archive '{name}' was already extracted (marker found).",
        "rpa_extract_attempt": "INFO: Attempting to extract archive: {path} (CWD: {cwd})",
        "rpa_game_not_found": "WARNING: 'game' folder not found in {path}. Extraction will use CWD={path}.",
        "rpa_command_debug": "DEBUG: Running command: {cmd}",
        "rpa_cwd_debug": "DEBUG: CWD directory: {cwd}",
        "rpa_success": "Archive '{name}' successfully processed.",
        "rpa_error_no_file": "unrpa reported 'No such file' for '{name}'.",
        "rpa_error_with_output": "unrpa error for '{name}' (Code: 0, but errors in output).",
        "rpa_error_code": "unrpa error for '{name}' (Code: {code}).",
        "rpa_timeout": "Extraction of '{name}' timed out (>5 minutes).",
        "rpa_command_not_found": "Command '{cmd}' not found.",
        "rpa_unexpected_error": "Unexpected error for '{name}': {error}",
        "rpa_unavailable": "unrpa command unavailable.",
        
        "rpyc_already_decompiled": "'{name}' already decompiled ('{rpy}' found).",
        "rpyc_attempt": "INFO: Attempting decompilation via runpy: {path}",
        "rpyc_success": "'{name}' successfully decompiled.",
        "rpyc_no_output": "runpy for '{name}' succeeded (Code 0), but {rpy} not found. File may be empty or contain only python block.",
        "rpyc_error": "Decompilation error for '{name}' (Code: {code}).",
        "rpyc_unavailable": "unrpyc decompiler script not found.",
        
        "project_path_invalid": "Project path not found or not a folder: {path}",
        "auto_prep_disabled_settings": "INFO: Auto project preparation disabled in settings.",
        
        # ---------------------------------------------------------------------
        # ACTION HANDLER (gui_action_handler.py)
        # ---------------------------------------------------------------------
        "batch_error_deep_translator_not_found": "CRITICAL: deep-translator library not found.",
        "batch_error_google_translator_init_failed": "CRITICAL: Failed to create GoogleTranslator: {error}",
        "batch_task_canceled": "Task canceled by user.",
        "batch_skipped_invalid_index": "Skipped invalid index: {index}",
        "batch_variable_mismatch": "Variable mismatch: {item}",
        "file_line_label": "file line {line}",
        "batch_empty_translation": "Empty translation for item {item}",
        "batch_translation_error": "Translation error for item {item}",
        "edit_ai_failed_init": "Failed to prepare Gemini. Check settings/network.",
        "edit_ai_gemini_unavailable": "Gemini unavailable. Check API key and selected model.",
        "edit_ai_gemini_error_title": "Gemini Error",
        "edit_ai_gemini_error_msg": "Failed to initialize Gemini.\n\nPossible reasons:\n- Invalid or inactive API key.\n- Gemini model not selected or unavailable.\n- Internet connection issues.\n\nCheck Settings -> Gemini API Key and model selection.",
        "edit_ai_select_item": "Select an item to edit with AI.",
        "edit_ai_data_error": "Data error for AI editing.",
        "edit_ai_success": "Item {item} modified using AI.",
        "edit_ai_update_error": "Error updating data after AI.",
        
        # ---------------------------------------------------------------------
        # RENFORGE CORE (renforge_core.py)
        # ---------------------------------------------------------------------
        "core_file_not_found": "File not found: {path}",
        "core_error": "Error: {error}",
        "core_read_error": "Error reading file '{path}': {error}",
        "core_file_loaded": "File {path} loaded ({lines} lines). Found {breakpoints} breakpoints.",
        "core_parser_start": "Starting context parser for file...",
        "core_parser_process": "Processing parser results for 'translate' mode...",
        "core_lang_found": "Detected translation language: {lang}",
        "core_lang_warning": "Warning: Found another block language ('{lang}' after '{detected}' at line {line}). Using first '{detected}'.",
        "core_type_mismatch_warning": "Warning Core L{line}: Original type ('{orig_type}', tag: {orig_tag}) does not match translation line type ('{trans_type}', tag: {trans_tag}). Line skipped.",
        "core_type_unknown_warning": "Warning Core L{line}: Could not determine dialogue/narration type in original comment: '# {comment}'. Translation line '{text}...' skipped.",
        "core_process_complete": "Processing complete. Found {count} items for editing in 'translate' mode.",
        "core_no_pairs_warning": "Warning: 'translate' blocks found, but no original/translation pairs found for editing.",
        "core_save_success": "Changes saved to file: {path}",
        "core_save_error": "Error saving file '{path}': {error}",
        "core_filter_direct": "Filtering parser results for 'direct' mode...",
        "core_direct_found": "Found {count} lines for editing in 'direct' mode.",
        "core_direct_none": "No lines found for editing.",
        "core_rebuild_saving": "Rebuilding and saving file to {path}...",
        "core_reformat_warning": "Warning: Could not reformat line {line}. Using memory version: '{content}'",
        "core_save_success_count": "File successfully saved. Text lines changed: {count}",
        
        "google_trans_unavailable_net": "Google Translate unavailable: no internet connection.",
        "error_no_network_title": "No Network",
        "error_no_network_msg_google": "An internet connection is required to use Google Translate.",
        "google_trans_unavailable_lib": "Google Translate unavailable (deep-translator library).",
        "error_library_not_found_title": "Library Error",
        "error_library_not_found_msg": "Library 'deep-translator' not found.\nGoogle Translate function is unavailable.\n\nInstall it: pip install deep-translator",
        "google_trans_select_item": "Select an item for Google Translate.",
        "google_trans_data_error": "Data error for Google Translate.",
        "google_trans_success": "Item {item} translated by Google.",
        "google_trans_update_error": "Error updating data after Google Translate.",
        
        "batch_google_unavailable_net": "Batch translation unavailable: no internet connection.",
        "error_no_network_msg_batch": "An internet connection is required for batch Google Translate.",
        "batch_google_unavailable_lib": "Google Translate unavailable (deep-translator library).",
        "error_library_not_found_msg_shorter": "Library 'deep-translator' not found.\nInstall it: pip install deep-translator",
        "batch_no_active_tab": "No active tab for batch translation.",
        "batch_no_selected_rows": "No selected rows for batch translation.",
        "batch_data_error": "Data error for batch translation.",
        "batch_lang_required_title": "Language Required",
        "batch_target_lang_required_msg": "Specify the target translation language.",
        "batch_source_lang_required_msg": "Specify the source translation language.",
        "batch_google_title": "Batch Google Translate",
        "batch_confirm_msg": "Translate {count} lines with Google Translate?\nLanguages: '{source}' ({source_code}) -> '{target}' ({target_code})\n\nWARNING: This will overwrite the current text/translation in the selected lines!\n(Verify the language selection is correct)",
        "batch_canceled": "Batch translation cancelled.",
        "batch_progress_msg": "Translating lines...",
        "batch_starting": "Starting batch translation...",
        
        "marker_select_line": "Select a line for the marker.",
        "marker_data_error": "Data error for setting marker.",
        "marker_line_idx_error": "Could not determine file line number for item {item}.",
        "marker_removed": "Marker removed from line {line}.",
        "marker_set": "Marker set on line {line}.",
        "marker_nav_no_markers": "No markers to navigate to.",
        "marker_nav_first": "Navigating to the first marker.",
        "marker_nav_not_found": "Markers not found (error?).",
        "marker_clear_no_data": "No data to clear markers.",
        "marker_clear_none_set": "No markers are set.",
        "confirmation": "Confirmation",
        "marker_clear_confirm_msg": "Remove all markers ({count}) in file {file}?",
        "marker_clear_success": "All markers removed.",
        
        "insert_line_mode_error": "Inserting lines is only available in 'direct' mode.",
        "insert_line_data_error": "Data error for insertion.",
        "insert_line_canceled": "Insertion canceled (empty line).",
        "parsing_error": "Parsing Error",
        "insert_line_parse_error_msg": "Line not recognized as an editable type:\n'{line}'\n(Allowed types: {types})",
        "insert_line_format_error": "Failed to format line for insertion.",
        "insert_line_success": "Line inserted.",
        
        "delete_line_mode_error": "Deleting lines is only available in 'direct' mode.",
        "delete_line_select_error": "Select a line to delete.",
        "delete_line_confirm_title": "Confirm Deletion",
        "delete_line_confirm_msg": "Delete line {line} from file {file}?\n\nText: \"{text}\"",
        "delete_line_success": "Line deleted",
        "marker_removed_short": "marker removed",
        "delete_line_error_title": "Deletion Error",
        "delete_line_index_error": "Critical index error during deletion: {error}\nData might be corrupted!",
        "delete_line_unexpected_error": "Unexpected error during deletion: {error}",
        "delete_line_canceled": "Line deletion cancelled.",
        
        "search_enter_text_error": "Enter search text and open a file.",
        "search_regex_error": "Regex Error: {error}",
        "search_no_data": "No data to search.",
        "search_restarted": "Search for '{text}' started from beginning.",
        "search_found": "Found '{text}' in line {line}.",
        "search_not_found": "Text '{text}' not found.",
        
        "replace_enter_text_error": "Enter search text and select a line to replace.",
        "replace_data_error": "Data or index error for replacement.",
        "replace_format_error_title": "Formatting Error",
        "replace_format_error_msg": "Could not update line {line} in file data after replacement.\nChanges in the table are applied but might be lost on save.",
        "replace_success_finding_next": "Replaced in line {line}. Finding next...",
        "replace_failed": "Failed to perform replacement (re.subn error).",
        "replace_regex_error": "Regex error during replacement: {error}",
        "replace_no_match": "No match in selected line. Finding next...",
        
        "replace_all_enter_text_error": "Enter search/replace text and open a file.",
        "replace_all_no_data": "No data to replace.",
        "replace_all_title": "Replace All?",
        "replace_all_confirm_msg": "Replace all occurrences of {search_mode}'{search}' with '{replace}' in the current file?\nThis action cannot be undone.",
        "replace_all_canceled": "Replace all canceled.",
        "replace_all_starting": "Performing replace all...",
        "replace_all_regex_error": "Line {line}: Regex error during replacement: {error}",
        "replace_all_format_error": "Line {line} (file {file_line}): Error formatting line.",
        "replace_all_update_error": "Line {line}: Error updating file line (index/data).",
        "replace_all_finished": "Finished. Total replacements: {count} in {lines} lines.",
        "replace_all_errors": "Formatting/update errors: {count}.",
        "replace_all_error_title": "Errors during 'Replace All'",
        "replace_all_error_msg_header": "Errors occurred during replace all:",

        # EMPTY FILE WARNINGS
        "warning_empty_translate_mode_title": "No Translatable Items Found",
        "warning_empty_translate_mode_msg": "File loaded in 'Translate' mode, but no editable original/translation pairs were found.\n\nPossible reasons:\n1. The file does not contain standard Ren'Py translation comments (# original text).\n2. The file is empty or contains only non-dialogue code.\n3. Verify the file content or try opening in 'Direct' mode.",
        "warning_empty_direct_mode_title": "No Editable Lines Found",
        "warning_empty_direct_mode_msg": "File loaded in 'Direct' mode, but no editable dialogue or narration lines were found.",

        # UI BUTTONS & GROUPS
        "btn_ai": "AI",
        "btn_gtranslate": "GTranslate",
        "btn_batch_gtranslate": "Batch GTrans.",
        "btn_revert": "Revert",
        "btn_revert_all": "Revert All",
        "btn_marker": "Marker",
        "btn_next_marker": "Next Marker",
        "btn_clear_markers": "Clear Markers",
        "btn_add": "Add",
        "btn_delete": "Delete",
        "group_tools_nav": "Tools & Navigation",
        "group_global_settings": "Global Settings",

        # MENU TITLES
        "menu_tools": "Tools",
        "menu_settings": "Settings",
        "menu_view": "View",
        "menu_toggle_marker": "Toggle Marker",
        "menu_clear_markers": "Clear All Markers",
        "menu_insert_line": "Insert Line (Direct)",
        "menu_delete_line": "Delete Line (Direct)",
        "menu_settings_general": "General...",
        "menu_settings_apikey": "Gemini API Key...",
        "menu_view_project": "Project Panel",
        "menu_view_search": "Search Panel",
    }
}


print("locales.py loaded")
