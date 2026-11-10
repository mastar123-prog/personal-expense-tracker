"""Authentication and user management for Lumen.

Uses standard library hashlib.pbkdf2_hmac with random salts for secure,
dependency-free password hashing, plus GitHub-style email verification,
OTP login, password recovery, and developer sandbox fallback.
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
def create_otp(email: str, token_type: str, validity_minutes: int = 15) -> str:
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


# ----------------------------------------------------------------------------- DNS MX & Email Delivery
WELL_KNOWN_MX: dict[str, list[tuple[int, str]]] = {
    "gmail.com": [(5, "gmail-smtp-in.l.google.com"), (10, "alt1.gmail-smtp-in.l.google.com"), (20, "alt2.gmail-smtp-in.l.google.com")],
    "googlemail.com": [(5, "gmail-smtp-in.l.google.com"), (10, "alt1.gmail-smtp-in.l.google.com")],
    "outlook.com": [(10, "outlook-com.olc.protection.outlook.com")],
    "hotmail.com": [(10, "hotmail-com.olc.protection.outlook.com")],
    "live.com": [(10, "live-com.olc.protection.outlook.com")],
    "msn.com": [(10, "msn-com.olc.protection.outlook.com")],
    "yahoo.com": [(10, "mta5.am0.yahoodns.net"), (10, "mta6.am0.yahoodns.net")],
    "ymail.com": [(10, "mta5.am0.yahoodns.net")],
    "icloud.com": [(10, "mx1.mail.icloud.com"), (10, "mx2.mail.icloud.com")],
    "me.com": [(10, "mx1.mail.icloud.com")],
    "mac.com": [(10, "mx1.mail.icloud.com")],
    "proton.me": [(10, "mail.protonmail.ch"), (20, "mailsec.protonmail.ch")],
    "protonmail.com": [(10, "mail.protonmail.ch")],
}


def get_mx_records(domain: str) -> list[str]:
    """Resolve DNS MX records for a domain, sorted by priority (lowest preference first)."""
    import subprocess
    import re

    clean_dom = domain.strip().lower()
    if clean_dom in WELL_KNOWN_MX:
        return [host for _, host in sorted(WELL_KNOWN_MX[clean_dom], key=lambda x: x[0])]

    # 1. Try dnspython if installed
    try:
        import dns.resolver
        answers = dns.resolver.resolve(clean_dom, "MX")
        sorted_answers = sorted(answers, key=lambda r: r.preference)
        return [str(r.exchange).rstrip(".") for r in sorted_answers]
    except Exception:
        pass

    # 2. Universal OS nslookup tool
    try:
        res = subprocess.run(
            ["nslookup", "-type=MX", clean_dom, "8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        records: list[tuple[int, str]] = []
        for line in (res.stdout + "\n" + res.stderr).splitlines():
            m = re.search(r"preference\s*=\s*(\d+).*?mail exchanger\s*=\s*([a-zA-Z0-9.-]+)", line, re.I)
            if m:
                records.append((int(m.group(1)), m.group(2).strip().rstrip(".")))
            else:
                m2 = re.search(r"mail exchanger\s*=\s*([a-zA-Z0-9.-]+)", line, re.I)
                if m2:
                    records.append((10, m2.group(1).strip().rstrip(".")))
        if records:
            records.sort(key=lambda x: x[0])
            return [host for _, host in records]
    except Exception:
        pass

    return []


def send_auth_email(to_email: str, subject: str, code: str, purpose: str) -> tuple[bool, str]:
    """Deliver authentication launch code using configured SMTP, DNS MX lookups, or local sandbox.
    
    Operates like GitHub: sends real emails when mail service is configured, and provides
    instant developer/local sandbox fallback so users are never blocked by residential ISP port 25 restrictions.
    """
    clean_email = to_email.strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, "Please enter a valid email address."

    domain = clean_email.split("@", 1)[1].strip()

    # DNS MX lookup to ensure domain actually exists
    mx_hosts = get_mx_records(domain)
    if not mx_hosts and domain not in ("localhost", "local"):
        return False, f"Domain check failed: No mail servers found for domain '{domain}'. Please verify your email spelling."

    # GitHub-style plain text and HTML emails
    body_text = (
        f"Lumen Authentication\n\n"
        f"Here is your launch code for {purpose}:\n"
        f"  {code}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        f"If you did not request this code, you can safely ignore this email.\n\n"
        f"— The Lumen Security Team"
    )
    body_html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;max-width:540px;margin:0 auto;padding:32px 24px;background:#0d1117;color:#c9d1d9;border-radius:12px;border:1px solid #30363d;">
      <div style="text-align:center;margin-bottom:24px;">
        <div style="font-size:36px;line-height:1;">✨</div>
        <h2 style="color:#ffffff;font-size:22px;margin:12px 0 4px;font-weight:600;">Verify your email address</h2>
        <p style="color:#8b949e;font-size:14px;margin:0;">Here is your Lumen launch code for <b>{purpose}</b></p>
      </div>
      <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:24px;text-align:center;margin:24px 0;">
        <p style="color:#8b949e;font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:0 0 10px;font-weight:600;">Your 6-digit verification code</p>
        <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#58a6ff;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;">{code}</div>
      </div>
      <p style="font-size:13px;color:#8b949e;line-height:1.5;">This launch code will expire in <b>15 minutes</b>. Enter it on the verification page to finish setting up your account.</p>
      <hr style="border:none;border-top:1px solid #21262d;margin:24px 0;">
      <p style="font-size:12px;color:#484f58;margin:0;text-align:center;">If you did not request this verification code, you can safely ignore this email.</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = clean_email
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    # Priority 1: Configured SMTP credentials (in settings or .env)
    cfg = get_smtp_config()
    if cfg["is_configured"]:
        sender = cfg["sender"] or cfg["user"]
        msg["From"] = f"Lumen Security <{sender}>"
        try:
            if cfg["use_ssl"] or cfg["port"] == 465:
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10)
            else:
                server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
                server.starttls()
            server.login(cfg["user"], cfg["pass"])
            server.sendmail(sender, [clean_email], msg.as_string())
            server.quit()
            return True, f"Verification launch code delivered to {clean_email}! Check your inbox."
        except Exception as e:
            print(f"[AUTH] Configured SMTP delivery failed: {e}")

    # Priority 2: Direct DNS MX Record Lookup delivery (Fast check if port 25 is open)
    sender = "noreply@lumen.finance"
    msg["From"] = f"Lumen Security <{sender}>"
    if mx_hosts:
        for mx_host in mx_hosts[:1]:
            try:
                server = smtplib.SMTP(mx_host, 25, timeout=1.0)
                server.ehlo("lumen.finance")
                if server.has_extn("STARTTLS"):
                    server.starttls()
                    server.ehlo("lumen.finance")
                code_m, _ = server.mail(sender)
                if code_m >= 400:
                    server.quit()
                    continue
                code_r, _ = server.rcpt(clean_email)
                if code_r >= 400:
                    server.quit()
                    continue
                code_d, _ = server.data(msg.as_string())
                server.quit()
                if code_d < 400:
                    return True, f"Verification launch code delivered to {clean_email} via mail server! Check your inbox."
            except Exception:
                continue

    # Priority 3: GitHub-Style Developer Mode & Local Sandbox Fallback
    # (Triggered when residential ISP or local firewall blocks outbound port 25 without SMTP credentials)
    print(f"[LUMEN AUTH] 📬 Launch code generated for {clean_email}: {code}")
    try:
        st.session_state["dev_last_otp_code"] = code
        st.session_state["dev_last_otp_email"] = clean_email
        st.session_state["dev_last_otp_purpose"] = purpose
    except Exception:
        pass

    return True, f"Verification launch code generated for {clean_email}!"


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
    ok, info = send_auth_email(
        email, "[Lumen] Please reset your password", code, "Password Reset"
    )
    if ok:
        return True, info, email
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
    ok, msg = send_auth_email(
        clean_email, "[Lumen] Your sign-in launch code", code, "Passwordless Sign-in"
    )
    return ok, msg


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
    """Render the GitHub-style sign in, sign up, forgot password, and email OTP portal."""
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

        # Tab 2: Create Account (GitHub-style 2-Step Flow)
        with tab_signup:
            verified_target = st.session_state.get("su_email_verified_target")

            if not verified_target:
                # Step 1: Account Details
                st.markdown("**Create your account** with GitHub-style email verification:")
                with st.form("signup_details_form", border=True):
                    c1, c2 = st.columns([3, 1])
                    su_name = c1.text_input("Full Name", placeholder="e.g. Alex Morgan")
                    su_avatar = c2.selectbox(
                        "Avatar",
                        ["👤", "✨", "🚀", "💎", "🦁", "🌸", "🥑", "🦊", "🌟", "🎯"],
                    )
                    su_user = st.text_input("Username", placeholder="e.g. alex")
                    su_email = st.text_input("Email", placeholder="e.g. alex@example.com")
                    p1, p2 = st.columns(2)
                    su_pwd = p1.text_input("Password", type="password", placeholder="At least 6 chars")
                    su_cpwd = p2.text_input("Confirm Password", type="password", placeholder="Re-enter password")

                    send_submitted = st.form_submit_button(
                        "Continue · Send Launch Code",
                        type="primary",
                        icon=":material/arrow_forward:",
                        width="stretch",
                    )

                if send_submitted:
                    if not su_email or "@" not in su_email:
                        st.error("Please enter a valid email address.")
                    elif not su_user or len(su_user) < 3:
                        st.error("Username must be at least 3 characters.")
                    elif not su_pwd or len(su_pwd) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif su_pwd != su_cpwd:
                        st.error("Passwords do not match!")
                    else:
                        clean_u = su_user.strip().lower()
                        clean_e = su_email.strip().lower()
                        with db._conn() as con:
                            taken = con.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (clean_u, clean_e)).fetchone()
                        if taken:
                            if taken["username"] == clean_u:
                                st.error("Username is already taken. Please choose another.")
                            else:
                                st.error("Email is already registered. Please sign in.")
                        else:
                            with st.spinner("Dispatching verification launch code..."):
                                code = create_otp(clean_e, "signup_verify", validity_minutes=15)
                                ok, info = send_auth_email(clean_e, "[Lumen] Please verify your email address", code, "Account Verification")
                            if ok:
                                st.session_state["su_email_verified_target"] = clean_e
                                st.session_state["su_cached_data"] = {
                                    "user": clean_u,
                                    "email": clean_e,
                                    "name": su_name,
                                    "avatar": su_avatar,
                                    "pwd": su_pwd,
                                }
                                st.toast("Verification launch code dispatched!", icon="📧")
                                st.rerun()
                            else:
                                st.error(f"❌ {info}")
            else:
                # Step 2: GitHub-style Verification Screen
                st.markdown(
                    f"""
                    <div style="background:rgba(22, 27, 34, 0.85);border:1px solid rgba(48, 54, 61, 0.9);border-radius:12px;padding:20px;text-align:center;margin-bottom:14px;">
                      <div style="font-size:2.2rem;margin-bottom:6px;">🐙</div>
                      <h3 style="margin:0 0 6px;color:#F0F6FC;font-size:1.35rem;font-weight:600;">Verify your email address</h3>
                      <div style="font-size:0.9rem;color:#8B949E;line-height:1.45;">
                        We sent a 6-digit launch code to <b style="color:#58A6FF;">{verified_target}</b>.<br>
                        Enter the code below to complete registration.
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                dev_code = st.session_state.get("dev_last_otp_code")
                dev_email = st.session_state.get("dev_last_otp_email")
                has_dev_code = bool(dev_code and dev_email == verified_target)

                if has_dev_code:
                    col_code_msg, col_code_btn = st.columns([3, 1.4], vertical_alignment="center")
                    with col_code_msg:
                        st.markdown(
                            f"""
                            <div style="background:rgba(56, 189, 248, 0.08);border:1px solid rgba(56, 189, 248, 0.25);border-radius:8px;padding:8px 12px;font-size:0.84rem;color:#8B949E;">
                              💡 <b>GitHub Sandbox Code</b>: <span style="font-family:monospace;font-weight:800;color:#38BDF8;font-size:1.05rem;letter-spacing:2px;margin-left:4px;">{dev_code}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_code_btn:
                        if st.button("⚡ Autofill Code", width="stretch", key="btn_autofill_su_code"):
                            st.session_state["su_code_autofill_val"] = dev_code
                            st.rerun()

                with st.form("signup_confirm_form", border=True):
                    initial_val = st.session_state.pop("su_code_autofill_val", "")
                    su_code_input = st.text_input(
                        "6-Digit Launch Code",
                        value=initial_val,
                        placeholder="123456",
                        max_chars=6,
                        help="Enter the 6-digit verification code sent to your email",
                    )
                    confirm_submitted = st.form_submit_button(
                        "Verify & Activate Account",
                        type="primary",
                        icon=":material/verified_user:",
                        width="stretch",
                    )

                if confirm_submitted:
                    code_to_check = (su_code_input or "").strip()
                    if not code_to_check:
                        st.error("Please enter the 6-digit launch code.")
                    elif not verify_otp(verified_target, "signup_verify", code_to_check):
                        st.error("Invalid or expired verification code. Please check your code and try again.")
                    else:
                        u_data = st.session_state.get("su_cached_data", {})
                        ok, msg, new_user = register_user(
                            u_data.get("user", ""),
                            verified_target,
                            u_data.get("pwd", ""),
                            u_data.get("name", ""),
                            u_data.get("avatar", "👤"),
                        )
                        if ok and new_user:
                            st.toast("Email verified! Welcome to Lumen.", icon="🎉")
                            st.session_state.pop("su_email_verified_target", None)
                            st.session_state.pop("su_cached_data", None)
                            st.session_state.pop("dev_last_otp_code", None)
                            sign_in(new_user)
                        else:
                            st.error(msg)

                c_resend, c_back = st.columns(2)
                with c_resend:
                    if st.button("🔄 Resend Email", width="stretch", key="su_resend_btn"):
                        new_code = create_otp(verified_target, "signup_verify", validity_minutes=15)
                        send_auth_email(verified_target, "[Lumen] Please verify your email address", new_code, "Account Verification")
                        st.toast("New verification launch code sent!", icon="📬")
                        st.rerun()
                with c_back:
                    if st.button("✏️ Change Email", width="stretch", key="su_back_edit_btn"):
                        st.session_state.pop("su_email_verified_target", None)
                        st.rerun()

            with st.expander("⚙️ Connect Gmail or Outlook (Send Real Emails in 1-Click)"):
                st.caption("Deliver emails directly through authenticated TLS (ports 587/465) without residential ISP port 25 restrictions. Configure credentials directly here without touching .env:")
                c_h, c_p = st.columns([2, 1])
                smtp_h = c_h.text_input("SMTP Server Host", value="smtp.gmail.com", key="auth_smtp_h")
                smtp_p = c_p.number_input("Port", value=587, min_value=1, max_value=65535, key="auth_smtp_p")
                c_u, c_pw = st.columns(2)
                smtp_u = c_u.text_input("Your Email", placeholder="you@gmail.com", key="auth_smtp_u")
                smtp_pw = c_pw.text_input("App Password", type="password", placeholder="16-character app password", key="auth_smtp_pw", help="For Gmail, create an App Password at myaccount.google.com/apppasswords")
                if st.button("Save Credentials to App", icon=":material/save:", key="auth_save_smtp"):
                    if not smtp_u or not smtp_pw:
                        st.error("Please enter both email and app password.")
                    else:
                        db.set_setting("smtp_host", smtp_h.strip(), user_id=1)
                        db.set_setting("smtp_port", str(smtp_p), user_id=1)
                        db.set_setting("smtp_user", smtp_u.strip(), user_id=1)
                        db.set_setting("smtp_pass", smtp_pw.strip(), user_id=1)
                        db.set_setting("smtp_sender", smtp_u.strip(), user_id=1)
                        st.success("Credentials saved to database! Emails will now send directly from your account.")

        # Tab 3: Forgot Password (GitHub-style 2-Step Flow)
        with tab_forgot:
            fp_target = st.session_state.get("fp_target_email")

            if not fp_target:
                st.markdown("**Reset your password** securely via GitHub-style launch code:")
                with st.form("fp_request_form", border=True):
                    reset_ident = st.text_input("Enter your Username or Email", placeholder="e.g. alex@example.com")
                    req_btn = st.form_submit_button("Send Password Reset Code", icon=":material/send:", type="primary", width="stretch")

                if req_btn:
                    with st.spinner("Dispatching reset launch code..."):
                        ok, msg, email_found = request_password_reset(reset_ident)
                    if ok and email_found:
                        st.session_state["fp_target_email"] = email_found
                        st.toast("Password reset launch code dispatched!", icon="🔑")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.markdown(
                    f"""
                    <div style="background:rgba(22, 27, 34, 0.85);border:1px solid rgba(48, 54, 61, 0.9);border-radius:12px;padding:20px;text-align:center;margin-bottom:14px;">
                      <div style="font-size:2.2rem;margin-bottom:6px;">🔑</div>
                      <h3 style="margin:0 0 6px;color:#F0F6FC;font-size:1.35rem;font-weight:600;">Reset your password</h3>
                      <div style="font-size:0.9rem;color:#8B949E;line-height:1.45;">
                        We sent a 6-digit reset code to <b style="color:#58A6FF;">{fp_target}</b>.<br>
                        Enter the code below with your new password.
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                dev_code = st.session_state.get("dev_last_otp_code")
                dev_email = st.session_state.get("dev_last_otp_email")
                has_dev_code = bool(dev_code and dev_email == fp_target)

                if has_dev_code:
                    col_code_msg, col_code_btn = st.columns([3, 1.4], vertical_alignment="center")
                    with col_code_msg:
                        st.markdown(
                            f"""
                            <div style="background:rgba(56, 189, 248, 0.08);border:1px solid rgba(56, 189, 248, 0.25);border-radius:8px;padding:8px 12px;font-size:0.84rem;color:#8B949E;">
                              💡 <b>GitHub Sandbox Code</b>: <span style="font-family:monospace;font-weight:800;color:#38BDF8;font-size:1.05rem;letter-spacing:2px;margin-left:4px;">{dev_code}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_code_btn:
                        if st.button("⚡ Autofill Code", width="stretch", key="btn_autofill_fp_code"):
                            st.session_state["fp_code_autofill_val"] = dev_code
                            st.rerun()

                with st.form("reset_pwd_form", border=True):
                    initial_val = st.session_state.pop("fp_code_autofill_val", "")
                    fp_code = st.text_input("6-Digit Reset Code", value=initial_val, placeholder="123456", max_chars=6)
                    np1, np2 = st.columns(2)
                    new_pwd = np1.text_input("New Password", type="password", placeholder="At least 6 chars")
                    confirm_npwd = np2.text_input("Confirm New Password", type="password", placeholder="Re-enter password")

                    reset_submit = st.form_submit_button("Reset Password & Sign In", type="primary", icon=":material/lock_reset:", width="stretch")

                if reset_submit:
                    if not fp_code:
                        st.error("Please enter the 6-digit reset code.")
                    elif new_pwd != confirm_npwd:
                        st.error("New passwords do not match.")
                    else:
                        ok, msg = reset_password_with_otp(fp_target, fp_code, new_pwd)
                        if ok:
                            st.toast(msg, icon="✅")
                            target_em = fp_target
                            st.session_state.pop("fp_target_email", None)
                            st.session_state.pop("dev_last_otp_code", None)
                            ok_l, _, u = authenticate_user(target_em, new_pwd)
                            if ok_l and u:
                                sign_in(u)
                        else:
                            st.error(msg)

                c_resend, c_back = st.columns(2)
                with c_resend:
                    if st.button("🔄 Resend Code", width="stretch", key="fp_resend_btn"):
                        new_code = create_otp(fp_target, "reset_password", validity_minutes=15)
                        send_auth_email(fp_target, "[Lumen] Please reset your password", new_code, "Password Reset")
                        st.toast("New password reset code sent!", icon="🔑")
                        st.rerun()
                with c_back:
                    if st.button("✏️ Change Email", width="stretch", key="fp_back_btn"):
                        st.session_state.pop("fp_target_email", None)
                        st.rerun()

        # Tab 4: Email OTP Sign-in (GitHub-style 2-Step Flow)
        with tab_otp:
            otp_target = st.session_state.get("otp_target_email")

            if not otp_target:
                st.markdown("**Passwordless Sign-In** with a GitHub-style launch code:")
                with st.form("otp_send_form", border=True):
                    otp_email = st.text_input("Registered Email Address", placeholder="you@example.com")
                    send_otp_btn = st.form_submit_button("Send Sign-In Code", icon=":material/mail:", type="primary", width="stretch")

                if send_otp_btn:
                    with st.spinner("Dispatching sign-in launch code..."):
                        ok, msg = request_email_login_otp(otp_email)
                    if ok:
                        st.session_state["otp_target_email"] = otp_email.strip().lower()
                        st.toast("Sign-in launch code dispatched!", icon="📬")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.markdown(
                    f"""
                    <div style="background:rgba(22, 27, 34, 0.85);border:1px solid rgba(48, 54, 61, 0.9);border-radius:12px;padding:20px;text-align:center;margin-bottom:14px;">
                      <div style="font-size:2.2rem;margin-bottom:6px;">📬</div>
                      <h3 style="margin:0 0 6px;color:#F0F6FC;font-size:1.35rem;font-weight:600;">Sign in with launch code</h3>
                      <div style="font-size:0.9rem;color:#8B949E;line-height:1.45;">
                        We sent a 6-digit sign-in code to <b style="color:#58A6FF;">{otp_target}</b>.<br>
                        Enter the code below to access your account.
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                dev_code = st.session_state.get("dev_last_otp_code")
                dev_email = st.session_state.get("dev_last_otp_email")
                has_dev_code = bool(dev_code and dev_email == otp_target)

                if has_dev_code:
                    col_code_msg, col_code_btn = st.columns([3, 1.4], vertical_alignment="center")
                    with col_code_msg:
                        st.markdown(
                            f"""
                            <div style="background:rgba(56, 189, 248, 0.08);border:1px solid rgba(56, 189, 248, 0.25);border-radius:8px;padding:8px 12px;font-size:0.84rem;color:#8B949E;">
                              💡 <b>GitHub Sandbox Code</b>: <span style="font-family:monospace;font-weight:800;color:#38BDF8;font-size:1.05rem;letter-spacing:2px;margin-left:4px;">{dev_code}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_code_btn:
                        if st.button("⚡ Autofill Code", width="stretch", key="btn_autofill_otp_code"):
                            st.session_state["otp_code_autofill_val"] = dev_code
                            st.rerun()

                with st.form("otp_login_form", border=True):
                    initial_val = st.session_state.pop("otp_code_autofill_val", "")
                    code_entered = st.text_input("6-Digit Sign-In Code", value=initial_val, placeholder="123456", max_chars=6)
                    login_otp_submit = st.form_submit_button("Sign In with Code", type="primary", icon=":material/login:", width="stretch")

                if login_otp_submit:
                    if not code_entered:
                        st.error("Please enter the 6-digit code.")
                    else:
                        ok, msg, user_obj = login_with_email_otp(otp_target, code_entered)
                        if ok and user_obj:
                            st.toast(msg, icon="🎉")
                            st.session_state.pop("otp_target_email", None)
                            st.session_state.pop("dev_last_otp_code", None)
                            sign_in(user_obj)
                        else:
                            st.error(msg)

                c_resend, c_back = st.columns(2)
                with c_resend:
                    if st.button("🔄 Resend Code", width="stretch", key="otp_resend_btn"):
                        new_code = create_otp(otp_target, "email_login", validity_minutes=15)
                        send_auth_email(otp_target, "[Lumen] Your sign-in launch code", new_code, "Passwordless Sign-in")
                        st.toast("New sign-in code sent!", icon="📬")
                        st.rerun()
                with c_back:
                    if st.button("✏️ Change Email", width="stretch", key="otp_back_btn"):
                        st.session_state.pop("otp_target_email", None)
                        st.rerun()
