"""
ScoreSight Platform · Auth
==========================

One common sign-in entry point; the issued token carries the role used to gate
every portal endpoint. Prototype-grade (opaque in-memory tokens) — not for
production. Credentials per the platform spec.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

# username (case-insensitive) -> (password, role, display_name)
ACCOUNTS: dict[str, tuple[str, str, str]] = {
    "bankuser_123": ("Bankuser_123", "bank_user", "RM · Chuyên viên QHKH"),
    "bank_admin": ("Bank_admin", "admin", "Quản trị & Kiểm toán"),
    "customer_123": ("Customer_123", "customer", "Công ty TNHH Demo SME"),
    "customer_green": ("Customer_green", "customer", "Công ty TNHH Sản xuất Minh Long"),
}

ROLE_HOME = {
    "customer": "/customer/dashboard",
    "bank_user": "/bank/cases",
    "admin": "/admin/dashboard",
}

# token -> session
_SESSIONS: dict[str, dict] = {}


def login(username: str, password: str) -> dict:
    rec = ACCOUNTS.get(username.strip().lower())
    if not rec or rec[0] != password:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu.")
    _, role, display = rec
    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = {"username": username.strip().lower(), "role": role, "display_name": display}
    return {"token": token, "role": role, "display_name": display, "home": ROLE_HOME[role]}


def session_of(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Thiếu token xác thực.")
    token = authorization.split(" ", 1)[1].strip()
    sess = _SESSIONS.get(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ.")
    return sess


def require_roles(*roles: str):
    def _dep(authorization: str | None = Header(default=None)) -> dict:
        sess = session_of(authorization)
        if sess["role"] not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập khu vực này.")
        return sess
    return _dep
