from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport": r"\b[a-zA-Z]\d{7,8}\b",
    "address_vn": (
        r"(?:địa chỉ|dia chi|đ/c|dc|nơi ở|noi o|thường trú|thuong tru|tạm trú|tam tru|quê quán|que quan)\s*[:=-]\s*[^,\n;]+(?:[,\s]+[^,\n;]+){1,5}|"
        r"\b(?:(?:số|so|số nhà|so nha)\s+)?\d+[\w/,-]*\s+(?:đường|duong|đ\.|d\.|phố|pho|ngõ|ngo|ngách|ngach|hẻm|hem|kiệt|kiet)\s+[^,\n;]+(?:[,\s]+(?:phường|phuong|p\.|p\b|xã|xa|x\.|x\b|quận|quan|q\.|q\b|huyện|huyen|h\.|h\b|thị xã|thi xa|tx\.|tx\b|thị trấn|thi tran|tt\.|tt\b|thành phố|thanh pho|tp\.|tp\b|tỉnh|tinh|t\.|hà nội|ha noi|hồ chí minh|ho chi minh|hcm|tphcm|đà nẵng|da nang|hải phòng|hai phong|cần thơ|can tho)\s*[\w\s.-]*)+|"
        r"\b(?:phường|phuong|p\.\s*|p\b\s*\d+|xã|xa)\s*[\w\s.-]+[,\s]+(?:quận|quan|q\.\s*|q\b\s*\d+|huyện|huyen|thị xã|thi xa|tx\.)\s*[\w\s.-]+(?:[,\s]+(?:thành phố|thanh pho|tp\.\s*|tp\b\s*|tỉnh|tinh\s*|hà nội|ha noi|hcm|tphcm|đà nẵng|da nang)?[\w\s.-]+)*"
    ),
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe, flags=re.IGNORECASE)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
