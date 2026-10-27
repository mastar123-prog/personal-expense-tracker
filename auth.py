"""Authentication and user management for Lumen.

Uses standard library hashlib.pbkdf2_hmac with random salts for secure,
dependency-free password hashing.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime
from typing import Any

import streamlit as st

import db

ITERATIONS = 120_000
HASH_ALGO = "sha256"


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    salt_bytes = salt if salt is not None else os.urandom(16)
    key = hashlib.pbkdf2_hmac(HASH_ALGO, password.encode("utf-8"), salt_bytes, ITERATIONS)
    return key.hex(), salt_bytes.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Verify password against the stored hash and salt."""
    salt_bytes = bytes.fromhex(salt_hex)
    computed_key, _ = hash_password(password, salt=salt_bytes)
    return hashlib.sha256(computed_key.encode()).digest() == hashlib.sha256(hash_hex.encode()).digest()


def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str = "",
    avatar: str = "👤",
) -> tuple[bool, str, dict[str, Any] | None]:
    """Register a new user. Returns (success, message, user_dict)."""
    username = username.strip().lower()
    email = email.strip().lower()

    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters.", None
    if not email or "@" not in email:
        return False, "Please enter a valid email address.", None
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters.", None

    pwd_hash, salt = hash_password(password)
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with db._conn() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, salt, full_name, avatar, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (username, email, pwd_hash, salt, full_name.strip() or username.title(), avatar or "👤", now),
            )
            user_id = cur.lastrowid

            # Seed default categories for this user
            for cat, t_type, emoji, color in db.DEFAULT_CATEGORIES:
                con.execute(
                    """
                    INSERT OR IGNORE INTO categories (name, type, emoji, color, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cat, t_type, emoji, color, user_id),
                )

            # Seed default settings
            for k, v in db.DEFAULT_SETTINGS.items():
                val = username.title() if k == "user_name" else v
                con.execute(
                    """
                    INSERT OR IGNORE INTO settings (key, value, user_id)
                    VALUES (?, ?, ?)
                    """,
                    (k, val, user_id),
                )

        user = get_user_by_id(user_id)
        return True, "Account created successfully!", user
    except sqlite3.IntegrityError as e:
        msg = str(e).lower()
        if "username" in msg:
            return False, "Username is already taken. Please pick another.", None
        if "email" in msg:
            return False, "Email is already registered. Please sign in.", None
        return False, "An account with these details already exists.", None


def authenticate_user(username_or_email: str, password: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Authenticate via username or email. Returns (success, message, user_dict)."""
    identifier = username_or_email.strip().lower()
    if not identifier or not password:
        return False, "Please fill in all fields.", None

    with db._conn() as con:
        row = con.execute(
            """
            SELECT id, username, email, password_hash, salt, full_name, avatar, created_at
            FROM users
            WHERE username = ? OR email = ?
            """,
            (identifier, identifier),
        ).fetchone()

    if not row:
        return False, "Invalid username or password.", None

    if not verify_password(password, row["password_hash"], row["salt"]):
        return False, "Invalid username or password.", None

    user = {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"] or row["username"].title(),
        "avatar": row["avatar"] or "👤",
        "created_at": row["created_at"],
    }
    return True, f"Welcome back, {user['full_name']}!", user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Fetch user dict by primary key ID."""
    with db._conn() as con:
        row = con.execute(
            """
            SELECT id, username, email, full_name, avatar, created_at
            FROM users
            WHERE id = ?
            """,
            (int(user_id),),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"] or row["username"].title(),
        "avatar": row["avatar"] or "👤",
        "created_at": row["created_at"],
    }


def update_profile(user_id: int, full_name: str, avatar: str) -> None:
    """Update profile name and avatar."""
    with db._conn() as con:
        con.execute(
            "UPDATE users SET full_name = ?, avatar = ? WHERE id = ?",
            (full_name.strip(), avatar.strip() or "👤", int(user_id)),
        )


def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
    """Change user password after verifying the old password."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    with db._conn() as con:
        row = con.execute(
            "SELECT password_hash, salt FROM users WHERE id = ?", (int(user_id),)
        ).fetchone()

    if not row or not verify_password(old_password, row["password_hash"], row["salt"]):
        return False, "Current password is incorrect."

    new_hash, new_salt = hash_password(new_password)
    with db._conn() as con:
        con.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (new_hash, new_salt, int(user_id)),
        )
    return True, "Password updated successfully!"


def get_current_user() -> dict[str, Any] | None:
    """Retrieve the current user from st.session_state if present."""
    return st.session_state.get("user")


def sign_in(user: dict[str, Any]) -> None:
    """Store user in session state and reload."""
    st.session_state["user"] = user
    st.rerun()


def sign_out() -> None:
    """Clear session and sign out."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def render_auth_page() -> None:
    """Render the glassmorphic sign in and sign up portal."""
    import ui

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        ui.html(
            """
            <div style="text-align:center;margin:1rem 0 1.6rem">
              <div style="font-size:3.2rem;display:inline-block;animation:lm-float 4s ease-in-out infinite">✨</div>
              <h1 class="lm-hero-title" style="font-size:2.35rem;margin:.3rem 0 .2rem">Lumen</h1>
              <div class="lm-muted" style="font-size:1.02rem">Your personal finance sanctuary</div>
            </div>
            """
        )

        tab_login, tab_signup = st.tabs(["🔑  Sign In", "✨  Create Account"])

        with tab_login:
            with st.form("login_form", border=True):
                st.markdown("**Welcome back!** Sign in to your ledger:")
                ident = st.text_input("Username or Email", placeholder="e.g. demo or you@email.com")
                pwd = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button(
                    "Sign In", type="primary", icon=":material/login:", width="stretch"
                )

                if submitted:
                    ok, msg, user = authenticate_user(ident, pwd)
                    if ok and user:
                        st.toast(msg, icon="🎉")
                        sign_in(user)
                    else:
                        st.error(msg)

            st.markdown(
                "<div style='text-align:center;margin:.8rem 0 .4rem' class='lm-muted'>— or —</div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "⚡ Instant Demo Login (demo / demo123)",
                width="stretch",
                icon=":material/bolt:",
            ):
                ok, msg, user = authenticate_user("demo", "demo123")
                if ok and user:
                    st.toast("Signed in as Demo Explorer!", icon="✨")
                    sign_in(user)
                else:
                    st.error("Demo account could not be found.")

        with tab_signup:
            with st.form("signup_form", border=True):
                st.markdown("**New to Lumen?** Set up your personal ledger in seconds:")
                c1, c2 = st.columns([3, 1])
                full_name = c1.text_input("Full Name", placeholder="e.g. Alex Morgan")
                avatar = c2.selectbox(
                    "Avatar", ["👤", "✨", "🚀", "💎", "🦁", "🌸", "🥑", "🦊", "🌟", "🎯"]
                )
                username = st.text_input("Username", placeholder="e.g. alex")
                email = st.text_input("Email", placeholder="e.g. alex@example.com")
                p1, p2 = st.columns(2)
                password = p1.text_input("Password", type="password", placeholder="At least 6 chars")
                confirm_password = p2.text_input(
                    "Confirm Password", type="password", placeholder="Re-enter password"
                )
                create_submitted = st.form_submit_button(
                    "Create Account",
                    type="primary",
                    icon=":material/person_add:",
                    width="stretch",
                )

                if create_submitted:
                    if password != confirm_password:
                        st.error("Passwords do not match!")
                    else:
                        ok, msg, user = register_user(
                            username, email, password, full_name, avatar
                        )
                        if ok and user:
                            st.toast(msg, icon="🎉")
                            sign_in(user)
                        else:
                            st.error(msg)

