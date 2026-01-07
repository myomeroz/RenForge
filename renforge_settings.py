"""
RenForge Settings Module
Handles loading and saving of application settings.
"""

import json
import os
import renforge_config as config
from renforge_logger import get_logger
logger = get_logger("settings")


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
        logger.info(f"Ayar dosyası bulunamadı ({settings_file}). Varsayılan değerler kullanılıyor.")
        return default_settings.copy()

    try:
        logger.debug(f"Ayarlar yükleniyor: {settings_file}")
        with settings_file.open('r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            
            settings = default_settings.copy()
            if isinstance(loaded_data, dict):
                settings.update(loaded_data) 

                # Validate mode_selection_method
                if settings.get("mode_selection_method") not in [None, "auto", "manual"]:
                     logger.warning(f"Geçersiz 'mode_selection_method' değeri ({settings.get('mode_selection_method')}). None'a sıfırlandı.")
                     settings["mode_selection_method"] = None
                     
                # Validate use_detected_target_lang
                if not isinstance(settings.get("use_detected_target_lang"), bool):
                     logger.warning(f"Geçersiz 'use_detected_target_lang' değeri. Varsayılan kullanılıyor.")
                     settings["use_detected_target_lang"] = config.DEFAULT_USE_DETECTED_TARGET_LANG
                     
                # Validate auto_prepare_project
                if not isinstance(settings.get("auto_prepare_project"), bool):
                     logger.warning(f"Geçersiz 'auto_prepare_project' değeri. Varsayılan kullanılıyor.")
                     settings["auto_prepare_project"] = config.DEFAULT_AUTO_PREPARE_PROJECT
                
                # Validate ui_language
                if settings.get("ui_language") not in ["tr", "en"]:
                    logger.warning(f"Geçersiz 'ui_language' değeri ({settings.get('ui_language')}). Varsayılan kullanılıyor.")
                    settings["ui_language"] = config.DEFAULT_UI_LANGUAGE
                
                # Validate window dimensions
                if not isinstance(settings.get("window_size_w"), int):
                    logger.warning(f"Geçersiz 'window_size_w' değeri. Varsayılan kullanılıyor.")
                    settings["window_size_w"] = default_settings["window_size_w"]
                if not isinstance(settings.get("window_size_h"), int):
                    logger.warning(f"Geçersiz 'window_size_h' değeri. Varsayılan kullanılıyor.")
                    settings["window_size_h"] = default_settings["window_size_h"]
                if not isinstance(settings.get("window_maximized"), bool):
                    logger.warning(f"Geçersiz 'window_maximized' değeri. Varsayılan kullanılıyor.")
                    settings["window_maximized"] = default_settings["window_maximized"]

            else:
                logger.warning("Ayar dosyası formatı geçersiz (sözlük değil). Varsayılanlar kullanılıyor.")
                settings = default_settings.copy() 

            logger.debug("Ayarlar başarıyla yüklendi.")
            return settings
            
    except json.JSONDecodeError:
        logger.error(f"Ayar dosyası ({settings_file}) bozuk (geçersiz JSON). Varsayılanlar kullanılıyor.")
        return default_settings.copy()
    except Exception as e:
        logger.error(f"Ayarlar yüklenirken hata ({settings_file}): {e}. Varsayılanlar kullanılıyor.")
        return default_settings.copy()



def save_settings(settings_data):
    """Save settings to JSON file."""
    
    settings_file = config.SETTINGS_FILE_PATH
    try:
        logger.debug(f"Ayarlar kaydediliyor: {settings_file}")
        
        # Ensure directory exists
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with settings_file.open('w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
        logger.info("Ayarlar başarıyla kaydedildi.")
        return True
    except Exception as e:
        logger.critical(f"Ayarlar kaydedilemedi ({settings_file}): {e}")
        return False


logger.debug("renforge_settings.py loaded")