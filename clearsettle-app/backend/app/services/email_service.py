"""
app/services/email_service.py — Transactional email via SMTP or SendGrid.

Priority: SendGrid (if api key set) → SMTP → log-only (dev fallback).
All methods are fire-and-forget from the router's perspective; errors are
logged but never propagate to the user (to avoid leaking whether an email
address exists).
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ── HTML email templates ──────────────────────────────────────────────────────

def _base_template(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 2px 12px rgba(13,31,53,.08);">
        <tr>
          <td style="background:#0D1F35;padding:28px 40px;">
            <span style="color:#fff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">
              ClearSettle
            </span>
          </td>
        </tr>
        <tr><td style="padding:40px 40px 32px;">{body_html}</td></tr>
        <tr>
          <td style="background:#F1F5F9;padding:20px 40px;
                     font-size:11px;color:#8FA5BD;text-align:center;">
            © 2026 ClearSettle Fintech Pvt Ltd &nbsp;·&nbsp;
            <a href="https://clearsettle.in/privacy" style="color:#8FA5BD;">Privacy Policy</a>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _btn(url: str, label: str, color: str = "#0ABFCA") -> str:
    return (f'<a href="{url}" style="display:inline-block;padding:14px 28px;'
            f'background:{color};color:#fff;border-radius:8px;font-weight:700;'
            f'font-size:14px;text-decoration:none;">{label}</a>')


def password_reset_html(name: str, reset_url: str, expires_minutes: int) -> tuple[str, str]:
    subject = "Reset your ClearSettle password"
    body = f"""
<h2 style="margin:0 0 8px;color:#0D1F35;font-size:20px;">Reset your password</h2>
<p style="color:#4B6080;font-size:14px;line-height:1.6;margin:0 0 24px;">
  Hi {name or 'there'},<br><br>
  We received a request to reset the password for your ClearSettle account.
  Click the button below — this link expires in <strong>{expires_minutes} minutes</strong>.
</p>
{_btn(reset_url, 'Reset Password')}
<p style="color:#8FA5BD;font-size:12px;margin:24px 0 0;line-height:1.6;">
  If you didn't request this, you can safely ignore this email.
  Your password will not be changed until you click the link above.
</p>"""
    return subject, _base_template(subject, body)


def email_verification_html(name: str, verify_url: str, expires_hours: int) -> tuple[str, str]:
    subject = "Verify your ClearSettle email"
    body = f"""
<h2 style="margin:0 0 8px;color:#0D1F35;font-size:20px;">Verify your email address</h2>
<p style="color:#4B6080;font-size:14px;line-height:1.6;margin:0 0 24px;">
  Hi {name or 'there'},<br><br>
  Welcome to ClearSettle! Click the button below to verify your email address.
  The link expires in <strong>{expires_hours} hours</strong>.
</p>
{_btn(verify_url, 'Verify Email', '#0DB07A')}
<p style="color:#8FA5BD;font-size:12px;margin:24px 0 0;line-height:1.6;">
  If you didn't create a ClearSettle account, please ignore this email.
</p>"""
    return subject, _base_template(subject, body)


def invitation_html(inviter_name: str, company_name: str,
                    invite_url: str, role: str, expires_days: int) -> tuple[str, str]:
    subject = f"You've been invited to join {company_name} on ClearSettle"
    body = f"""
<h2 style="margin:0 0 8px;color:#0D1F35;font-size:20px;">You're invited!</h2>
<p style="color:#4B6080;font-size:14px;line-height:1.6;margin:0 0 24px;">
  <strong>{inviter_name}</strong> has invited you to join
  <strong>{company_name}</strong> on ClearSettle as a <strong>{role}</strong>.
  Click the button below to accept — this invitation expires in {expires_days} days.
</p>
{_btn(invite_url, 'Accept Invitation')}
<p style="color:#8FA5BD;font-size:12px;margin:24px 0 0;line-height:1.6;">
  If you weren't expecting this invitation, you can safely ignore it.
</p>"""
    return subject, _base_template(subject, body)


# ── Delivery backends ─────────────────────────────────────────────────────────

def _send_via_sendgrid(to_email: str, subject: str, html: str, settings) -> bool:
    try:
        import httpx
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.smtp_from_email, "name": settings.smtp_from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        }
        resp = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            timeout=10,
        )
        if resp.status_code not in (200, 202):
            logger.error("SendGrid error %s: %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as exc:
        logger.error("SendGrid exception: %s", exc)
        return False


def _send_via_smtp(to_email: str, subject: str, html: str, settings) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html", "utf-8"))

        cls = smtplib.SMTP_SSL if not settings.smtp_tls else smtplib.SMTP
        with cls(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_tls:
                server.ehlo()
                server.starttls()
                server.ehlo()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.error("SMTP exception: %s", exc)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, html: str) -> None:
    """
    Best-effort send.  Tries SendGrid first, falls back to SMTP, then logs only.
    Never raises — callers must not depend on delivery confirmation.
    """
    settings = get_settings()

    if settings.sendgrid_api_key:
        if _send_via_sendgrid(to_email, subject, html, settings):
            logger.info("Email sent via SendGrid to %s: %s", to_email, subject)
            return

    if settings.smtp_host:
        if _send_via_smtp(to_email, subject, html, settings):
            logger.info("Email sent via SMTP to %s: %s", to_email, subject)
            return

    # Development fallback — log the link so developers can test without SMTP
    logger.warning(
        "EMAIL (no transport configured) → to=%s subject=%s\n%s",
        to_email, subject, html[:500],
    )


def send_password_reset(to_email: str, name: str, token: str) -> None:
    settings = get_settings()
    url = f"{settings.frontend_url}/reset-password?token={token}"
    subject, html = password_reset_html(name, url, settings.password_reset_expire_minutes)
    send_email(to_email, subject, html)


def send_email_verification(to_email: str, name: str, token: str) -> None:
    settings = get_settings()
    url = f"{settings.frontend_url}/verify-email?token={token}"
    subject, html = email_verification_html(name, url, settings.email_verification_expire_hours)
    send_email(to_email, subject, html)


def send_invitation(to_email: str, inviter_name: str,
                    company_name: str, token: str, role: str) -> None:
    settings = get_settings()
    url = f"{settings.frontend_url}/accept-invite?token={token}"
    subject, html = invitation_html(inviter_name, company_name, url, role,
                                    settings.invitation_expire_days)
    send_email(to_email, subject, html)
