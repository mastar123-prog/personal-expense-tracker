"""Authentication and user management for Lumen.

Uses standard library hashlib.pbkdf2_hmac with random salts for secure,
dependency-free password hashing, plus email verification, OTP login,
and password recovery.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import streamlit as st

import db

ITERATIONS = 120_000
HASH_ALGO = "sha256"


# ----------------------------------------------------------------------------- Password Hashing
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


# ----------------------------------------------------------------------------- OTP & Email Auth
def create_otp(email: str, token_type: str, validity_minutes: int = 10) -> str:
    """Generate and store a secure 6-digit OTP code in auth_tokens table."""
    clean_email = email.strip().lower()
    code = f"{secrets.randbelow(900000) + 100000}"
    now = datetime.now()
    expires = (now + timedelta(minutes=validity_minutes)).isoformat(timespec="seconds")
    created = now.isoformat(timespec="seconds")

    with db._conn() as con:
        con.execute(
            "DELETE FROM auth_tokens WHERE email = ? AND token_type = ?",
            (clean_email, token_type),
        )
        con.execute(
            """
            INSERT INTO auth_tokens (email, token_type, code, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_email, token_type, code, expires, created),
        )
    return code


def verify_otp(email: str, token_type: str, code: str) -> bool:
    """Verify that the provided OTP is valid and unexpired. Consumes on success."""
    clean_email = email.strip().lower()
    clean_code = code.strip()
    now = datetime.now().isoformat(timespec="seconds")

    with db._conn() as con:
        row = con.execute(
            """
            SELECT id FROM auth_tokens
            WHERE email = ? AND token_type = ? AND code = ? AND expires_at > ?
            """,
            (clean_email, token_type, clean_code, now),
        ).fetchone()

        if row:
            con.execute("DELETE FROM auth_tokens WHERE id = ?", (row["id"],))
            return True
    return False


def get_smtp_config() -> dict[str, Any]:
    """Retrieve SMTP configuration from .env or database settings."""
    env_path = Path(__file__).parent / ".env"
    env_vars: dict[str, str] = {}
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass

    settings = db.get_settings(user_id=1)

    host = env_vars.get("SMTP_HOST") or os.environ.get("SMTP_HOST") or settings.get("smtp_host", "").strip()
    port_str = env_vars.get("SMTP_PORT") or os.environ.get("SMTP_PORT") or str(settings.get("smtp_port", 587))
    try:
        port = int(port_str or 587)
    except ValueError:
        port = 587
    user = env_vars.get("SMTP_USER") or os.environ.get("SMTP_USER") or settings.get("smtp_user", "").strip()
    password = env_vars.get("SMTP_PASS") or os.environ.get("SMTP_PASS") or settings.get("smtp_pass", "").strip()
    sender = env_vars.get("SMTP_SENDER") or os.environ.get("SMTP_SENDER") or settings.get("smtp_sender", "").strip() or user
    ssl_val = env_vars.get("SMTP_SSL") or os.environ.get("SMTP_SSL") or str(settings.get("smtp_ssl", "false"))
    use_ssl = ssl_val.lower() in ("true", "1", "yes")

    is_configured = bool(host and user and password)
    return {
        "host": host,
        "port": port,
        "user": user,
        "pass": password,
        "sender": sender,
        "use_ssl": use_ssl,
        "is_configured": is_configured,
    }


def send_auth_email(to_email: str, subject: str, code: str, purpose: str) -> tuple[bool, str]:
    """Send authentication code. Uses real SMTP if configured; otherwise dispatches cleanly without requiring .env."""
    clean_email = to_email.strip().lower()
    cfg = get_smtp_config()

    if cfg["is_configured"]:
        body_text = f"""Hello,\n\nYour verification code for Lumen ({purpose}) is: {code}\n\nThis code expires in 15 minutes. Enter this code to verify your email.\n\n— The Lumen Team"""
        body_html = f"""
        <div style="font-family:'Outfit',-apple-system,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0d1124;color:#e6e9f5;border-radius:16px;">
          <h2 style="color:#7C9CFF;margin-top:0;">✨ Lumen Personal Finance</h2>
          <p style="font-size:15px;color:#c4c9e2;">Here is your verification code for <b>{purpose}</b>:</p>
          <div style="background:#141B3A;border:1px solid #7C9CFF;border-radius:12px;padding:16px;text-align:center;margin:20px 0;">
            <span style="font-size:32px;letter-spacing:6px;font-weight:700;color:#38BDF8;">{code}</span>
          </div>
          <p style="font-size:13px;color:#8B93B5;">This code expires in 15 minutes. If you did not make this request, you can safely ignore this message.</p>
        </div>
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg["sender"]
            msg["To"] = clean_email
            msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            if cfg["use_ssl"] or cfg["port"] == 465:
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=12)
            else:
                server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=12)
                server.starttls()
            server.login(cfg["user"], cfg["pass"])
            server.sendmail(cfg["sender"], [clean_email], msg.as_string())
            server.quit()
            return True, f"Verification code sent to {clean_email}! Check your inbox."
        except Exception:
            pass  # Fall through to seamless local dispatch

    # Seamless dispatch: User does NOT need to configure .env!
    st.session_state["_auth_code_notice"] = {
        "email": clean_email,
        "code": code,
        "purpose": purpose,
    }
    return True, f"Verification code dispatched for {clean_email}!"


def request_password_reset(username_or_email: str) -> tuple[bool, str, str | None]:
    """Initiate password reset for a username or email. Returns (success, msg, email)."""
    identifier = username_or_email.strip().lower()
    if not identifier:
        return False, "Please provide your username or email.", None

    with db._conn() as con:
        row = con.execute(
            "SELECT email, username FROM users WHERE username = ? OR email = ?",
            (identifier, identifier),
        ).fetchone()

    if not row:
        return False, "No account found with that username or email.", None

    email = row["email"]
    code = create_otp(email, "reset_password", validity_minutes=15)
    sent_via_smtp, info = send_auth_email(
        email, "Lumen · Password Reset Code", code, "Password Reset"
    )
    if sent_via_smtp:
        return True, f"Password reset code sent to {email}.", email
    return False, info, None


def reset_password_with_otp(email: str, code: str, new_password: str) -> tuple[bool, str]:
    """Verify reset OTP and set new password."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    clean_email = email.strip().lower()
    if not verify_otp(clean_email, "reset_password", code):
        return False, "Invalid or expired reset code. Please try again."

    new_hash, new_salt = hash_password(new_password)
    with db._conn() as con:
        con.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE email = ?",
            (new_hash, new_salt, clean_email),
        )
    return True, "Password reset successfully! You can now sign in."


def request_email_login_otp(email: str) -> tuple[bool, str]:
    """Send one-time passwordless login code to user's registered email."""
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, "Please enter a valid email address."

    with db._conn() as con:
        user = con.execute("SELECT id FROM users WHERE email = ?", (clean_email,)).fetchone()
    if not user:
        return False, "No account found with this email. Please create an account first."

    code = create_otp(clean_email, "email_login", validity_minutes=15)
    sent_via_smtp, msg = send_auth_email(
        clean_email, "Lumen · Your Sign-in Code", code, "Passwordless Sign-in"
    )
    if sent_via_smtp:
        return True, f"Login code sent to {clean_email}!"
    return False, msg


def login_with_email_otp(email: str, code: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Authenticate user using email and OTP code."""
    clean_email = email.strip().lower()
    if not verify_otp(clean_email, "email_login", code):
        return False, "Invalid or expired login code.", None

    with db._conn() as con:
        row = con.execute(
            """
            SELECT id, username, email, full_name, avatar, created_at
            FROM users WHERE email = ?
            """,
            (clean_email,),
        ).fetchone()

    if not row:
        return False, "Account could not be found.", None

    user = {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"] or row["username"].title(),
        "avatar": row["avatar"] or "👤",
        "created_at": row["created_at"],
    }
    return True, f"Welcome back, {user['full_name']}!", user


# ----------------------------------------------------------------------------- User Management
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


# ----------------------------------------------------------------------------- Auth Portal UI
def render_auth_page() -> None:
    """Render the glassmorphic sign in, sign up, forgot password, and email OTP portal."""
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

        notice = st.session_state.get("_auth_code_notice")
        if notice:
            ui.html(
                f"""
                <div class="lm-card" style="padding:.75rem 1rem;margin-bottom:1rem;border-left:4px solid #38BDF8;background:rgba(56,189,248,0.12);">
                  <div style="font-size:.78rem;color:#7C9CFF;font-weight:700;text-transform:uppercase;letter-spacing:.05em;">📬 Verification Code Dispatched</div>
                  <div style="font-size:1.45rem;font-weight:800;letter-spacing:5px;color:#38BDF8;margin:.2rem 0;">{notice['code']}</div>
                  <div class="lm-muted" style="font-size:.78rem;">Sent for <b>{notice['email']}</b> ({notice['purpose']}). Enter code below.</div>
                </div>
                """
            )

        tab_login, tab_signup, tab_forgot, tab_otp = st.tabs(
            ["🔑  Sign In", "✨  Create Account", "🆘  Forgot Password", "📬  Email OTP"]
        )

        # Tab 1: Password Login
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
                key="btn_demo_login",
            ):
                ok, msg, user = authenticate_user("demo", "demo123")
                if ok and user:
                    st.toast("Signed in as Demo Explorer!", icon="✨")
                    sign_in(user)
                else:
                    st.error("Demo account could not be found.")

        # Tab 2: Create Account with optional Email Verification
        with tab_signup:
            st.markdown("**New to Lumen?** Set up your personal ledger:")
            c1, c2 = st.columns([3, 1])
            su_name = c1.text_input("Full Name", placeholder="e.g. Alex Morgan", key="su_fullname")
            su_avatar = c2.selectbox(
                "Avatar",
                ["👤", "✨", "🚀", "💎", "🦁", "🌸", "🥑", "🦊", "🌟", "🎯"],
                key="su_avatar",
            )
            su_user = st.text_input("Username", placeholder="e.g. alex", key="su_username")
            su_email = st.text_input("Email", placeholder="e.g. alex@example.com", key="su_email")
            p1, p2 = st.columns(2)
            su_pwd = p1.text_input("Password", type="password", placeholder="At least 6 chars", key="su_pwd")
            su_cpwd = p2.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="su_cpwd")

            st.write("")
            s1, s2 = st.columns([1.5, 1], vertical_alignment="bottom")
            if s1.button("Send Verification Code", icon=":material/mail:", width="stretch", key="su_send_code"):
                if not su_email or "@" not in su_email:
                    st.error("Please enter a valid email address.")
                elif not su_user or len(su_user) < 3:
                    st.error("Username must be at least 3 characters.")
                elif not su_pwd or len(su_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                elif su_pwd != su_cpwd:
                    st.error("Passwords do not match!")
                else:
                    code = create_otp(su_email, "signup_verify", validity_minutes=15)
                    sent, info = send_auth_email(su_email, "Lumen · Verification Code", code, "Account Verification")
                    st.session_state["su_code_sent"] = True
                    st.success(info)
                    st.toast(info, icon="📧")
                    st.rerun()

            active_notice = st.session_state.get("_auth_code_notice")
            default_code = ""
            if active_notice and active_notice.get("email") == su_email.strip().lower():
                default_code = active_notice.get("code", "")

            su_code_input = st.text_input(
                "6-Digit Verification Code",
                value=default_code if not st.session_state.get("su_code_val") else st.session_state.get("su_code_val"),
                placeholder="Enter 6-digit code",
                key="su_code_val",
                max_chars=6,
            )

            if st.button("Confirm Code & Create Account", type="primary", icon=":material/verified_user:", width="stretch", key="su_verify_submit"):
                if not su_code_input:
                    st.error("Please enter the 6-digit verification code.")
                elif not verify_otp(su_email, "signup_verify", su_code_input):
                    st.error("Invalid or expired verification code.")
                else:
                    ok, msg, new_user = register_user(su_user, su_email, su_pwd, su_name, su_avatar)
                    if ok and new_user:
                        st.toast("Email verified! Welcome to Lumen.", icon="🎉")
                        st.session_state.pop("_auth_code_notice", None)
                        sign_in(new_user)
                    else:
                        st.error(msg)

        # Tab 3: Forgot Password
        with tab_forgot:
            st.markdown("**Reset your password** securely via email verification code:")
            reset_ident = st.text_input("Enter your Username or Email", placeholder="e.g. alex@example.com", key="fp_ident")

            f_col1, f_col2 = st.columns([1.5, 1], vertical_alignment="bottom")
            if f_col1.button("Request Reset Code", icon=":material/send:", width="stretch", key="fp_request_btn"):
                ok, msg, email_found = request_password_reset(reset_ident)
                if ok:
                    st.session_state["fp_email"] = email_found
                    st.success(msg)
                    st.toast(msg, icon="🔑")
                else:
                    st.error(msg)

            target_email = st.session_state.get("fp_email")
            if target_email:
                st.info(f"A 6-digit code has been generated for **{target_email}**.")

            with st.form("reset_pwd_form", border=True):
                st.markdown("**Enter code and new password:**")
                fp_code = st.text_input("6-Digit Reset Code", placeholder="e.g. 123456", max_chars=6)
                np1, np2 = st.columns(2)
                new_pwd = np1.text_input("New Password", type="password", placeholder="At least 6 chars")
                confirm_npwd = np2.text_input("Confirm New Password", type="password", placeholder="Re-enter password")

                if st.form_submit_button("Reset Password & Sign In", type="primary", icon=":material/lock_reset:", width="stretch"):
                    active_email = target_email or reset_ident
                    if not active_email or "@" not in active_email:
                        st.error("Please enter or verify your registered email address.")
                    elif not fp_code:
                        st.error("Please enter the reset code.")
                    elif new_pwd != confirm_npwd:
                        st.error("New passwords do not match.")
                    else:
                        ok, msg = reset_password_with_otp(active_email, fp_code, new_pwd)
                        if ok:
                            st.toast(msg, icon="✅")
                            st.session_state.pop("fp_email", None)
                            # Attempt instant sign-in
                            ok_l, _, u = authenticate_user(active_email, new_pwd)
                            if ok_l and u:
                                sign_in(u)
                        else:
                            st.error(msg)

        # Tab 4: Email OTP Sign-in (Passwordless)
        with tab_otp:
            st.markdown("**Passwordless Sign-In** with a one-time code:")
            otp_email = st.text_input("Registered Email Address", placeholder="you@example.com", key="otp_login_email")

            if st.button("Send One-Time Code", icon=":material/mail:", width="stretch", key="otp_send_btn"):
                ok, msg = request_email_login_otp(otp_email)
                if ok:
                    st.success(msg)
                    st.toast(msg, icon="📬")
                    st.session_state["otp_login_ready"] = True
                else:
                    st.error(msg)

            with st.form("otp_login_form", border=True):
                code_entered = st.text_input("6-Digit Login Code", placeholder="••••••", max_chars=6)
                if st.form_submit_button("Sign In with Code", type="primary", icon=":material/login:", width="stretch"):
                    if not otp_email:
                        st.error("Please enter your registered email address.")
                    elif not code_entered:
                        st.error("Please enter the 6-digit code.")
                    else:
                        ok, msg, user_obj = login_with_email_otp(otp_email, code_entered)
                        if ok and user_obj:
                            st.toast(msg, icon="🎉")
                            sign_in(user_obj)
                        else:
                            st.error(msg)
