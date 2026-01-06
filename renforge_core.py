import re
import os

import renforge_config as config
from locales import tr

import renforge_parser as parser

def prepare_lines_for_saving(current_file_lines, current_breakpoints):

    prepared_lines = []

    breakpoint_pattern_end = re.compile(re.escape(config.BREAKPOINT_MARKER) + r'\s*$')

    for i, line in enumerate(current_file_lines):

        line_without_marker = breakpoint_pattern_end.sub('', line).rstrip()

        if i in current_breakpoints:

            prepared_lines.append(line_without_marker + " " + config.BREAKPOINT_MARKER)
        else:

            prepared_lines.append(line_without_marker if line.strip() else line)
    return prepared_lines

def detect_file_mode(file_path):

    print(f"--- [detect_file_mode] Detecting mode for: {file_path} ---")

    loaded_file_lines, _ = load_and_parse_base(file_path)
    if loaded_file_lines is None:
        print(f"--- [detect_file_mode] Warning: Could not load file. Defaulting to 'direct'. ---")
        return "direct" 

    has_translate_blocks = False
    has_screen_definitions = False

    screen_def_regex = parser.RE_SCREEN_START
    translate_block_regex = parser.RE_TRANSLATE_START

    print(f"--- [detect_file_mode] Scanning for translate blocks and screen definitions...")
    for line in loaded_file_lines:
        stripped_line = line.lstrip()

        if stripped_line.startswith('#'):
            continue

        if translate_block_regex.match(line):
            has_translate_blocks = True

        if screen_def_regex.match(line):
            has_screen_definitions = True

    print(f"--- [detect_file_mode] Analysis results:")
    print(f"    Has 'translate' blocks: {has_translate_blocks}")
    print(f"    Has 'screen' definitions: {has_screen_definitions}")

    if has_screen_definitions:
        print(f"--- [detect_file_mode] Decision: 'direct' (Screen definitions found) ---")
        return "direct"

    if has_translate_blocks:
        print(f"--- [detect_file_mode] Decision: 'translate' (Translate blocks found, no screen definitions) ---")
        return "translate"

    print(f"--- [detect_file_mode] Decision: 'direct' (Default - No screen or translate blocks found) ---")
    return "direct"

def load_and_parse_base(input_path):

    try:

        input_path_obj = config.Path(input_path)
        if not input_path_obj.is_file():
             raise FileNotFoundError(tr("core_file_not_found", path=input_path))

        raw_lines = input_path_obj.read_text(encoding='utf-8-sig').splitlines()
    except FileNotFoundError as e:
        print(tr("core_error", error=e))
        return None, None 
    except Exception as e:
        print(tr("core_read_error", path=input_path, error=e))
        return None, None 

    loaded_file_lines = []
    loaded_breakpoints = set()

    breakpoint_pattern = re.compile(r'^(.*?)(\s+' + re.escape(config.BREAKPOINT_MARKER) + r'\s*)$')

    for i, raw_line in enumerate(raw_lines):
        match = breakpoint_pattern.search(raw_line)
        if match:
            line_content = match.group(1) 
            loaded_breakpoints.add(i) 
            loaded_file_lines.append(line_content) 
        else:
            loaded_file_lines.append(raw_line) 

    print(tr("core_file_loaded", path=input_path, lines=len(loaded_file_lines), breakpoints=len(loaded_breakpoints)))
    return loaded_file_lines, loaded_breakpoints

def load_and_parse_translate_file(input_path):

    loaded_file_lines, loaded_breakpoints = load_and_parse_base(input_path)
    if loaded_file_lines is None:
        return [], [], set(), None 

    print(tr("core_parser_start"))

    all_parsed_items = parser.parse_file_contextually(loaded_file_lines)

    print(tr("core_parser_process"))
    parsed_translatable_items = []
    detected_language = None
    last_old_item = None 
    last_original_comment_item = None 

    for item in all_parsed_items:
        item_index = item['line_index']
        item_type = item['type']
        item_context = item['context']
        item_context_data = item.get('context_data', {})
        item_lang = item_context_data.get('language') if item_context_data else None

        if detected_language is None and item_lang:
            detected_language = item_lang
            print(tr("core_lang_found", lang=detected_language)) 
        elif detected_language and item_lang and detected_language != item_lang:
            print(tr("core_lang_warning", lang=item_lang, detected=detected_language, line=item_index+1))

        if item_context == parser.CONTEXT_TRANSLATE_STRINGS:
            if item_type == "translate_old":
                last_old_item = item 
                last_original_comment_item = None 
            elif item_type == "translate_new" and last_old_item:

                new_text = item['text']
                final_item = {
                    "original_line_index": last_old_item['line_index'],
                    "translated_line_index": item_index,
                    "original_text": last_old_item['text'],
                    "translated_text": new_text,
                    "initial_text": new_text,
                    "is_modified_session": False,
                    "block_language": last_old_item.get('context_data', {}).get('language'),
                    "character_trans": None, 
                    "character_tag": None,   
                    "type": "string", 
                    "parsed_data": item['parsed_data'], 
                    "has_breakpoint": item['has_breakpoint'] 
                }

                if 'reconstruction_rule' not in final_item['parsed_data']:
                    final_item['parsed_data']['reconstruction_rule'] = 'translate_new'

                parsed_translatable_items.append(final_item)
                last_old_item = None 
            else:

                last_old_item = None

        elif item_context == parser.CONTEXT_TRANSLATE:
            if item_type == "translate_potential_original":

                last_original_comment_item = item
                last_old_item = None 

            elif item_type == "translate_translation" and last_original_comment_item:

                original_parsed_data = last_original_comment_item.get('parsed_data', {})
                original_type = original_parsed_data.get('original_type') 
                original_char_tag = original_parsed_data.get('original_char_tag')

                original_text_content = last_original_comment_item['text']

                translation_char_tag = item.get("character_tag") 
                translation_base_type = "dialogue" if translation_char_tag else "narration"
                translated_text = item['text']

                if original_type:

                    if original_type == translation_base_type:

                        final_item = {
                            "original_line_index": last_original_comment_item['line_index'],
                            "translated_line_index": item_index,
                            "original_text": original_text_content, 
                            "translated_text": translated_text, 
                            "initial_text": translated_text,
                            "is_modified_session": False,
                            "block_language": item_lang,
                            "character_trans": translation_char_tag, 
                            "character_tag": original_char_tag,      
                            "type": original_type,                   
                            "parsed_data": item['parsed_data'],      
                            "has_breakpoint": item['has_breakpoint'] 
                        }

                        rec_rule = 'standard' if translation_char_tag else 'narration'
                        final_item['parsed_data']['reconstruction_rule'] = rec_rule

                        parsed_translatable_items.append(final_item)

                        last_original_comment_item = None 
                    else:

                        print(tr("core_type_mismatch_warning", line=item_index+1, orig_type=original_type, orig_tag=original_char_tag, trans_type=translation_base_type, trans_tag=translation_char_tag))
                        last_original_comment_item = None 
                else:

                    print(tr("core_type_unknown_warning", line=item_index+1, comment=original_parsed_data.get('original_full_comment_content', ''), text=translated_text[:30]))
                    last_original_comment_item = None 
            else:

                if item_type != "translate_potential_original": 
                     last_original_comment_item = None

        else:

            if item_context != parser.CONTEXT_TRANSLATE and item_context != parser.CONTEXT_TRANSLATE_STRINGS:
                last_old_item = None
                last_original_comment_item = None

    print(tr("core_process_complete", count=len(parsed_translatable_items)))
    if not parsed_translatable_items and detected_language:
        print(tr("core_no_pairs_warning"))

    return parsed_translatable_items, loaded_file_lines, loaded_breakpoints, detected_language

def save_translate_file(output_path, current_file_lines, current_breakpoints):

    lines_to_save = prepare_lines_for_saving(current_file_lines, current_breakpoints)
    try:

        output_path_obj = config.Path(output_path)
        output_path_obj.write_text('\n'.join(lines_to_save) + '\n', encoding='utf-8')
        print(tr("core_save_success", path=output_path))
        return True 
    except Exception as e:
        print(tr("core_save_error", path=output_path, error=e))
        return False 

def get_context_for_translate_item(item_index, items_list, lines_list):

    if not items_list or not (0 <= item_index < len(items_list)):
        return [] 

    target_item = items_list[item_index]

    target_line_index = target_item['translated_line_index']

    original_line_index = target_item['original_line_index']

    start_line_idx = max(0, target_line_index - config.CONTEXT_LINES)
    end_line_idx = min(len(lines_list), target_line_index + config.CONTEXT_LINES + 1)

    context_lines_info = []

    item_lookup_trans = {item['translated_line_index']: item for item in items_list}
    item_lookup_orig = {item['original_line_index']: item for item in items_list}

    for i in range(start_line_idx, end_line_idx):

        if i >= len(lines_list):
            break
        line_content = lines_list[i]

        info = {
            "line_index": i,
            "is_target": (i == target_line_index), 
            "is_original_of_target": (i == original_line_index), 
            "content": line_content,
            "original": None,         
            "translated": None,       
            "is_translation_line": False, 
            "is_original_comment": False, 
            "character_tag": None     
        }

        char_tag = None 

        if i in item_lookup_trans:
             item_data = item_lookup_trans[i]
             info["original"] = item_data['original_text']
             info["translated"] = item_data['translated_text']
             info["is_translation_line"] = True

             char_tag = item_data.get('character_trans')

        elif i in item_lookup_orig:
             item_data = item_lookup_orig[i]
             info["original"] = item_data['original_text']

             info["is_original_comment"] = True

             char_tag = item_data.get('character_tag')

        else:

             if line_content.lstrip().startswith('#'):

                 pass
             else:

                 match_dialogue = parser.RE_DIALOGUE.match(line_content)
                 if match_dialogue:
                     char_tag = match_dialogue.group(2) 

        info["character_tag"] = char_tag 
        context_lines_info.append(info)

    return context_lines_info

def load_and_parse_direct_file(input_path):

    loaded_file_lines, loaded_breakpoints = load_and_parse_base(input_path)
    if loaded_file_lines is None:
        return [], [], set()

    print(f"DEBUG Core: Calling parser.parse_file_contextually for Direct Mode on {input_path}") 
    all_parsed_items = parser.parse_file_contextually(loaded_file_lines)
    print(f"DEBUG Core: Parser finished for Direct Mode. Found {len(all_parsed_items) if all_parsed_items is not None else 'None'} raw items.") 

    print(tr("core_filter_direct"))
    parsed_direct_items = []

    editable_types_direct = {
        "dialogue",
        "narration",
        "choice",
        "screen_button",
        "screen_label",
        "screen_text_statement",
        "screen_text_property",
        "variable" 
    }

    for item in all_parsed_items:

        if item['context'] in [parser.CONTEXT_TRANSLATE, parser.CONTEXT_TRANSLATE_STRINGS]:
             if item['type'] == 'translate_potential_original': continue
             continue

        if item['type'] in editable_types_direct:
            text = item['text']
            direct_item = {
                "line_index": item['line_index'],
                "original_text": text,
                "current_text": text,
                "initial_text": text,
                "is_modified_session": False,
                "character_tag": item.get('character_tag'), 
                "variable_name": item.get('variable_name'), 
                "type": item['type'],
                "parsed_data": item['parsed_data'],
                "has_breakpoint": item['has_breakpoint']
            }
            parsed_direct_items.append(direct_item)

    print(tr("core_direct_found", count=len(parsed_direct_items)))
    if not parsed_direct_items:
        print(tr("core_direct_none"))
    return parsed_direct_items, loaded_file_lines, loaded_breakpoints

def save_direct_file(output_path, current_items_list, current_file_lines, current_breakpoints):

    print(tr("core_rebuild_saving", path=output_path))

    items_by_index = {item['line_index']: item for item in current_items_list}
    new_file_lines_temp = [] 
    saved_count = 0 

    for i, original_line_in_memory in enumerate(current_file_lines):

        if i in items_by_index:
            item = items_by_index[i]

            new_line = parser.format_line_from_components(item, item['current_text'])
            if new_line is not None:
                new_file_lines_temp.append(new_line)

                if item['current_text'] != item['original_text']:
                    saved_count += 1
            else:

                print(tr("core_reformat_warning", line=i+1, content=original_line_in_memory))
                new_file_lines_temp.append(original_line_in_memory)
        else:

            new_file_lines_temp.append(original_line_in_memory)

    lines_to_save = prepare_lines_for_saving(new_file_lines_temp, current_breakpoints)

    try:

        output_path_obj = config.Path(output_path)
        output_path_obj.write_text('\n'.join(lines_to_save) + '\n', encoding='utf-8')
        print(tr("core_save_success_count", count=saved_count))
        return True 
    except Exception as e:
        print(tr("core_save_error", path=output_path, error=e))
        return False 

def get_context_for_direct_item(item_index, items_list, lines_list):

    if not items_list or not (0 <= item_index < len(items_list)):
        return []

    target_item = items_list[item_index]
    target_line_index = target_item['line_index'] 

    start_line_idx = max(0, target_line_index - config.CONTEXT_LINES)
    end_line_idx = min(len(lines_list), target_line_index + config.CONTEXT_LINES + 1)

    context_lines_info = []

    items_lookup = {item['line_index']: item for item in items_list}

    for i in range(start_line_idx, end_line_idx):

        if i >= len(lines_list):
            break
        line_content = lines_list[i]

        info = {
            "line_index": i,
            "is_target": (i == target_line_index),
            "content": line_content,
            "is_editable": False, 
            "character_tag": None,
            "current_text": None 
        }

        char_tag = None
        var_name = None 
        current_text = None

        if i in items_lookup:
            item_data = items_lookup[i]
            info["is_editable"] = True
            char_tag = item_data.get('character_tag')
            var_name = item_data.get('variable_name') 
            current_text = item_data.get('current_text')

        else:
             if line_content.lstrip().startswith('#'): pass 
             else:

                 match_var_dollar = parser.RE_VAR_ASSIGN_DOLLAR.match(line_content)
                 if match_var_dollar:
                     var_name = match_var_dollar.group(2) 
                     current_text = match_var_dollar.group(3).replace('\\"', '"')
                 else:

                     match_var_py = parser.RE_VAR_ASSIGN_PYTHON.match(line_content)
                     if match_var_py:
                          var_name = match_var_py.group(2) 
                          current_text = match_var_py.group(3).replace('\\"', '"')

                     elif parser.RE_DIALOGUE.match(line_content): 
                          match_dialogue = parser.RE_DIALOGUE.match(line_content)
                          if match_dialogue and match_dialogue.group(2) not in parser.NON_TEXT_KEYWORDS:
                               char_tag = match_dialogue.group(2)
                               current_text = match_dialogue.group(5).replace('\\"', '"')
                     elif parser.RE_NARRATION.match(line_content): 
                         match_narration = parser.RE_NARRATION.match(line_content)
                         first_word = line_content.lstrip().split(None, 1)[0] if line_content.lstrip() else ""
                         if match_narration and first_word not in parser.NON_TEXT_KEYWORDS:
                             current_text = match_narration.group(2).replace('\\"', '"')
                     else:

                          match_screen_generic = parser.RE_SCREEN_GENERIC_TEXT.match(line_content)
                          if match_screen_generic:
                              _, _, text_quotes, text_underscore, _ = match_screen_generic.groups()
                              if text_quotes is not None:
                                   current_text = text_quotes.replace('\\"', '"')
                              elif text_underscore is not None:
                                   current_text = text_underscore.replace('\\"', '"')
                          else:

                               match_screen_prop = parser.RE_SCREEN_PROP.match(line_content)
                               if match_screen_prop:
                                   _, _, text_quotes, text_underscore, _ = match_screen_prop.groups()
                                   if text_quotes is not None:
                                       current_text = text_quotes.replace('\\"', '"')
                                   elif text_underscore is not None:
                                       current_text = text_underscore.replace('\\"', '"')

        info["character_tag"] = char_tag

        if current_text is not None:
            info["current_text"] = current_text

        context_lines_info.append(info)

    return context_lines_info

def get_context_for_item(item_index, items_list, lines_list, mode):

    if mode == "translate":
        return get_context_for_translate_item(item_index, items_list, lines_list)
    elif mode == "direct":
        return get_context_for_direct_item(item_index, items_list, lines_list)
    else:
        print(f"Warning: Unknown mode '{mode}' in get_context_for_item. Returning empty context.")
        return []

print("renforge_core.py loaded") 