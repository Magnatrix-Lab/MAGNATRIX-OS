"""Native stdlib module: Locale Validator
Validates locale codes, date formats, and number formats for target markets.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class DateFormat(Enum):
    MDY = "MM/DD/YYYY"
    DMY = "DD/MM/YYYY"
    YMD = "YYYY-MM-DD"

class NumberFormat(Enum):
    DOT_COMMA = "1,234.56"
    COMMA_DOT = "1.234,56"
    SPACE_COMMA = "1 234,56"

@dataclass
class LocaleRule:
    locale_code: str
    date_format: DateFormat
    number_format: NumberFormat
    currency_symbol: str
    text_direction: str = "ltr"

@dataclass
class LocaleValidator:
    project_name: str
    target_locales: List[LocaleRule] = field(default_factory=list)
    content_samples: List[str] = field(default_factory=list)

    def validate_dates(self, sample: str) -> List[str]:
        issues = []
        for locale in self.target_locales:
            if locale.date_format == DateFormat.MDY and "DD/MM" in sample:
                issues.append(f"{locale.locale_code}: possible DMY format found")
        return issues

    def locale_count(self) -> int:
        return len(self.target_locales)

    def rtl_count(self) -> int:
        return sum(1 for l in self.target_locales if l.text_direction == "rtl")

    def stats(self) -> Dict:
        return {
            "project": self.project_name,
            "locale_count": self.locale_count(),
            "rtl_locales": self.rtl_count(),
            "locales": [l.locale_code for l in self.target_locales],
        }

def run():
    lv = LocaleValidator(
        project_name="Global Website",
        target_locales=[
            LocaleRule("en-US", DateFormat.MDY, NumberFormat.DOT_COMMA, "$"),
            LocaleRule("de-DE", DateFormat.DMY, NumberFormat.COMMA_DOT, "€"),
            LocaleRule("ja-JP", DateFormat.YMD, NumberFormat.DOT_COMMA, "¥"),
            LocaleRule("ar-SA", DateFormat.DMY, NumberFormat.DOT_COMMA, "ر.س", "rtl"),
        ]
    )
    print(lv.stats())

if __name__ == "__main__":
    run()
