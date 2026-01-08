import re
import os

from renforge_logger import get_logger
logger = get_logger("core")

import renforge_config as config
from locales import tr

import parser.core as parser
from parser.patterns import RenpyPatterns
from parser.direct_parser import NON_TEXT_KEYWORDS
from models.parsed_file import ParsedItem
from renforge_enums import ItemType, ContextType
from renforge_exceptions import FileOperationError, SaveError, ModeDetectionError
from dataclasses import replace

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

    logger.debug(f"[detect_file_mode] Detecting mode for: {file_path}")

    loaded_file_lines, _ = load_and_parse_base(file_path)
    if loaded_file_lines is None:
        logger.warning(f"[detect_file_mode] Could not load file. Defaulting to 'direct'.")
        return "direct" 

    has_translate_blocks = False
    has_screen_definitions = False

    screen_def_regex = RenpyPatterns.SCREEN_START
    translate_block_regex = RenpyPatterns.TRANSLATE_START

    logger.debug(f"[detect_file_mode] Scanning for translate blocks and screen definitions...")
    for line in loaded_file_lines:
        stripped_line = line.lstrip()

        if stripped_line.startswith('#'):
            continue

        if translate_block_regex.match(line):
            has_translate_blocks = True

        if screen_def_regex.match(line):
            has_screen_definitions = True

    logger.debug(f"[detect_file_mode] Analysis results: translate={has_translate_blocks}, screen={has_screen_definitions}")

    if has_screen_definitions:
        logger.debug(f"[detect_file_mode] Decision: 'direct' (Screen definitions found)")
        return "direct"

    if has_translate_blocks:
        logger.debug(f"[detect_file_mode] Decision: 'translate' (Translate blocks found)")
        return "translate"

    logger.debug(f"[detect_file_mode] Decision: 'direct' (Default)")
    return "direct"

def load_and_parse_base(input_path):

    try:

        input_path_obj = config.Path(input_path)
        if not input_path_obj.is_file():
             raise FileNotFoundError(tr("core_file_not_found", path=input_path))

        raw_lines = input_path_obj.read_text(encoding='utf-8-sig').splitlines()
    except FileNotFoundError as e:
        logger.error(tr("core_error", error=e))
        return None, None 
    except Exception as e:
        logger.error(tr("core_read_error", path=input_path, error=e))
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

    logger.debug(tr("core_file_loaded", path=input_path, lines=len(loaded_file_lines), breakpoints=len(loaded_breakpoints)))
    return loaded_file_lines, loaded_breakpoints

def load_and_parse_translate_file(input_path):

    loaded_file_lines, loaded_breakpoints = load_and_parse_base(input_path)
    if loaded_file_lines is None:
        return [], [], set(), None 

    logger.debug(tr("core_parser_start"))

    all_parsed_items, _ = parser.parse_file_contextually(loaded_file_lines)

    logger.debug(tr("core_parser_process"))
    parsed_translatable_items = []
    detected_language = None
    last_old_item = None 
    last_original_comment_item = None 

    for item in all_parsed_items:
        item_index = item.line_index
        item_type = item.type
        item_context = item.context
        item_lang = item.block_language

        if detected_language is None and item_lang:
            detected_language = item_lang
            logger.info(tr("core_lang_found", lang=detected_language)) 
        elif detected_language and item_lang and detected_language != item_lang:
            logger.warning(tr("core_lang_warning", lang=item_lang, detected=detected_language, line=item_index+1))

        if item_context == ContextType.TRANSLATE_STRINGS:
            if item_type == ItemType.TRANSLATE_OLD:
                last_old_item = item 
                last_original_comment_item = None 
            elif item_type == ItemType.TRANSLATE_NEW and last_old_item:

                new_text = item.current_text
                final_item = replace(item,
                    original_line_index=last_old_item.line_index,
                    original_text=last_old_item.original_text,
                    parsed_data=item.parsed_data,
                    block_language=last_old_item.block_language,
                    type=ItemType("string"),
                    is_modified_session=False,
                    # current_text is already in item
                    initial_text=new_text
                )
                
                if 'reconstruction_rule' not in final_item.parsed_data:
                    final_item.parsed_data['reconstruction_rule'] = 'translate_new'

                parsed_translatable_items.append(final_item)
                last_old_item = None 
            else:

                last_old_item = None

        elif item_context == ContextType.TRANSLATE:
            # NEW FORMAT: Parser already paired comment+dialogue into DIALOGUE items
            # with original_text and current_text set correctly
            if item_type == ItemType.DIALOGUE:
                rec_rule = item.parsed_data.get('reconstruction_rule', '')
                # Items from new parser format (translate_dialogue or translate_new)
                if rec_rule in ('translate_dialogue', 'translate_new'):
                    # Already a complete paired item from new parser
                    final_item = replace(item,
                        type=ItemType("dialogue"),
                        is_modified_session=False,
                        initial_text=item.current_text,
                        block_language=item_lang or detected_language
                    )
                    parsed_translatable_items.append(final_item)
                    continue
            
            # OLD FORMAT: Handle potential original (comment) waiting for translation line
            if item_type == ItemType.TRANSLATE_POTENTIAL_ORIGINAL:

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

                        final_item = ParsedItem(
                            line_index=item_index,
                            original_line_index=last_original_comment_item['line_index'],
                            original_text=original_text_content,
                            current_text=translated_text,
                            initial_text=translated_text,
                            type=ItemType(original_type),  # Ensure enum conversion
                            parsed_data=item['parsed_data'],
                            has_breakpoint=item['has_breakpoint'],
                            
                            is_modified_session=False,
                            block_language=item_lang,
                            character_trans=translation_char_tag,
                            character_tag=original_char_tag
                        )

                        rec_rule = 'standard' if translation_char_tag else 'narration'
                        final_item.parsed_data['reconstruction_rule'] = rec_rule

                        parsed_translatable_items.append(final_item)

                        last_original_comment_item = None 
                    else:

                        logger.warning(tr("core_type_mismatch_warning", line=item_index+1, orig_type=original_type, orig_tag=original_char_tag, trans_type=translation_base_type, trans_tag=translation_char_tag))
                        last_original_comment_item = None 
                else:

                    logger.warning(tr("core_type_unknown_warning", line=item_index+1, comment=original_parsed_data.get('original_full_comment_content', ''), text=translated_text[:30]))
                    last_original_comment_item = None 
            else:
                 # Logic for clearing if mismatch sequence
                if item_type != ItemType.TRANSLATE_POTENTIAL_ORIGINAL: 
                     last_original_comment_item = None

        else:
            if item_context != ContextType.TRANSLATE and item_context != ContextType.TRANSLATE_STRINGS:
                last_old_item = None
                last_original_comment_item = None

    logger.debug(tr("core_process_complete", count=len(parsed_translatable_items)))
    if not parsed_translatable_items and detected_language:
        logger.warning(tr("core_no_pairs_warning"))

    return parsed_translatable_items, loaded_file_lines, loaded_breakpoints, detected_language

def save_translate_file(output_path, current_file_lines, current_breakpoints):

    lines_to_save = prepare_lines_for_saving(current_file_lines, current_breakpoints)
    try:
        output_path_obj = config.Path(output_path)
        output_path_obj.write_text('\n'.join(lines_to_save) + '\n', encoding='utf-8')
        logger.info(tr("core_save_success", path=output_path))
        return True 
    except (IOError, OSError) as e:
        raise SaveError(tr("core_save_error", path=output_path, error=str(e)), file_path=output_path) from e
    except Exception as e:
        raise SaveError(f"Unexpected error saving file: {e}", file_path=output_path) from e 

def get_context_for_translate_item(item_index, items_list, lines_list):

    if not items_list or not (0 <= item_index < len(items_list)):
        return [] 

    target_item: ParsedItem = items_list[item_index]

    target_line_index = target_item.line_index

    original_line_index = target_item.original_line_index if target_item.original_line_index is not None else -1

    start_line_idx = max(0, target_line_index - config.CONTEXT_LINES)
    end_line_idx = min(len(lines_list), target_line_index + config.CONTEXT_LINES + 1)

    context_lines_info = []

    item_lookup_trans = {item.line_index: item for item in items_list}
    item_lookup_orig = {item.original_line_index: item for item in items_list if item.original_line_index is not None}

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
             info["original"] = item_data.original_text
             info["translated"] = item_data.current_text
             info["is_translation_line"] = True

             char_tag = item_data.character_trans

        elif i in item_lookup_orig:
             item_data = item_lookup_orig[i]
             info["original"] = item_data.original_text

             info["is_original_comment"] = True

             char_tag = item_data.character_tag

        else:

             if line_content.lstrip().startswith('#'):

                 pass
             else:

                 match_dialogue = RenpyPatterns.DIALOGUE.match(line_content)
                 if match_dialogue:
                     char_tag = match_dialogue.group(2) 

        info["character_tag"] = char_tag 
        context_lines_info.append(info)

    return context_lines_info

def load_and_parse_direct_file(input_path):

    loaded_file_lines, loaded_breakpoints = load_and_parse_base(input_path)
    if loaded_file_lines is None:
        return [], [], set()

    logger.debug(f"Calling parser.parse_file_contextually for Direct Mode on {input_path}") 
    all_parsed_items = parser.parse_file_contextually(loaded_file_lines)
    logger.debug(f"Parser finished for Direct Mode. Found {len(all_parsed_items) if all_parsed_items is not None else 'None'} raw items.") 

    logger.debug(tr("core_filter_direct"))
    parsed_direct_items = []

    editable_types_direct = {
        ItemType.DIALOGUE,
        ItemType.NARRATION,
        ItemType.CHOICE,
        ItemType.SCREEN_BUTTON,
        ItemType.SCREEN_LABEL,
        ItemType.SCREEN_TEXT_STATEMENT,
        ItemType.SCREEN_TEXT_PROPERTY,
        ItemType.VARIABLE 
    }

    for item in all_parsed_items:

        if item.context in [ContextType.TRANSLATE, ContextType.TRANSLATE_STRINGS]:
             if item.type == ItemType.TRANSLATE_POTENTIAL_ORIGINAL: continue
             continue

        if item.type in editable_types_direct:
            text = item.original_text
            
            # direct_item logic removed, we use the parsed item directly.
            parsed_direct_items.append(item)
            continue

    logger.debug(tr("core_direct_found", count=len(parsed_direct_items)))
    if not parsed_direct_items:
        logger.warning(tr("core_direct_none"))
    return parsed_direct_items, loaded_file_lines, loaded_breakpoints

def save_direct_file(output_path, current_items_list, current_file_lines, current_breakpoints):

    logger.debug(tr("core_rebuild_saving", path=output_path))

    items_by_index = {item.line_index: item for item in current_items_list}
    new_file_lines_temp = [] 
    saved_count = 0 

    for i, original_line_in_memory in enumerate(current_file_lines):

        if i in items_by_index:
            item = items_by_index[i]

            # Reconstruct the line using the parser's helper, but adapted for ParsedItem if needed
            # The parser expects a dict-like structure or specific keys. 
            # It seems format_line_from_components takes (item_dict, new_text).
            # We might need to adjust parser or convert item back to dict for the parser function?
            # Or better, just pass the parsed_data which format_line_from_components often needs.
            # Let's check parser.format_line_from_components usage.
            
            # Since parser expects specific keys usually found in the raw parser output,
            # and ParsedItem stores that in 'parsed_data' + type/text fields.
            
            # Temporary bridge: The parser function likely expects the structure it produced.
            # Our ParsedItem stores that in 'parsed_data' but we modified 'text' in the item.
            
            # Actually, `parser.format_line_from_components(item_data, new_text)`
            # In existing code `item` was the direct_item dict which mapped almost 1:1 to parser output.
            
            # We need to construct a compatible dict or modify parser.
            # Let's pass the item.parsed_data augmented with type.
            
            # Wait, `renforge_parser.py` implementation of `format_line_from_components`
            # checks `item_data['type']`. `parsed_data` usually doesn't have 'type'.
            
            # Let's create a proxy dict for the parser function.
            parser_proxy_item = item.parsed_data.copy()
            parser_proxy_item['type'] = item.type
            if item.character_tag: parser_proxy_item['character_tag'] = item.character_tag
            
            new_line = parser.format_line_from_components(parser_proxy_item, item.current_text)
            if new_line is not None:
                new_file_lines_temp.append(new_line)

                if item.current_text != item.original_text:
                    saved_count += 1
            else:

                logger.warning(tr("core_reformat_warning", line=i+1, content=original_line_in_memory))
                new_file_lines_temp.append(original_line_in_memory)
        else:

            new_file_lines_temp.append(original_line_in_memory)

    lines_to_save = prepare_lines_for_saving(new_file_lines_temp, current_breakpoints)

    try:
        output_path_obj = config.Path(output_path)
        output_path_obj.write_text('\n'.join(lines_to_save) + '\n', encoding='utf-8')
        logger.info(tr("core_save_success_count", count=saved_count))
        # return True - No need to return True if we trust exceptions, but for now let's keep consistent if caller expects it, 
        # or better: verify if caller checks return value. 
        # Actually standard practice with exceptions is void return on success usually.
        # But let's return True to be safe with existing checks while we transition.
        return True 
    except (IOError, OSError) as e:
        # Wrap IO errors in our custom SaveError
        raise SaveError(tr("core_save_error", path=output_path, error=str(e)), file_path=output_path) from e
    except Exception as e:
         # Catch-all for other unexpected errors during save preparation
         raise SaveError(f"Unexpected error saving file: {e}", file_path=output_path) from e 

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

                 match_var_dollar = RenpyPatterns.VAR_ASSIGN_DOLLAR.match(line_content)
                 if match_var_dollar:
                     var_name = match_var_dollar.group(2) 
                     current_text = match_var_dollar.group(3).replace('\\"', '"')
                 else:

                     match_var_py = RenpyPatterns.VAR_ASSIGN_PYTHON.match(line_content)
                     if match_var_py:
                          var_name = match_var_py.group(2) 
                          current_text = match_var_py.group(3).replace('\\"', '"')

                     elif RenpyPatterns.DIALOGUE.match(line_content): 
                          match_dialogue = RenpyPatterns.DIALOGUE.match(line_content)
                          if match_dialogue and match_dialogue.group(2) not in NON_TEXT_KEYWORDS:
                               char_tag = match_dialogue.group(2)
                               current_text = match_dialogue.group(5).replace('\\"', '"')
                     elif RenpyPatterns.NARRATION.match(line_content): 
                         match_narration = RenpyPatterns.NARRATION.match(line_content)
                         first_word = line_content.lstrip().split(None, 1)[0] if line_content.lstrip() else ""
                         if match_narration and first_word not in NON_TEXT_KEYWORDS:
                             current_text = match_narration.group(2).replace('\\"', '"')
                     else:

                          match_screen_generic = RenpyPatterns.SCREEN_GENERIC_TEXT.match(line_content)
                          if match_screen_generic:
                              _, _, text_quotes, text_underscore, _ = match_screen_generic.groups()
                              if text_quotes is not None:
                                   current_text = text_quotes.replace('\\"', '"')
                              elif text_underscore is not None:
                                   current_text = text_underscore.replace('\\"', '"')
                          else:

                               match_screen_prop = RenpyPatterns.SCREEN_PROP.match(line_content)
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
        logger.warning(f"Unknown mode '{mode}' in get_context_for_item. Returning empty context.")
        return []

logger.debug("renforge_core.py loaded") 