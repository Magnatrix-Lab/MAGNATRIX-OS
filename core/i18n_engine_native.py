#!/usr/bin/env python3
"""
i18n Engine for MAGNATRIX-OS
Multi-language support, translation, locale detection, pluralization.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


class I18nEngine:
    """Internationalization engine."""

    def __init__(self, default_locale: str = 'en') -> None:
        self._default_locale = default_locale
        self._current_locale = default_locale
        self._translations: Dict[str, Dict[str, str]] = {}

    def load_translations(self, locale: str, translations: Dict[str, str]) -> None:
        self._translations[locale] = translations

    def load_from_file(self, locale: str, file_path: str) -> None:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self._translations[locale] = json.load(f)

    def set_locale(self, locale: str) -> None:
        self._current_locale = locale

    def get_locale(self) -> str:
        return self._current_locale

    def translate(self, key: str, **kwargs: Any) -> str:
        locale = self._current_locale
        translations = self._translations.get(locale, {})
        text = translations.get(key, key)

        # Format with kwargs
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    def pluralize(self, key: str, count: int, **kwargs: Any) -> str:
        locale = self._current_locale
        translations = self._translations.get(locale, {})

        # Simple pluralization rules
        if locale == 'en':
            plural_key = f"{key}_plural" if count != 1 else key
        elif locale == 'id':
            plural_key = key  # No plural in Indonesian
        else:
            plural_key = f"{key}_plural" if count != 1 else key

        text = translations.get(plural_key, key)
        return text.format(count=count, **kwargs)

    def detect_locale(self, text: str) -> str:
        """Simple locale detection based on character patterns."""
        if any('\u0600' <= c <= '\u06FF' for c in text):
            return 'ar'
        if any('\u0400' <= c <= '\u04FF' for c in text):
            return 'ru'
        if any('\u4E00' <= c <= '\u9FFF' for c in text):
            return 'zh'
        if any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' for c in text):
            return 'ja'
        return 'en'

    def list_locales(self) -> List[str]:
        return list(self._translations.keys())


def _demo() -> None:
    print("=== i18n Engine Demo ===\n")

    i18n = I18nEngine()

    # Load translations
    i18n.load_translations('en', {
        'hello': 'Hello, {name}!',
        'items': '{count} item',
        'items_plural': '{count} items',
    })

    i18n.load_translations('id', {
        'hello': 'Halo, {name}!',
        'items': '{count} item',
    })

    i18n.load_translations('es', {
        'hello': 'Hola, {name}!',
        'items': '{count} item',
        'items_plural': '{count} items',
    })

    # Translate
    i18n.set_locale('en')
    print(f"EN: {i18n.translate('hello', name='World')}")
    print(f"EN plural: {i18n.pluralize('items', 1, count=1)}")
    print(f"EN plural: {i18n.pluralize('items', 5, count=5)}")

    i18n.set_locale('id')
    print(f"ID: {i18n.translate('hello', name='Dunia')}")
    print(f"ID plural: {i18n.pluralize('items', 5, count=5)}")

    # Detect
    print(f"Detected locale: {i18n.detect_locale('Hello world')}")

    print("\n=== i18n Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
