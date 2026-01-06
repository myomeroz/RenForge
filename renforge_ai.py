import sys
import os
import time
import re
import json
from pathlib import Path
import socket

import renforge_config as config
import renforge_settings as set

genai = None
GoogleTranslator = None
gemini_model = None
_loaded_api_key = None 
_available_models_cache = None 
no_ai = False 

def is_internet_available(host="8.8.8.8", port=53, timeout=1):

    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        print("--- [is_internet_available] Check successful. ---")
        return True
    except socket.error as ex:
        print(f"--- [is_internet_available] Check failed: {ex} ---")
        return False

def _lazy_import_genai():

    global genai, no_ai

    if 'google.generativeai' in sys.modules and genai is not None:
        return genai

    if genai is None:
        try:
            print("Lazy importing google.generativeai...")
            import google.generativeai as genai_local
            genai = genai_local
            print("Lazy import successful: google.generativeai")
            no_ai = False 
            return genai
        except ImportError:
            print("ERROR: Failed to lazy import google.generativeai. AI features disabled.")

            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox

                is_gui_running = QApplication.instance() is not None
                if is_gui_running:
                     QMessageBox.critical(None, "Ошибка импорта",
                                       "Не удалось импортировать библиотеку 'google-generativeai'.\n"
                                       "Установите ее: pip install google-generativeai\n"
                                       "Функции ИИ будут недоступны.")
            except ImportError:
                 print("INFO: PyQt6 not found, skipping GUI warning for google.generativeai import error.")
            no_ai = True 
            return None
    return genai

def _lazy_import_translator():

    global GoogleTranslator

    if 'deep_translator' in sys.modules and GoogleTranslator is not None:
        return GoogleTranslator

    if GoogleTranslator is None:
        try:
            print("Lazy importing deep_translator...")
            from deep_translator import GoogleTranslator as Translator_local
            GoogleTranslator = Translator_local
            print("Lazy import successful: deep_translator.GoogleTranslator")
            return GoogleTranslator
        except ImportError:
            print("ERROR: Failed to lazy import deep_translator. Translate features disabled.")

            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox
                is_gui_running = QApplication.instance() is not None
                if is_gui_running:
                    QMessageBox.critical(None, "Ошибка импорта",
                                   "Не удалось импортировать библиотеку 'deep-translator'.\n"
                                   "Установите ее: pip install deep-translator\n"
                                   "Функции перевода Google будут недоступны.")
            except ImportError:
                 print("INFO: PyQt6 not found, skipping GUI warning for deep_translator import error.")
            return None 
    return GoogleTranslator

def get_google_languages() -> dict | None:

    if not is_internet_available():
        print("Cannot get languages: Internet connection not available.")
        return None

    Translator = _lazy_import_translator()
    if Translator is None:
        print("Cannot get languages: deep_translator not available.")
        return None
    try:

        name_code_dict = Translator().get_supported_languages(as_dict=True)

        code_name_dict = {code: name for name, code in name_code_dict.items()}
        return code_name_dict
    except Exception as e:
        print(f"Error getting supported languages from deep_translator: {e}")
        return None

def load_api_key():

    print("--- [load_api_key] Called. Attempting to load settings... ---") 
    settings = set.load_settings() 

    if not isinstance(settings, dict):
        print(f"--- [load_api_key] ERROR: set.load_settings did not return a dictionary (returned {type(settings)}). Cannot get 'api_key'. ---")
        return None
    key = settings.get("api_key") 
    if key:

        if isinstance(key, str) and key.strip():
            masked_key = f"...{key[-4:]}" if len(key) >=4 else key
            print(f"--- [load_api_key] Found valid key ending with {masked_key} in settings. Type: {type(key)}. ---") 
            return key 
        else:
            print(f"--- [load_api_key] Found 'api_key' in settings, but it's not a valid non-empty string. Type: {type(key)}. Value: '{key}'. Returning None. ---")
            return None 
    else:
        print(f"--- [load_api_key] Key 'api_key' not found or is None in loaded settings. Returning None. ---") 
        return None 

def save_api_key(api_key):

    settings = set.load_settings() 

    if not isinstance(settings, dict):
         settings = {}
         print("Warning: set.load_settings не вернул словарь в save_api_key. Начинаем с чистого листа.")

    action_taken = "unchanged" 
    current_api_key = settings.get("api_key")

    if api_key: 
        if current_api_key != api_key:
            settings["api_key"] = api_key 
            action_taken = "saved" 
            print(f"Подготовка к сохранению/обновлению API ключа в {config.SETTINGS_FILE_PATH}")
        else:

            print(f"API ключ не изменился, действие не требуется.")
            return "unchanged", settings 
    else: 
        if current_api_key is not None:
            settings.pop("api_key", None) 
            action_taken = "removed" 
            print(f"Подготовка к удалению API ключа из {config.SETTINGS_FILE_PATH}")
        else:

            print(f"API ключ отсутствует в настройках, удаление не требуется.")
            return "unchanged", settings 

    if action_taken in ["saved", "removed"]:
        print(f"Попытка сохранения настроек: {settings}")

        if set.save_settings(settings): 
            if action_taken == "saved":
                print(f"API ключ успешно сохранен/обновлен.")
            elif action_taken == "removed":
                print(f"API ключ успешно удален.")
            return action_taken, settings 
        else:

            print(f"Ошибка при сохранении файла настроек '{config.SETTINGS_FILE_PATH}' во время обновления API ключа.")

            return "error", settings 
    else:

        return "unchanged", settings 

def prompt_for_api_key(force_prompt=False):

    global _loaded_api_key
    current_key = load_api_key()
    if current_key and not force_prompt:
        return current_key

    print("-" * 30)
    print("Требуется API ключ Google Gemini.")
    if current_key:
        print(f"Текущий ключ: ...{current_key[-4:]}")
        try:
            change = input("Хотите изменить ключ? (y/n): ").lower()
            if change != 'y':
                return current_key
        except (EOFError, KeyboardInterrupt):
             print("\nВвод отменен.")
             return current_key 

    else:
        print("Ключ не найден.")

    while True:
        try:
            new_key = input("Введите ваш Google API ключ: ").strip()
            if new_key:
                if save_api_key(new_key):
                    return new_key
                else:

                    print("Повторите попытку.")
                    continue 
            else:
                print("Ключ не может быть пустым.")
        except EOFError:
            print("\nВвод отменен.")
            return None 
        except KeyboardInterrupt:
            print("\nВвод прерван.")
            return None 

def get_available_models(force_refresh=False):

    global _available_models_cache, no_ai, genai
    print(f"--- [get_available_models] Called. Force refresh: {force_refresh} ---")

    if _available_models_cache and not force_refresh:
        print(f"--- [get_available_models] Returning cached models: {len(_available_models_cache)} models ---")
        return _available_models_cache

    genai_module = _lazy_import_genai()
    if no_ai or genai_module is None:
        print("--- [get_available_models] Failed: AI module not available or import failed. ---")
        return None

    if not load_api_key():
         print("--- [get_available_models] Failed: API key not configured. ---")
         no_ai = True 
         _available_models_cache = None 
         return None

    if not is_internet_available():
        print("--- [get_available_models] Failed: Internet connection not available. ---")
        no_ai = True 
        _available_models_cache = None 
        return None

    try:
        print("--- [get_available_models] Attempting to list models via API... ---")
        available_models = []

        for m in genai_module.list_models():

            if 'generateContent' in m.supported_generation_methods and 'embed' not in m.name.lower():

                available_models.append(m.name)

        if available_models:

            available_models.sort()
            _available_models_cache = available_models 
            print(f"--- [get_available_models] Success. Found {len(available_models)} models. Caching result. ---")

            return available_models
        else:
            print("--- [get_available_models] Warning: API returned no suitable models. ---")
            _available_models_cache = [] 
            return []
    except ImportError:

        print("--- [get_available_models] ERROR: google.generativeai not imported. ---")
        no_ai = True
        _available_models_cache = None
        return None
    except Exception as e:

        error_str = str(e).lower()
        print(f"--- [get_available_models] ERROR: Failed to list models from Gemini API: {e} ---")
        no_ai = True 
        _available_models_cache = None 

        network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "404", "503"]
        auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]

        is_network_error = any(keyword in error_str for keyword in network_error_keywords)
        is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)

        if is_network_error:
             print("--- [get_available_models] Error seems network-related. Check internet connection. ---")
        elif is_auth_error:
             print("--- [get_available_models] Error likely related to API Key. ---")
        else:
             print("--- [get_available_models] An unexpected error occurred. ---")

        return None

def configure_gemini(model_name_to_use=None):

    global gemini_model, no_ai, genai 

    if gemini_model is None or no_ai:
        print("--- [configure_gemini] Checking internet connection before configuration attempt... ---")
        if not is_internet_available():
            print("--- [configure_gemini] Failed: Internet connection not available. ---")
            no_ai = True
            gemini_model = None

            return False

    if genai and gemini_model and not no_ai and gemini_model.model_name.endswith(model_name_to_use):
        print(f"--- Skipping configure_gemini: Already configured for {model_name_to_use} ---")
        return True 

    if model_name_to_use is None:
        model_name_to_use = config.DEFAULT_MODEL_NAME
    print(f"Target model: {model_name_to_use}") 

    genai_module = _lazy_import_genai()
    if genai_module is None:
        no_ai = True 
        gemini_model = None 
        print("configure_gemini failed: google.generativeai module not imported.")
        print("--- Ending configure_gemini (failure: no module) ---") 
        return False 

    api_key = load_api_key()

    is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None

    if api_key:

        masked_key = f"...{api_key[-4:]}" if len(api_key) >= 4 else api_key
        print(f"API Key loaded successfully (ends with: {masked_key})") 
    else:
        print("API Key not found in settings.") 
        if not is_gui:
            print("GUI not detected, prompting for API key in console...") 
            api_key = prompt_for_api_key(force_prompt=True)
        else:

            no_ai = True
            gemini_model = None
            print("configure_gemini failed: API Key missing (GUI detected). User should add via Settings.")

            print("--- Ending configure_gemini (failure: no key in GUI) ---") 
            return False 

    if not api_key and not is_gui:
        print("\nКлюч API не найден в файле настроек (configure_gemini). Запрос ключа...")
        api_key = prompt_for_api_key(force_prompt=True) 

    if not api_key:
        no_ai = True
        gemini_model = None
        print("configure_gemini failed: API Key is still missing after prompt (or prompt cancelled).")
        print("--- Ending configure_gemini (failure: no key after prompt) ---") 
        return False 

    try:

        print("--- [configure_gemini] Checking internet connection before creating model object... ---")
        if not is_internet_available():
             print("--- [configure_gemini] Failed: Internet connection lost before creating model object. ---")
             no_ai = True
             gemini_model = None

             is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None
             if is_gui:
                try:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(None, "Сетевая ошибка Gemini", "Не удалось создать объект модели Gemini.\nПроверьте ваше интернет-соединение.")
                except Exception as msg_err:
                    print(f"Could not show GUI error message box: {msg_err}")
             return False
        masked_key_for_config = f"...{api_key[-4:]}" if len(api_key) >= 4 else api_key
        print(f"Configuring genai with key ending in {masked_key_for_config}") 
        genai_module.configure(api_key=api_key)
        print("genai.configure called successfully.") 

        print(f"Attempting to create/verify model: {model_name_to_use}") 

        gemini_model = genai_module.GenerativeModel(
             model_name_to_use
        )

        print(f"--- [configure_gemini] Inside try block AFTER assignment: gemini_model is None={gemini_model is None}, type={type(gemini_model)} ---") 

        print(f"Model '{model_name_to_use}' object created successfully (further verification may occur on first use).") 
        no_ai = False 
        print("--- Ending configure_gemini (success, model object created) ---") 
        return True 
    except ImportError:

        print("--- [configure_gemini] ERROR: google.generativeai not imported. ---")
        no_ai = True
        gemini_model = None
        return False
    except Exception as e:

        no_ai = True 
        gemini_model = None 
        error_message = f"Error during Gemini configuration or model creation: {e}"
        print(error_message) 

        error_str = str(e).lower()
        gui_message_title = "Ошибка Gemini"
        gui_message_text = f"Не удалось настроить Gemini API или создать модель '{model_name_to_use}'.\n\nОшибка: {e}"

        network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "404", "503"]
        auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]

        is_network_error = any(keyword in error_str for keyword in network_error_keywords)
        is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)

        if is_network_error:
            print("Error seems network-related during configuration. Check internet connection.")
            gui_message_title = "Сетевая ошибка Gemini"
            gui_message_text = f"Не удалось связаться с Gemini API.\nПроверьте ваше интернет-соединение.\n\nОшибка: {e}"
        elif is_auth_error:

            print("Error likely related to API Key validity or permissions.")
            gui_message_title = "Ошибка API ключа Gemini"
            gui_message_text = (f"Не удалось настроить Gemini API.\n"
                                f"Проверьте правильность и действительность вашего API ключа и доступ к модели '{model_name_to_use}'.\n\n"
                                f"Ошибка: {e}")
        elif ("not found" in error_str) and model_name_to_use in str(e):

             print(f"Error: Model '{model_name_to_use}' not found or unavailable for this key.")
             gui_message_title = "Модель Gemini не найдена"
             gui_message_text = f"Указанная модель '{model_name_to_use}' не найдена или недоступна для вашего ключа.\nПроверьте имя модели или выберите другую.\n\nОшибка: {e}"
        else:
             print("An unexpected error occurred during configuration.")

        is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None
        if is_gui:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, gui_message_title, gui_message_text)
            except Exception as msg_err:
                print(f"Could not show GUI error message box: {msg_err}")

        print("--- Ending configure_gemini (failure: exception) ---")
        return False 

def refine_text_with_gemini(original_text, current_text, user_instruction, context_info,
                            source_lang, target_lang, mode, character_tag=None):

    global gemini_model, no_ai
    if no_ai or gemini_model is None:
        return (None, "Модель Gemini не инициализирована или недоступна.")

    if not is_internet_available():
        print("--- [refine_text_with_gemini] Failed: Internet connection not available. ---")

        return (None, "Отсутствует подключение к интернету для запроса к Gemini.")

    context_prompt = "Context (surrounding lines):\n"
    marker = ""
    line_num_str = ""
    tag_prefix = ""
    display_content = ""
    text_to_show = ""

    for info in context_info:
        marker = ">> " if info["is_target"] else "   " 
        line_num_str = f"L{info['line_index']+1}:"
        tag_prefix = f"[{info['character_tag']}] " if info.get('character_tag') else ""

        if mode == "translate":
            if info.get("is_translation_line"): 
                context_prompt += f"{marker}{line_num_str} Original ({source_lang}): {tag_prefix}{info['original']}\n"
                context_prompt += f"{marker}{line_num_str} Current Translation ({target_lang}): {tag_prefix}{info['translated']}\n\n"
            elif info.get("is_original_comment"): 

                 context_prompt += f"{marker}{line_num_str} Original Line ({source_lang}): {tag_prefix}{info['original']}\n\n"

            else: 
                display_content = (info['content'][:75] + '...') if len(info['content']) > 75 else info['content']
                context_prompt += f"{marker}{line_num_str} Raw Line: {tag_prefix}{display_content}\n\n"
        else: 
            text_to_show = info.get('current_text') 
            if text_to_show is not None and info.get("is_editable"): 
                 context_prompt += f"{marker}{line_num_str} Editable Text ({target_lang}): {tag_prefix}{text_to_show}\n\n"

            else: 
                display_content = (info['content'][:75] + '...') if len(info['content']) > 75 else info['content']
                context_prompt += f"{marker}{line_num_str} Raw Line: {display_content}\n\n"

    character_info = f"The character speaking is '{character_tag}'." if character_tag else "This is narration or menu text."

    if mode == "translate":
        prompt = (
            f"You are an expert editor revising translations for a Ren'Py visual novel script.\n"
            f"Your task is to refine the 'Current Translation' based on the 'Original Text' and the 'User Instruction', considering the provided 'Context'.\n"
            f"{character_info}\n"
            f"Source Language: {source_lang}\n"
            f"Target Language: {target_lang}\n\n"
            f"Original Text:\n\"\"\"\n{original_text}\n\"\"\"\n\n"
            f"Current Translation:\n\"\"\"\n{current_text}\n\"\"\"\n\n"
            f"User Instruction:\n\"\"\"\n{user_instruction}\n\"\"\"\n\n"
            f"{context_prompt}"
            f"Constraints:\n"
            f"- Preserve the original meaning and intent.\n"
            f"- Maintain the character's voice and tone (if applicable).\n"
            f"- Ensure grammatical correctness and natural phrasing in the *{target_lang}* language.\n"
            f"- Keep Ren'Py tags (like {{w}}, {{p}}) and text variables (like [variable_name]) unchanged.\n"
            f"- ONLY output the refined translation text, without any explanations or quotation marks around it.\n\n"
            f"Refined Translation ({target_lang}):\n"
        )
    else: 
        prompt = (
            f"You are an expert editor revising a script for a Ren'Py visual novel.\n"
            f"Your task is to refine the 'Current Text' based on the 'User Instruction', considering the provided 'Context'.\n"
            f"{character_info}\n"
            f"Language: {target_lang}\n\n"
            f"Current Text:\n\"\"\"\n{current_text}\n\"\"\"\n\n"
            f"User Instruction:\n\"\"\"\n{user_instruction}\n\"\"\"\n\n"
            f"{context_prompt}"
            f"Constraints:\n"
            f"- Preserve the original meaning and intent.\n"
            f"- Maintain the character's voice and tone (if applicable).\n"
            f"- Ensure grammatical correctness and natural phrasing in the *{target_lang}* language.\n"
            f"- Keep Ren'Py tags (like {{w}}, {{p}}) and text variables (like [variable_name]) unchanged.\n"
            f"- ONLY output the refined text, without any explanations or quotation marks around it.\n\n"
            f"Refined Text ({target_lang}):\n"
        )

    retries = 3
    for attempt in range(retries):
        try:
            print(f"--- DEBUG: Before generate_content call (Attempt {attempt+1}): gemini_model type = {type(gemini_model)}, value = {gemini_model} ---")
            if not hasattr(gemini_model, 'generate_content') or not callable(gemini_model.generate_content):
                 error_msg = f"Ошибка: gemini_model (type: {type(gemini_model)}) не имеет вызываемого метода 'generate_content'."
                 print(f"  {error_msg}")
                 no_ai = True 
                 return (None, error_msg)
            print(f"  Attempt {attempt + 1}/{retries}: Sending refinement request to Gemini...")

            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            try:
                 response = gemini_model.generate_content(prompt, safety_settings=safety_settings)
                 print(f"--- DEBUG: API call returned. Response type: {type(response)} ---")
            except TypeError as te:

                 print(f"--- CRITICAL TYPE ERROR during API call: {te} ---")
                 print(f"    gemini_model type at time of error: {type(gemini_model)}")
                 print(f"    gemini_model.generate_content type: {type(gemini_model.generate_content) if hasattr(gemini_model, 'generate_content') else 'N/A'}")
                 no_ai = True 
                 return (None, f"TypeError при вызове Gemini API: {te}. Проверьте состояние модели.")
            except Exception as api_call_e:

                 print(f"--- ERROR during actual API call: {type(api_call_e).__name__}: {api_call_e} ---")

                 raise api_call_e

            time.sleep(config.REQUEST_DELAY_SECONDS)

            if response.parts:
                refined_text = response.text.strip()

                if refined_text.startswith(''):
                    refined_text = refined_text[3:-3].strip()
                elif refined_text.startswith('"') and refined_text.endswith('"'):
                    refined_text = refined_text[1:-1].strip()

                print(f"  Gemini suggested: \"{refined_text}\"")

                text_before_refinement = current_text
                original_vars = re.findall(r'(\[.*?\])', text_before_refinement) 
                refined_vars = re.findall(r'(\[.*?\])', refined_text)

                if original_vars != refined_vars:
                     warning_msg = f"  Warning: Variable set [...] might have changed! Original: {original_vars}, Refined: {refined_vars}"
                     print(warning_msg)

                return (refined_text, None) 
            else:

                error_msg = "Received empty or blocked response from Gemini."
                block_reason = None
                finish_reason = None
                try:

                     if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                          block_reason = response.prompt_feedback.block_reason

                     if hasattr(response, 'candidates') and response.candidates:
                         finish_reason = response.candidates[0].finish_reason

                     if block_reason:
                         error_msg += f" Block Reason: {block_reason}."
                     elif finish_reason and finish_reason != 1: 
                          error_msg += f" Finish Reason: {finish_reason}." 
                     else:
                          error_msg += " Reason unknown."

                except Exception as feedback_error:
                    print(f"  Error retrieving feedback from Gemini response: {feedback_error}")
                    error_msg += " Could not retrieve specific reason."

                print(f"  Warning: {error_msg}")

                if attempt + 1 == retries:
                    return (None, error_msg)

                delay = config.REQUEST_DELAY_SECONDS * (attempt + 2)
                print(f"  Retrying after {delay} seconds...")
                time.sleep(delay)
                continue 

        except Exception as e:

            error_msg = f"Error calling Gemini API (Attempt {attempt + 1}/{retries}): {e}"
            print(f"  {error_msg}")
            error_str = str(e).lower()

            auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]
            rate_limit_keywords = ["rate limit", "429"]
            network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "503"] 

            is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)
            is_rate_limit = any(keyword in error_str for keyword in rate_limit_keywords)
            is_network_error = any(keyword in error_str for keyword in network_error_keywords) 

            if is_auth_error:
                 final_error = f"Authentication/Permission error with Gemini API: {e}. Check your API key."
                 print(f"  {final_error}")
                 no_ai = True 
                 return (None, final_error)

            if is_network_error:
                 final_error = f"Network error contacting Gemini API (during request): {e}."
                 print(f"  {final_error}")

                 return (None, final_error)

            if is_rate_limit:

                pass 

            elif attempt + 1 == retries:
                final_error = f"Failed to refine text after {retries} attempts. Last error: {e}"
                print(f"  {final_error}")

                return (None, final_error)
            else:

                time.sleep(config.REQUEST_DELAY_SECONDS * 2)

    return (None, f"Failed to get response from Gemini after {retries} attempts.")

def refine_text_with_gemini_translate(original_text, current_translation, user_instruction, context_info, source_lang, target_lang, character_tag=None):

    return refine_text_with_gemini(original_text, current_translation, user_instruction, context_info,
                                   source_lang, target_lang, "translate", character_tag)

def refine_text_with_gemini_direct(current_text, user_instruction, context_info, target_lang, character_tag=None):

    return refine_text_with_gemini(current_text, current_text, user_instruction, context_info,
                                   None, target_lang, "direct", character_tag) 