"""Simple UI translations: one JSON file per language."""
import json
import os

DEFAULT_LANGUAGE = "en"
LANGUAGE_NAMES = {
    "en": "English",
    "zh-CN": "简体中文",
}


def _locales_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "locales",
    )


class I18n:
    def __init__(self):
        self._language = DEFAULT_LANGUAGE
        self._strings = {}
        self._names = dict(LANGUAGE_NAMES)
        self._load(self._language)

    @property
    def language(self):
        return self._language

    def available(self):
        found = {}
        locales = _locales_dir()
        if os.path.isdir(locales):
            for name in os.listdir(locales):
                if not name.lower().endswith(".json"):
                    continue
                path = os.path.join(locales, name)
                code = os.path.splitext(name)[0]
                display = LANGUAGE_NAMES.get(code, code)
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        data = json.load(handle) or {}
                    code = str(data.get("code") or code).strip() or code
                    display = str(data.get("name") or display).strip() or display
                except Exception:
                    pass
                found[code] = display
        for code, display in LANGUAGE_NAMES.items():
            found.setdefault(code, display)
        order = ["en", "zh-CN"]
        items = [(code, found[code]) for code in order if code in found]
        items.extend(sorted((code, name) for code, name in found.items() if code not in order))
        return items

    def display_names(self):
        return [name for _code, name in self.available()]

    def code_for_name(self, name):
        wanted = str(name or "").strip()
        for code, display in self.available():
            if display == wanted or code == wanted:
                return code
        return DEFAULT_LANGUAGE

    def name_for_code(self, code=None):
        lang = self.normalize(code if code is not None else self._language)
        for item_code, display in self.available():
            if item_code == lang:
                return display
        return LANGUAGE_NAMES.get(lang, lang)

    def normalize(self, code):
        raw = str(code or "").strip().replace("_", "-")
        if not raw:
            return DEFAULT_LANGUAGE
        lowered = raw.lower()
        if lowered in ("en", "en-us", "english"):
            return "en"
        if lowered in ("zh", "zh-cn", "zh-hans", "cn", "chs", "simplified chinese", "简体中文"):
            return "zh-CN"
        for item_code, display in self.available():
            if item_code.lower() == lowered or display == raw:
                return item_code
        return DEFAULT_LANGUAGE

    def set_language(self, code):
        lang = self.normalize(code)
        self._language = lang
        self._load(lang)
        return lang

    def t(self, text, **kwargs):
        key = "" if text is None else str(text)
        if not key:
            return ""
        value = self._strings.get(key, key)
        if kwargs:
            try:
                value = str(value).format(**kwargs)
            except Exception:
                pass
        return value

    def heading(self, text):
        value = self.t(text)
        if self._language == "en":
            return str(value).upper()
        return value

    def _load(self, code):
        path = os.path.join(_locales_dir(), f"{code}.json")
        data = {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
        except Exception:
            data = {}
        strings = data.get("strings", data) if isinstance(data, dict) else {}
        self._strings = strings if isinstance(strings, dict) else {}
        name = str(data.get("name") or LANGUAGE_NAMES.get(code) or code)
        self._names[code] = name


i18n = I18n()


def t(text, **kwargs):
    return i18n.t(text, **kwargs)


def heading(text):
    return i18n.heading(text)
