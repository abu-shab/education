import re
import unicodedata

DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).translate(DIGITS).lower()
    text = re.sub(r'[\u064b-\u065f\u0670\u0640]', '', text)
    text = text.translate(str.maketrans('أإآٱى', 'ااااي'))
    # Join known spaced code families only. "Science 2022" and "Minor 2024"
    # are program/year phrases, not course codes.
    text = re.sub(r'\b(t|cs|math)[\s-]+(\d{2,6})\b', r'\1\2', text)
    return re.sub(r'\s+', ' ', text).strip()

def tokens(text: str) -> list[str]:
    return re.findall(r'[a-z]+\d+|[\w]+', normalize(text))

def codes(text: str) -> list[str]:
    return sorted(set(x.upper() for x in re.findall(r'(?<!\w)(?:[a-z]{1,8}\d{2,6}|\d{2,3}[a-z]{1,3}\d{1,3}|\d{5})(?!\w)', normalize(text))))

def expand_query(text: str) -> str:
    n = normalize(text)
    aliases = {
        'غبت': 'غياب حضور', 'بغيب': 'غياب حضور', 'الحضور': 'حضور غياب',
        'اسحب': 'انسحاب سحب', 'بقدر اسجل': 'تسجيل متطلبات سابقة',
        'معدلي': 'معدل تسجيل ساعات حد ادنى اقصى', 'برمجه': 'برمجة',
        'رسبت': 'رسوب اعادة', 'تحذير': 'انذار اكاديمي',
    }
    return text + ' ' + ' '.join(v for k, v in aliases.items() if k in n)
