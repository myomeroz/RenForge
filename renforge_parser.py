

import re
import renforge_config as config


CONTEXT_GLOBAL = 'global'
CONTEXT_SCREEN = 'screen'
CONTEXT_LABEL = 'label' 
CONTEXT_PYTHON = 'python'
CONTEXT_TRANSLATE = 'translate' 
CONTEXT_TRANSLATE_STRINGS = 'translate_strings' 
CONTEXT_MENU = 'menu' 
CONTEXT_VARIABLE = 'variable' 


CONTEXT_IMAGE_DEF = 'image_def'
CONTEXT_TRANSFORM_DEF = 'transform_def'
CONTEXT_STYLE_DEF = 'style_def'
CONTEXT_DEFINE_DEF = 'define_def' 



RE_SCREEN_START = re.compile(r'^\s*screen\s+(\w+)\s*(\(.*\))?\s*:', re.IGNORECASE)
RE_LABEL_START = re.compile(r'^\s*label\s+(\w+)\s*:', re.IGNORECASE)
RE_PYTHON_START = re.compile(r'^\s*(python|init\s+python)\s*:', re.IGNORECASE)
RE_TRANSLATE_START = re.compile(r'^\s*translate\s+(\w+)\s+(\w+)\s*:', re.IGNORECASE)
RE_MENU_START = re.compile(r'^\s*menu\s*:', re.IGNORECASE)
RE_IMAGE_START = re.compile(r'^\s*image\s+([\w."\'=+\-\*\/\s]+)\s*:', re.IGNORECASE) 
RE_TRANSFORM_START = re.compile(r'^\s*transform\s+([\w.]+)\s*(\(.*\))?\s*:', re.IGNORECASE)
RE_STYLE_START = re.compile(r'^\s*style\s+(\w+)\s*(?:is\s+(\w+))?\s*:', re.IGNORECASE)
RE_DEFINE_START = re.compile(r'^\s*(define|default)\s+([a-zA-Z_]\w*)\s*=.*', re.IGNORECASE) 



RE_VAR_ASSIGN_DOLLAR = re.compile(r'^(\s*)\$\s+([a-zA-Z_]\w*)\s*=\s*"((?:\\.|[^"\\])*)"(.*)$')

RE_VAR_ASSIGN_PYTHON = re.compile(r'^(\s*)([a-zA-Z_]\w*)\s*=\s*"((?:\\.|[^"\\])*)"(.*)$')






RE_DIALOGUE = re.compile(r'^(\s*)([a-zA-Z0-9_]+)((?:\s+[a-zA-Z0-9_]+)*)?(?:\s+([a-z]+))?\s+"((?:\\.|[^"\\])*)"(.*)$')
RE_DIALOGUE_COMMENT_CONTENT = re.compile(r'^([a-zA-Z0-9_]+)((?:\s+[a-zA-Z0-9_]+)*)?(?:\s+([a-z]+))?\s+"((?:\\.|[^"\\])*)"(.*)$')


RE_NARRATION = re.compile(r'^(\s*)"((?:\\.|[^"\\])*)"(.*)$')
RE_NARRATION_COMMENT_CONTENT = re.compile(r'^"((?:\\.|[^"\\])*)"(.*)$') 
RE_MENU_CHOICE = re.compile(r'^(\s*)"((?:\\.|[^"\\])*)"(\s*:.+?)$') 



RE_SCREEN_GENERIC_TEXT = re.compile(
    r'^(\s*)'                                  
    r'(?:(text|button|textbutton|label)\s+)?'    
    r'(?:'                                     
        r'"((?:\\.|[^"\\])*)"'                 
      r'|'
        r'_\("((?:\\.|[^"\\])*)"\)'            
    r')'
    r'(.*)$'                                   
) 



NON_TEXT_KEYWORDS = {
    'play', 'queue', 'stop', 'show', 'scene', 'hide', 'with', 'window', 'image',
    'movie', 'voice', 'sound', 'music', 'style', 'transform', 'animation',
    'call', 'jump', 'return', '$', 'init', 'python', 'label', 'screen', 'menu',
    'if', 'while', 'for', 'pass'
    
}




RENPY_KEYWORDS_AND_PROPERTIES = {
    
    'play', 'queue', 'stop', 'show', 'scene', 'hide', 'with', 'window', 'image',
    'movie', 'voice', 'sound', 'music', 'style', 'transform', 'animation',
    'call', 'jump', 'return', '$', 'init', 'python', 'label', 'screen', 'menu',
    'if', 'while', 'for', 'pass', 'use', 'tag', 'layer', 'zorder', 'at', 'as',
    'behind', 'onlayer', 'predict', 'define', 'default', 'fixed', 'has', 'hbox', 'vbox',
    'grid', 'vpgrid', 'side', 'key', 'timer', 'on', 'action', 'sensitiveif',
    'imagemap', 'hotspot', 'hotbar', 'drag', 'draggroup', 'bar', 'vbar', 'slider', 'vslider',
    'scrollbar', 'vscrollbar', 'viewport', 'input', 'imagemap', 'textbutton', 'button',
    'imagebutton', 'frame', 'null', 'add', 'transclude', 'imagemap',
    
    'font', 'background', 'thumb', 'selected_idle_background', 'selected_hover_background',
    'idle_background', 'hover_background', 'insensitive_background', 'ground',
    'xpos', 'ypos', 'xanchor', 'yanchor', 'xalign', 'yalign', 'id', 'style_prefix',
    'tooltip', 'alt', 'title', 'text', 'value', 'action', 'hovered', 'unhovered',
    'hover_sound', 'activate_sound', 'selected_activate_sound', 'selected_hover_sound',
    
    'unscrollable', 'scrollbars', 'modal',
    
    'cols', 'rows', 'spacing', 'padding', 'margin', 'xoffset', 'yoffset',
    'xsize', 'ysize', 'xmaximum', 'ymaximum', 'xminimum', 'yminimum',
    'size', 'color', 'hover_color', 'idle_color', 'selected_color', 'selected_hover_color',
    'insensitive_color', 'outlines', 'hover_outlines', 'selected_outlines', 'insensitive_outlines',
    'properties', 'layout', 'text_align', 'size_group', 'base_bar', 'top_bar', 'bottom_bar',
    'caret', 'left_bar', 'right_bar', 'left_gutter', 'right_gutter', 'top_gutter', 'bottom_gutter',
    'mipmap', 'subpixel', 'alpha', 'rotate', 'zoom', 'xzoom', 'yzoom', 'matrixcolor',
    'default', 
    'transform', 
}



TEXT_PATTERN = r'(?:\_\(\s*"((?:\\.|[^"\\])*)"\s*\)|"((?:\\.|[^"\\])*)")'



RE_SCREEN_TEXT_STMT = re.compile(r'^(\s*)(text)\s+' + TEXT_PATTERN + r'(.*)$', re.IGNORECASE)
RE_SCREEN_BUTTON = re.compile(r'^(\s*)(button|textbutton)\s+' + TEXT_PATTERN + r'(.*)$', re.IGNORECASE)
RE_SCREEN_LABEL = re.compile(r'^(\s*)(label)\s+' + TEXT_PATTERN + r'(.*)$', re.IGNORECASE)


RE_SCREEN_PROP = re.compile(
    r'^(\s*)'                                  
    r'(\w+\s*.*?)??\s*'                        
    r'(text|tooltip|title|alt|placeholder)\s+' 
    + TEXT_PATTERN +                           
    r'(.*)$'                                   
, re.IGNORECASE)


RE_TRANSLATE_OLD = re.compile(r'^(\s*)old\s+"((?:\\.|[^"\\])*)"(.*)$')
RE_TRANSLATE_NEW = re.compile(r'^(\s*)new\s+"((?:\\.|[^"\\])*)"(.*)$')


RE_TRANSLATE_COMMENT = re.compile(r'^(\s*)#\s?(.*)')


def get_indentation(line):
    
    return len(line) - len(line.lstrip(' '))


def parse_file_contextually(lines_list):
    print(f"DEBUG Parser: Entered parse_file_contextually with {len(lines_list) if lines_list is not None else 'None'} lines.") 
    parsed_items = []
    
    
    context_stack = [(-1, CONTEXT_GLOBAL, None)]
    current_indent = 0
    current_context = CONTEXT_GLOBAL
    current_context_data = None 

    for i, line in enumerate(lines_list):
        
        if not line.strip():
            continue

        
        line_indent = get_indentation(line)
        lstripped_line = line.lstrip()

        
        breakpoint_marker = config.BREAKPOINT_MARKER
        has_breakpoint = line.rstrip().endswith(breakpoint_marker)
        if has_breakpoint:
            line_to_parse = re.sub(r'\s+' + re.escape(breakpoint_marker) + r'\s*$', '', line)
            lstripped_line = line_to_parse.lstrip()
        else:
            line_to_parse = line

        
        
        
        
        is_comment = lstripped_line.startswith('#')

        # Fix: Comments should not trigger context popping (dedentation).
        # We process the pop loop only if it's NOT a comment.
        if not is_comment:
            while context_stack and line_indent <= context_stack[-1][0]:
                 context_stack.pop()
             

        
        current_indent, current_context, current_context_data = context_stack[-1]
        
        if is_comment:
            if current_context == CONTEXT_TRANSLATE:
                
                 match_comment = RE_TRANSLATE_COMMENT.match(line_to_parse)
                 if match_comment:
                    indent_com, content = match_comment.groups()
                    original_content_stripped = content.strip()
                    original_char_tag = None; original_type = None; original_parsed_text = None
                    original_attributes = None; original_tag_attribute = None
                    match_dialogue = RE_DIALOGUE_COMMENT_CONTENT.match(original_content_stripped)
                    if match_dialogue:
                        original_char_tag = match_dialogue.group(1); original_attributes = match_dialogue.group(2)
                        original_tag_attribute = match_dialogue.group(3); original_parsed_text = match_dialogue.group(4).replace('\\"', '"')
                        original_type = "dialogue"
                    else:
                         match_narration = RE_NARRATION_COMMENT_CONTENT.match(original_content_stripped)
                         if match_narration:
                             original_parsed_text = match_narration.group(1).replace('\\"', '"')
                             original_type = "narration"
                    parsed_items.append({
                         "line_index": i, "type": "translate_potential_original",
                         "text": original_parsed_text if original_type else content,
                         "context": current_context, "context_data": current_context_data,
                         "parsed_data": {"indent": indent_com, "original_type": original_type, "original_char_tag": original_char_tag,
                                         "original_attributes": original_attributes, "original_tag_attribute": original_tag_attribute,
                                         "original_full_comment_content": content},
                         "has_breakpoint": has_breakpoint})
            continue 


        
        new_context_found = False
        
        if line_indent > current_indent:
            
            match_python = RE_PYTHON_START.match(line_to_parse)
            if match_python:
                new_indent = line_indent; new_context = CONTEXT_PYTHON; new_context_data = None
                context_stack.append((new_indent, new_context, new_context_data))
                new_context_found = True
                print(f"DEBUG Parser L{i+1}: Entered context PYTHON at indent {new_indent}")

            
            if not new_context_found:
                match_screen = RE_SCREEN_START.match(line_to_parse)
                if match_screen:
                    new_indent = line_indent; new_context = CONTEXT_SCREEN; new_context_data = {"name": match_screen.group(1)}
                    context_stack.append((new_indent, new_context, new_context_data))
                    new_context_found = True
                    print(f"DEBUG Parser L{i+1}: Entered context SCREEN '{new_context_data['name']}' at indent {new_indent}")

            
            if not new_context_found:
                match_translate = RE_TRANSLATE_START.match(line_to_parse)
                if match_translate:
                    new_indent = line_indent
                    lang, identifier = match_translate.groups()
                    if identifier.lower() == 'strings': new_context = CONTEXT_TRANSLATE_STRINGS
                    else: new_context = CONTEXT_TRANSLATE
                    new_context_data = {"language": lang, "identifier": identifier}
                    context_stack.append((new_indent, new_context, new_context_data))
                    new_context_found = True
                    print(f"DEBUG Parser L{i+1}: Entered context {new_context} '{lang} {identifier}' at indent {new_indent}")

            
            if not new_context_found and current_context != CONTEXT_SCREEN:
                match_label = RE_LABEL_START.match(line_to_parse)
                if match_label:
                    new_indent = line_indent; new_context = CONTEXT_LABEL; new_context_data = {"name": match_label.group(1)}
                    context_stack.append((new_indent, new_context, new_context_data))
                    new_context_found = True
                    print(f"DEBUG Parser L{i+1}: Entered context LABEL '{new_context_data['name']}' at indent {new_indent}")

            
            if not new_context_found:
                match_menu = RE_MENU_START.match(line_to_parse)
                if match_menu:
                    new_indent = line_indent; new_context = CONTEXT_MENU; new_context_data = None
                    context_stack.append((new_indent, new_context, new_context_data))
                    new_context_found = True
                    print(f"DEBUG Parser L{i+1}: Entered context MENU at indent {new_indent}")

            
            if not new_context_found:
                 match_image = RE_IMAGE_START.match(line_to_parse)
                 if match_image:
                     new_indent = line_indent; new_context = CONTEXT_IMAGE_DEF; new_context_data = {"name_expr": match_image.group(1).strip()}
                     context_stack.append((new_indent, new_context, new_context_data))
                     new_context_found = True
                     print(f"DEBUG Parser L{i+1}: Entered context IMAGE_DEF '{new_context_data['name_expr']}' at indent {new_indent}")

            
            if not new_context_found:
                 match_transform = RE_TRANSFORM_START.match(line_to_parse)
                 if match_transform:
                     new_indent = line_indent; new_context = CONTEXT_TRANSFORM_DEF; new_context_data = {"name": match_transform.group(1)}
                     context_stack.append((new_indent, new_context, new_context_data))
                     new_context_found = True
                     print(f"DEBUG Parser L{i+1}: Entered context TRANSFORM_DEF '{new_context_data['name']}' at indent {new_indent}")

            
            if not new_context_found:
                 match_style = RE_STYLE_START.match(line_to_parse)
                 if match_style:
                     new_indent = line_indent; new_context = CONTEXT_STYLE_DEF; new_context_data = {"name": match_style.group(1)}
                     context_stack.append((new_indent, new_context, new_context_data))
                     new_context_found = True
                     print(f"DEBUG Parser L{i+1}: Entered context STYLE_DEF '{new_context_data['name']}' at indent {new_indent}")

            
            
            if not new_context_found:
                match_define = RE_DEFINE_START.match(line_to_parse)
                if match_define:
                    
                    if '=' in lstripped_line and '"' in lstripped_line.split('=', 1)[1]:
                         
                         
                         new_indent = line_indent; new_context = CONTEXT_DEFINE_DEF; new_context_data = {"name": match_define.group(2)}
                         context_stack.append((new_indent, new_context, new_context_data))
                         new_context_found = True
                         print(f"DEBUG Parser L{i+1}: Entered context DEFINE_DEF '{new_context_data['name']}' at indent {new_indent}")
                    

        
        if new_context_found:
            current_indent, current_context, current_context_data = context_stack[-1]
            continue

        

        
        if current_context in [CONTEXT_PYTHON, CONTEXT_IMAGE_DEF, CONTEXT_TRANSFORM_DEF, CONTEXT_STYLE_DEF]:
             continue

        
        parsed_data = None; item_type = None; text = None; char_tag = None
        attributes = None; tag_attribute = None; uses_underscore = False
        variable_name = None; has_dollar_prefix = False

        
        first_word = lstripped_line.split(None, 1)[0] if lstripped_line else ""

        
        if current_context == CONTEXT_DEFINE_DEF:
            match_var_py = RE_VAR_ASSIGN_PYTHON.match(line_to_parse) 
            if match_var_py:
                indent, var_name_match, text_raw, suffix = match_var_py.groups()
                
                if context_data and var_name_match == context_data.get('name'):
                    item_type = CONTEXT_VARIABLE; variable_name = var_name_match
                    text = text_raw.replace('\\"', '"'); has_dollar_prefix = False
                    
                    keyword = "define" if line_to_parse.strip().startswith("define") else "default"
                    parsed_data = {"indent": indent, "variable_name": variable_name, "suffix": suffix,
                                   "has_dollar": has_dollar_prefix, "reconstruction_rule": "define_variable", "keyword": keyword} 
                    

        
        if not parsed_data and current_context != CONTEXT_DEFINE_DEF: 
            match_var_dollar = RE_VAR_ASSIGN_DOLLAR.match(line_to_parse)
            if match_var_dollar:
                indent_var, var_name_match, text_raw, suffix_var = match_var_dollar.groups()
                item_type = CONTEXT_VARIABLE; variable_name = var_name_match
                text = text_raw.replace('\\"', '"'); has_dollar_prefix = True
                parsed_data = {"indent": indent_var, "variable_name": variable_name, "suffix": suffix_var,
                               "has_dollar": has_dollar_prefix, "reconstruction_rule": "variable"}

        
        if not parsed_data:
            if current_context == CONTEXT_SCREEN:
                 
                 match_prop = RE_SCREEN_PROP.match(line_to_parse)
                 if match_prop:
                    indent, prefix_content, keyword, text_underscore, text_quotes, suffix = match_prop.groups()
                    if text_underscore is not None: text, uses_underscore = text_underscore.replace('\\"', '"'), True
                    elif text_quotes is not None: text, uses_underscore = text_quotes.replace('\\"', '"'), False
                    if text is not None: item_type = "screen_text_property"; parsed_data = {"indent": indent, "prefix_content": prefix_content or '', "keyword": keyword, "suffix": suffix, "uses_underscore": uses_underscore, "reconstruction_rule": "screen_property"}

                 if not parsed_data:
                     match_btn = RE_SCREEN_BUTTON.match(line_to_parse)
                     if match_btn:
                        indent, keyword, text_underscore, text_quotes, suffix = match_btn.groups()
                        if text_underscore is not None: text, uses_underscore = text_underscore.replace('\\"', '"'), True
                        elif text_quotes is not None: text, uses_underscore = text_quotes.replace('\\"', '"'), False
                        if text is not None: item_type = "screen_button"; parsed_data = {"indent": indent, "keyword": keyword, "suffix": suffix, "uses_underscore": uses_underscore, "reconstruction_rule": "screen_button"}

                 if not parsed_data:
                     match_label = RE_SCREEN_LABEL.match(line_to_parse)
                     if match_label:
                        indent, keyword, text_underscore, text_quotes, suffix = match_label.groups()
                        if text_underscore is not None: text, uses_underscore = text_underscore.replace('\\"', '"'), True
                        elif text_quotes is not None: text, uses_underscore = text_quotes.replace('\\"', '"'), False
                        if text is not None: item_type = "screen_label"; parsed_data = {"indent": indent, "keyword": keyword, "suffix": suffix, "uses_underscore": uses_underscore, "reconstruction_rule": "screen_label"}

                 if not parsed_data:
                     match_text = RE_SCREEN_TEXT_STMT.match(line_to_parse)
                     if match_text:
                        indent, keyword, text_underscore, text_quotes, suffix = match_text.groups()
                        if text_underscore is not None: text, uses_underscore = text_underscore.replace('\\"', '"'), True
                        elif text_quotes is not None: text, uses_underscore = text_quotes.replace('\\"', '"'), False
                        if text is not None: item_type = "screen_text_statement"; parsed_data = {"indent": indent, "keyword": keyword, "suffix": suffix, "uses_underscore": uses_underscore, "reconstruction_rule": "screen_text_statement"}

            elif current_context == CONTEXT_TRANSLATE_STRINGS:
                 
                 match_old = RE_TRANSLATE_OLD.match(line_to_parse)
                 if match_old: indent, text_raw, suffix = match_old.groups(); item_type = "translate_old"; text = text_raw.replace('\\"', '"'); parsed_data = {"indent": indent, "suffix": suffix, "reconstruction_rule": "translate_old"}
                 if not parsed_data:
                     match_new = RE_TRANSLATE_NEW.match(line_to_parse)
                     if match_new: indent, text_raw, suffix = match_new.groups(); item_type = "translate_new"; text = text_raw.replace('\\"', '"'); parsed_data = {"indent": indent, "suffix": suffix, "reconstruction_rule": "translate_new"}

            elif current_context == CONTEXT_MENU:
                 
                  match_choice = RE_MENU_CHOICE.match(line_to_parse)
                  if match_choice: indent, text_raw, suffix = match_choice.groups(); item_type = "choice"; text = text_raw.replace('\\"', '"'); parsed_data = {"indent": indent, "suffix": suffix, "reconstruction_rule": "choice"}


            
            elif current_context in [CONTEXT_GLOBAL, CONTEXT_LABEL, CONTEXT_TRANSLATE]:
                 match_dialogue = RE_DIALOGUE.match(line_to_parse)
                 if match_dialogue:
                     indent_dlg, char_tag_match, attrs_match, tag_attr_match, text_raw, suffix = match_dialogue.groups()
                     if char_tag_match not in RENPY_KEYWORDS_AND_PROPERTIES:
                         item_type = "translate_translation" if current_context == CONTEXT_TRANSLATE else "dialogue"
                         char_tag = char_tag_match; attributes = attrs_match; tag_attribute = tag_attr_match
                         text = text_raw.replace('\\"', '"')
                         prefix_parts = [indent_dlg, char_tag]
                         if attributes: prefix_parts.append(attributes)
                         if tag_attribute: prefix_parts.append(f" {tag_attribute}")
                         prefix = "".join(prefix_parts) + " "
                         parsed_data = {"prefix": prefix, "suffix": suffix, "reconstruction_rule": "standard", "attributes": attributes, "tag_attribute": tag_attribute, "indent": indent_dlg}

                 if not parsed_data:
                     match_narration = RE_NARRATION.match(line_to_parse)
                     if match_narration:
                         is_paren_block_content = re.match(r'^"((?:\\.|[^"\\])*)"\s*,.*', lstripped_line)
                         is_style_property = False
                         if current_context == CONTEXT_GLOBAL: 
                             potential_prop = lstripped_line.split('"', 1)[0].strip()
                             if potential_prop in RENPY_KEYWORDS_AND_PROPERTIES:
                                  is_style_property = True

                         if first_word not in RENPY_KEYWORDS_AND_PROPERTIES and not is_paren_block_content and not is_style_property:
                             indent_nar, text_raw, suffix = match_narration.groups()
                             item_type = "translate_translation" if current_context == CONTEXT_TRANSLATE else "narration"
                             char_tag = None; attributes = None; tag_attribute = None
                             text = text_raw.replace('\\"', '"')
                             parsed_data = {"indent": indent_nar, "suffix": suffix, "reconstruction_rule": "narration", "attributes": None, "tag_attribute": None}
                         


        
        
        if parsed_data and item_type and text is not None:
             if len(text.strip()) > 0 or config.ALLOW_EMPTY_STRINGS or item_type == CONTEXT_VARIABLE:
                 if 'indent' not in parsed_data:
                      print(f"ERROR Parser L{i+1}: 'indent' key missing in parsed_data for type '{item_type}'. Line: '{line_to_parse.strip()}'")
                      continue
                 item_to_add = {
                     "line_index": i, "type": item_type, "character_tag": char_tag,
                     "variable_name": variable_name, "text": text, "context": current_context,
                     "context_data": current_context_data, "parsed_data": parsed_data,
                     "has_breakpoint": has_breakpoint }
                 parsed_items.append(item_to_add)
             continue 

        
        

    print(f"Контекстный парсер завершен. Найдено {len(parsed_items)} потенциальных элементов.")
    return parsed_items



def format_line_from_components(item_data, new_text):
    if not item_data or 'parsed_data' not in item_data or 'type' not in item_data:
         print("Ошибка: Отсутствуют данные 'parsed_data' или 'type' для форматирования строки.")
         return None 

    parsed_data = item_data['parsed_data']
    item_type = item_data['type'] 
    rule = parsed_data.get('reconstruction_rule', item_type)
    escaped_new_text = new_text.replace('"', '\\"') 

    
    uses_underscore = parsed_data.get('uses_underscore', False) 
    indent = parsed_data.get('indent', '') 
    prefix_content = parsed_data.get('prefix_content', '') 
    prefix = parsed_data.get('prefix', '') 
    suffix = parsed_data.get('suffix', '') 
    keyword = parsed_data.get('keyword', '') 
    variable_name = parsed_data.get('variable_name') 
    has_dollar = parsed_data.get('has_dollar', False) 
    define_keyword = parsed_data.get('keyword') 

    

    
    if rule == "variable": 
        dollar_prefix = "$ " if has_dollar else "" 
        return f'{indent}{dollar_prefix}{variable_name} = "{escaped_new_text}"{suffix}'
    elif rule == "define_variable": 
         return f'{indent}{define_keyword} {variable_name} = "{escaped_new_text}"{suffix}'

    
    elif rule == "standard":
        return f'{prefix}"{escaped_new_text}"{suffix}'
    elif rule == "choice" or item_type == "choice":
        return f'{indent}"{escaped_new_text}"{suffix}'
    elif rule in ("screen_button", "screen_label", "screen_text_statement") \
      or item_type in ("screen_button", "screen_textbutton", "screen_label", "screen_text_statement"):
        keyword_part = f"{keyword} " if keyword else ""
        if uses_underscore: return f'{indent}{keyword_part}_("{escaped_new_text}"){suffix}'
        else: return f'{indent}{keyword_part}"{escaped_new_text}"{suffix}'
    elif rule == "screen_property" or item_type == "screen_text_property":
        prefix_part = f"{prefix_content} " if prefix_content and prefix_content.strip() else prefix_content
        full_prefix = f"{indent}{prefix_part}"
        if uses_underscore: return f'{full_prefix}{keyword} _("{escaped_new_text}"){suffix}'
        else: return f'{full_prefix}{keyword} "{escaped_new_text}"{suffix}'
    elif rule == "narration" or (item_type == "translate_translation" and not item_data.get('character_tag')):
         return f'{indent}"{escaped_new_text}"{suffix}'
    elif rule == "translate_new" or item_type == "translate_new":
        return f'{indent}new "{escaped_new_text}"{suffix}'
    elif item_type == "translate_old":
        original_escaped = item_data.get('text', '').replace('"', '\\"')
        return f'{indent}old "{original_escaped}"{suffix}'
    elif item_type == "translate_potential_original":
         original_full_content = parsed_data.get('original_full_comment_content', item_data.get('text', ''))
         return f'{indent}# {original_full_content}'
    else:
        print(f"Предупреждение: Неизвестный тип/правило '{item_type}'/'{rule}' при форматировании строки {item_data.get('line_index', '?') + 1}.")
        return f'{indent}"{escaped_new_text}"{suffix}'



print("renforge_parser.py (contextual) loaded") 