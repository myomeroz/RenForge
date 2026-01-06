"""
RenForge Settings Module
Handles loading and saving of application settings.
"""

import json
import os
import renforge_config as config


def load_settings():
    """Load settings from JSON file, or return defaults if not found."""
    
    settings_file = config.SETTINGS_FILE_PATH
    default_settings = {
        "api_key": None,
        "mode_selection_method": config.DEFAULT_MODE_SELECTION_METHOD,
        "default_target_language": config.DEFAULT_TARGET_LANG,
        "default_source_language": config.DEFAULT_SOURCE_LANG,
        "default_selected_model": config.DEFAULT_MODEL_NAME,
        "use_detected_target_lang": config.DEFAULT_USE_DETECTED_TARGET_LANG,
        "auto_prepare_project": config.DEFAULT_AUTO_PREPARE_PROJECT,
        "ui_language": config.DEFAULT_UI_LANGUAGE,  # NEW: UI language setting
        
        "window_size_w": 1200, 
        "window_size_h": 800,
        "window_maximized": False,
    }

    if not settings_file.is_file():
        print(f"Ayar dosyası bulunamadı ({settings_file}). Varsayılan değerler kullanılıyor.")
        return default_settings.copy()

    try:
        print(f"Ayarlar yükleniyor: {settings_file}")
        with settings_file.open('r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            
            settings = default_settings.copy()
            if isinstance(loaded_data, dict):
                settings.update(loaded_data) 

                # Validate mode_selection_method
                if settings.get("mode_selection_method") not in [None, "auto", "manual"]:
                     print(f"Uyarı: Geçersiz 'mode_selection_method' değeri ({settings.get('mode_selection_method')}). None'a sıfırlandı.")
                     settings["mode_selection_method"] = None
                     
                # Validate use_detected_target_lang
                if not isinstance(settings.get("use_detected_target_lang"), bool):
                     print(f"Uyarı: Geçersiz 'use_detected_target_lang' değeri. Varsayılan kullanılıyor.")
                     settings["use_detected_target_lang"] = config.DEFAULT_USE_DETECTED_TARGET_LANG
                     
                # Validate auto_prepare_project
                if not isinstance(settings.get("auto_prepare_project"), bool):
                     print(f"Uyarı: Geçersiz 'auto_prepare_project' değeri. Varsayılan kullanılıyor.")
                     settings["auto_prepare_project"] = config.DEFAULT_AUTO_PREPARE_PROJECT
                
                # Validate ui_language
                if settings.get("ui_language") not in ["tr", "en"]:
                    print(f"Uyarı: Geçersiz 'ui_language' değeri ({settings.get('ui_language')}). Varsayılan kullanılıyor.")
                    settings["ui_language"] = config.DEFAULT_UI_LANGUAGE
                
                # Validate window dimensions
                if not isinstance(settings.get("window_size_w"), int):
                    print(f"Uyarı: Geçersiz 'window_size_w' değeri. Varsayılan kullanılıyor.")
                    settings["window_size_w"] = default_settings["window_size_w"]
                if not isinstance(settings.get("window_size_h"), int):
                    print(f"Uyarı: Geçersiz 'window_size_h' değeri. Varsayılan kullanılıyor.")
                    settings["window_size_h"] = default_settings["window_size_h"]
                if not isinstance(settings.get("window_maximized"), bool):
                    print(f"Uyarı: Geçersiz 'window_maximized' değeri. Varsayılan kullanılıyor.")
                    settings["window_maximized"] = default_settings["window_maximized"]

            else:
                print("Uyarı: Ayar dosyası formatı geçersiz (sözlük değil). Varsayılanlar kullanılıyor.")
                settings = default_settings.copy() 

            print("Ayarlar başarıyla yüklendi.")
            return settings
            
    except json.JSONDecodeError:
        print(f"Hata: Ayar dosyası ({settings_file}) bozuk (geçersiz JSON). Varsayılanlar kullanılıyor.")
        return default_settings.copy()
    except Exception as e:
        print(f"Hata: Ayarlar yüklenirken hata ({settings_file}): {e}. Varsayılanlar kullanılıyor.")
        return default_settings.copy()



def save_settings(settings_data):
    """Save settings to JSON file."""
    
    settings_file = config.SETTINGS_FILE_PATH
    try:
        print(f"Ayarlar kaydediliyor: {settings_file}")
        
        # Ensure directory exists
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with settings_file.open('w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
        print("Ayarlar başarıyla kaydedildi.")
        return True
    except Exception as e:
        print(f"Kritik hata: Ayarlar kaydedilemedi ({settings_file}): {e}")
        return False


print("renforge_settings.py loaded")