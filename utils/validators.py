import re
import logging

logger = logging.getLogger(__name__)

def validate_channel_link(link):
    """Проверить валидность ссылки на канал"""
    if not link:
        return False
    link = link.strip()
    return link.startswith("@") or link.startswith("https://t.me/")

def extract_channel(link):
    """Извлечь название канала из ссылки"""
    if not link:
        return None
    if link.startswith("@"):
        return link
    match = re.search(r'(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)', link)
    return "@" + match.group(1) if match else link

def validate_number(text, allow_zero=False):
    """Проверить является ли те��ст числом"""
    try:
        num = float(text) if '.' in text else int(text)
        if not allow_zero and num <= 0:
            return False
        return num
    except (ValueError, TypeError):
        return None

def validate_quantity_in_range(qty, min_val, max_val):
    """Проверить количество в диапазоне"""
    try:
        qty = int(qty)
        return min_val <= qty <= max_val
    except ValueError:
        return False