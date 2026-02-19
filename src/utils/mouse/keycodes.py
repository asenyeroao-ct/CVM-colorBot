import re


_DIGIT_TO_HID = {
    "1": 30,
    "2": 31,
    "3": 32,
    "4": 33,
    "5": 34,
    "6": 35,
    "7": 36,
    "8": 37,
    "9": 38,
    "0": 39,
}

_DIGIT_TO_VK = {
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
}


def _build_vk_by_name():
    mapping = {
        "BACKSPACE": 0x08,
        "TAB": 0x09,
        "ENTER": 0x0D,
        "SHIFT": 0x10,
        "CONTROL": 0x11,
        "MENU": 0x12,  # Alt
        "PAUSE": 0x13,
        "CAPSLOCK": 0x14,
        "ESCAPE": 0x1B,
        "SPACE": 0x20,
        "PAGEUP": 0x21,
        "PAGEDOWN": 0x22,
        "END": 0x23,
        "HOME": 0x24,
        "LEFT": 0x25,
        "UP": 0x26,
        "RIGHT": 0x27,
        "DOWN": 0x28,
        "PRINTSCREEN": 0x2C,
        "INSERT": 0x2D,
        "DELETE": 0x2E,
        "LWIN": 0x5B,
        "RWIN": 0x5C,
        "APPS": 0x5D,
        "NUMPAD0": 0x60,
        "NUMPAD1": 0x61,
        "NUMPAD2": 0x62,
        "NUMPAD3": 0x63,
        "NUMPAD4": 0x64,
        "NUMPAD5": 0x65,
        "NUMPAD6": 0x66,
        "NUMPAD7": 0x67,
        "NUMPAD8": 0x68,
        "NUMPAD9": 0x69,
        "MULTIPLY": 0x6A,
        "ADD": 0x6B,
        "SEPARATOR": 0x6C,
        "SUBTRACT": 0x6D,
        "DECIMAL": 0x6E,
        "DIVIDE": 0x6F,
        "NUMLOCK": 0x90,
        "SCROLLLOCK": 0x91,
        "LSHIFT": 0xA0,
        "RSHIFT": 0xA1,
        "LCONTROL": 0xA2,
        "RCONTROL": 0xA3,
        "LMENU": 0xA4,  # Left Alt
        "RMENU": 0xA5,  # Right Alt
        "OEM_1": 0xBA,      # ;:
        "OEM_PLUS": 0xBB,   # =+
        "OEM_COMMA": 0xBC,  # ,<
        "OEM_MINUS": 0xBD,  # -_
        "OEM_PERIOD": 0xBE, # .>
        "OEM_2": 0xBF,      # /?
        "OEM_3": 0xC0,      # `~
        "OEM_4": 0xDB,      # [{
        "OEM_5": 0xDC,      # \|
        "OEM_6": 0xDD,      # ]}
        "OEM_7": 0xDE,      # '"
    }

    for idx, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        mapping[letter] = 0x41 + idx
    mapping.update({
        "W": 0x57,
        "A": 0x41,
        "S": 0x53,
        "D": 0x44,
    })
    for digit, vk in _DIGIT_TO_VK.items():
        mapping[digit] = vk
    for i in range(1, 25):
        mapping[f"F{i}"] = 0x6F + i
    return mapping


def _build_hid_by_name():
    mapping = {
        "ENTER": 40,
        "ESCAPE": 41,
        "BACKSPACE": 42,
        "TAB": 43,
        "SPACE": 44,
        "MINUS": 45,
        "EQUAL": 46,
        "LEFTBRACKET": 47,
        "RIGHTBRACKET": 48,
        "BACKSLASH": 49,
        "SEMICOLON": 51,
        "APOSTROPHE": 52,
        "GRAVE": 53,
        "COMMA": 54,
        "PERIOD": 55,
        "SLASH": 56,
        "CAPSLOCK": 57,
        "F1": 58,
        "F2": 59,
        "F3": 60,
        "F4": 61,
        "F5": 62,
        "F6": 63,
        "F7": 64,
        "F8": 65,
        "F9": 66,
        "F10": 67,
        "F11": 68,
        "F12": 69,
        "PRINTSCREEN": 70,
        "SCROLLLOCK": 71,
        "PAUSE": 72,
        "INSERT": 73,
        "HOME": 74,
        "PAGEUP": 75,
        "DELETE": 76,
        "END": 77,
        "PAGEDOWN": 78,
        "RIGHT": 79,
        "LEFT": 80,
        "DOWN": 81,
        "UP": 82,
        "NUMLOCK": 83,
        "APPLICATION": 101,
        "LCTRL": 224,
        "LSHIFT": 225,
        "LALT": 226,
        "LGUI": 227,
        "RCTRL": 228,
        "RSHIFT": 229,
        "RALT": 230,
        "RGUI": 231,
    }

    for idx, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        mapping[letter] = 4 + idx
    # Explicit common movement keys for readability.
    mapping.update({
        "W": 26,  # HID Keyboard W
        "A": 4,   # HID Keyboard A
        "S": 22,  # HID Keyboard S
        "D": 7,   # HID Keyboard D
    })
    for digit, hid in _DIGIT_TO_HID.items():
        mapping[digit] = hid
    for i in range(13, 25):
        mapping[f"F{i}"] = 104 + (i - 13)
    return mapping


_VK_BY_NAME = _build_vk_by_name()
_HID_BY_NAME = _build_hid_by_name()

_ALIASES = {
    "ESC": "ESCAPE",
    "DEL": "DELETE",
    "INS": "INSERT",
    "PGUP": "PAGEUP",
    "PGDN": "PAGEDOWN",
    "RETURN": "ENTER",
    "SPACEBAR": "SPACE",
    "CTRL": "CONTROL",
    "ALT": "MENU",
    "WIN": "LWIN",
    "CMD": "LWIN",
    "OPTION": "LMENU",
    "LCTRL": "LCONTROL",
    "RCTRL": "RCONTROL",
    "LALT": "LMENU",
    "RALT": "RMENU",
    "LBRACKET": "LEFTBRACKET",
    "RBRACKET": "RIGHTBRACKET",
    "BACKQUOTE": "GRAVE",
    "TILDE": "GRAVE",
    "DOT": "PERIOD",
    "QUOTE": "APOSTROPHE",
    "PRTSC": "PRINTSCREEN",
    "SNAPSHOT": "PRINTSCREEN",
}

_ALIASES_HID = {
    "CTRL": "LCTRL",
    "CONTROL": "LCTRL",
    "ALT": "LALT",
    "MENU": "LALT",
    "WIN": "LGUI",
    "CMD": "LGUI",
    "OPTION": "LALT",
    "DELETE": "DELETE",
}


def _safe_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    return None


def _parse_int_text(text):
    raw = str(text).strip()
    if not raw:
        return None
    try:
        return int(raw, 0)
    except Exception:
        return None


def _strip_prefix(raw):
    match = re.match(r"^(VK|HID)\s*[:_ ]\s*(.+)$", str(raw).strip(), flags=re.IGNORECASE)
    if match:
        return match.group(1).upper(), match.group(2).strip()
    return None, str(raw).strip()


def _normalize_name(raw):
    if raw is None:
        return None
    token = str(raw).strip().upper().replace("-", "_").replace(" ", "_")
    if not token:
        return None
    if token.startswith("VK_"):
        token = token[3:]
    if token.startswith("KEY_"):
        token = token[4:]
    return token


def _hid_to_vk(hid_code):
    if hid_code is None:
        return None
    try:
        hid_code = int(hid_code)
    except Exception:
        return None

    # Letters
    if 4 <= hid_code <= 29:
        return 0x41 + (hid_code - 4)
    # Digits row (1..9,0)
    if 30 <= hid_code <= 38:
        return 0x31 + (hid_code - 30)
    if hid_code == 39:
        return 0x30

    by_hid = {
        40: _VK_BY_NAME["ENTER"],
        41: _VK_BY_NAME["ESCAPE"],
        42: _VK_BY_NAME["BACKSPACE"],
        43: _VK_BY_NAME["TAB"],
        44: _VK_BY_NAME["SPACE"],
        57: _VK_BY_NAME["CAPSLOCK"],
        58: _VK_BY_NAME["F1"],
        59: _VK_BY_NAME["F2"],
        60: _VK_BY_NAME["F3"],
        61: _VK_BY_NAME["F4"],
        62: _VK_BY_NAME["F5"],
        63: _VK_BY_NAME["F6"],
        64: _VK_BY_NAME["F7"],
        65: _VK_BY_NAME["F8"],
        66: _VK_BY_NAME["F9"],
        67: _VK_BY_NAME["F10"],
        68: _VK_BY_NAME["F11"],
        69: _VK_BY_NAME["F12"],
        70: _VK_BY_NAME["PRINTSCREEN"],
        71: _VK_BY_NAME["SCROLLLOCK"],
        72: _VK_BY_NAME["PAUSE"],
        73: _VK_BY_NAME["INSERT"],
        74: _VK_BY_NAME["HOME"],
        75: _VK_BY_NAME["PAGEUP"],
        76: _VK_BY_NAME["DELETE"],
        77: _VK_BY_NAME["END"],
        78: _VK_BY_NAME["PAGEDOWN"],
        79: _VK_BY_NAME["RIGHT"],
        80: _VK_BY_NAME["LEFT"],
        81: _VK_BY_NAME["DOWN"],
        82: _VK_BY_NAME["UP"],
        83: _VK_BY_NAME["NUMLOCK"],
        224: _VK_BY_NAME["LCONTROL"],
        225: _VK_BY_NAME["LSHIFT"],
        226: _VK_BY_NAME["LMENU"],
        227: _VK_BY_NAME["LWIN"],
        228: _VK_BY_NAME["RCONTROL"],
        229: _VK_BY_NAME["RSHIFT"],
        230: _VK_BY_NAME["RMENU"],
        231: _VK_BY_NAME["RWIN"],
    }
    return by_hid.get(hid_code)


def _vk_to_hid(vk_code):
    if vk_code is None:
        return None
    try:
        vk_code = int(vk_code)
    except Exception:
        return None

    # Letters
    if 0x41 <= vk_code <= 0x5A:
        return 4 + (vk_code - 0x41)
    # Digits row
    if 0x31 <= vk_code <= 0x39:
        return 30 + (vk_code - 0x31)
    if vk_code == 0x30:
        return 39

    by_vk = {
        _VK_BY_NAME["ENTER"]: 40,
        _VK_BY_NAME["ESCAPE"]: 41,
        _VK_BY_NAME["BACKSPACE"]: 42,
        _VK_BY_NAME["TAB"]: 43,
        _VK_BY_NAME["SPACE"]: 44,
        _VK_BY_NAME["CAPSLOCK"]: 57,
        _VK_BY_NAME["F1"]: 58,
        _VK_BY_NAME["F2"]: 59,
        _VK_BY_NAME["F3"]: 60,
        _VK_BY_NAME["F4"]: 61,
        _VK_BY_NAME["F5"]: 62,
        _VK_BY_NAME["F6"]: 63,
        _VK_BY_NAME["F7"]: 64,
        _VK_BY_NAME["F8"]: 65,
        _VK_BY_NAME["F9"]: 66,
        _VK_BY_NAME["F10"]: 67,
        _VK_BY_NAME["F11"]: 68,
        _VK_BY_NAME["F12"]: 69,
        _VK_BY_NAME["SCROLLLOCK"]: 71,
        _VK_BY_NAME["PAUSE"]: 72,
        _VK_BY_NAME["INSERT"]: 73,
        _VK_BY_NAME["HOME"]: 74,
        _VK_BY_NAME["PAGEUP"]: 75,
        _VK_BY_NAME["DELETE"]: 76,
        _VK_BY_NAME["END"]: 77,
        _VK_BY_NAME["PAGEDOWN"]: 78,
        _VK_BY_NAME["RIGHT"]: 79,
        _VK_BY_NAME["LEFT"]: 80,
        _VK_BY_NAME["DOWN"]: 81,
        _VK_BY_NAME["UP"]: 82,
        _VK_BY_NAME["NUMLOCK"]: 83,
        _VK_BY_NAME["LCONTROL"]: 224,
        _VK_BY_NAME["LSHIFT"]: 225,
        _VK_BY_NAME["LMENU"]: 226,
        _VK_BY_NAME["LWIN"]: 227,
        _VK_BY_NAME["RCONTROL"]: 228,
        _VK_BY_NAME["RSHIFT"]: 229,
        _VK_BY_NAME["RMENU"]: 230,
        _VK_BY_NAME["RWIN"]: 231,
    }
    return by_vk.get(vk_code)


def to_vk_code(value):
    direct = _safe_int(value)
    if direct is not None:
        return int(direct)

    prefix, body = _strip_prefix(value)
    if not body:
        return None

    if prefix == "HID":
        hid = to_hid_code(body)
        return _hid_to_vk(hid)

    numeric = _parse_int_text(body)
    if numeric is not None:
        return int(numeric)

    token = _normalize_name(body)
    if token is None:
        return None

    token = _ALIASES.get(token, token)
    vk = _VK_BY_NAME.get(token)
    if vk is not None:
        return vk

    hid = _HID_BY_NAME.get(token)
    if hid is not None:
        return _hid_to_vk(hid)

    return None


def to_hid_code(value):
    direct = _safe_int(value)
    if direct is not None:
        return int(direct)

    prefix, body = _strip_prefix(value)
    if not body:
        return None

    if prefix == "VK":
        vk = to_vk_code(body)
        return _vk_to_hid(vk)

    numeric = _parse_int_text(body)
    if numeric is not None:
        return int(numeric)

    token = _normalize_name(body)
    if token is None:
        return None

    token = _ALIASES.get(token, token)
    token = _ALIASES_HID.get(token, token)
    hid = _HID_BY_NAME.get(token)
    if hid is not None:
        return hid

    vk = _VK_BY_NAME.get(token)
    if vk is not None:
        return _vk_to_hid(vk)

    return None


def to_key_token(value):
    if value is None:
        return None
    numeric = _safe_int(value)
    if numeric is not None:
        return str(int(numeric))

    prefix, body = _strip_prefix(value)
    if not body:
        return None

    if prefix == "VK":
        vk = to_vk_code(body)
        if vk is None:
            return None
        return str(int(vk))
    if prefix == "HID":
        hid = to_hid_code(body)
        if hid is None:
            return None
        return str(int(hid))

    numeric_text = _parse_int_text(body)
    if numeric_text is not None:
        return str(int(numeric_text))

    token = _normalize_name(body)
    if token is None:
        return None
    if len(token) == 1 and token.isalnum():
        return f"KEY_{token}"
    if token.startswith("KEY_"):
        return token
    return token
