"""Email delivery service using Resend SDK."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Shared styles ──────────────────────────────────────────────────────

_BODY_STYLE = (
    "font-family: -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, sans-serif; "
    "max-width: 600px; margin: 0 auto; "
    "padding: 40px 20px; color: #1f2937;"
)
_CARD_STYLE = (
    "background: #f9fafb; border: 1px solid #e5e7eb; "
    "border-radius: 12px; padding: 32px; text-align: center;"
)
_BTN_STYLE = (
    "display: inline-block; margin-top: 24px; "
    "padding: 12px 32px; "
    "background: linear-gradient(to right, #7c3aed, #4f46e5); "
    "color: white; text-decoration: none; "
    "border-radius: 8px; font-weight: 500;"
)


def _build_email_html(title: str, content_html: str) -> str:
    """Build a complete HTML email with shared header/footer.

    Args:
        title: Card heading text.
        content_html: Inner HTML for the card body.

    Returns:
        Full HTML document string.
    """
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="{_BODY_STYLE}">
  <div style="text-align: center; margin-bottom: 32px;">
    <h1 style="color: #7c3aed; font-size: 24px; margin: 0;">
      Saldora
    </h1>
  </div>

  <div style="{_CARD_STYLE}">
    <h2 style="font-size: 20px; margin: 0 0 16px 0;">
      {title}
    </h2>
    {content_html}
  </div>

  <p style="text-align: center; color: #9ca3af; font-size: 12px; margin-top: 32px;">
    Ako niste očekivali ovaj email, možete ga ignorisati.
  </p>
</body>
</html>"""


async def _send_email(to_email: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Skips silently if API key is not set.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html: HTML body content.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email to %s", to_email)
        return False

    import resend

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s: %s", to_email, subject)
        return False


# ── Public email functions ─────────────────────────────────────────────


async def send_invitation_email(
    to_email: str,
    organization_name: str,
    role: str,
    accept_url: str,
    inviter_name: str | None = None,
) -> bool:
    """Send an invitation email to join an organization.

    Args:
        to_email: Recipient email address.
        organization_name: Name of the inviting organization.
        role: Offered role in the organization.
        accept_url: URL to accept the invitation.
        inviter_name: Name of the person who sent the invite.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    inviter_line = (
        f"<p>{inviter_name} vas poziva da se pridružite organizaciji "
        f"<strong>{organization_name}</strong> kao "
        f"<strong>{role}</strong>.</p>"
        if inviter_name
        else f"<p>Pozvani ste da se pridružite organizaciji "
        f"<strong>{organization_name}</strong> kao "
        f"<strong>{role}</strong>.</p>"
    )

    content = f"""{inviter_line}
    <p style="color: #6b7280; font-size: 14px;">
      Pozivnica ističe za 7 dana.
    </p>
    <a href="{accept_url}" style="{_BTN_STYLE}">
      Prihvatite poziv
    </a>"""

    html = _build_email_html("Poziv za pridruživanje", content)
    subject = f"Poziv za {organization_name} — Saldora"
    return await _send_email(to_email, subject, html)


async def send_welcome_email(to_email: str, first_name: str | None) -> bool:
    """Send a welcome email after registration.

    Args:
        to_email: Recipient email address.
        first_name: User's first name (for personalised greeting).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    greeting = first_name or "korisniče"

    content = f"""<p>Zdravo, <strong>{greeting}</strong>!</p>
    <p style="color: #6b7280; font-size: 14px;">
      Vaš nalog na Saldora je uspešno kreiran.
      Sada možete da kreirate organizaciju ili se
      pridružite postojećoj.
    </p>
    <a href="{settings.frontend_url}/login" style="{_BTN_STYLE}">
      Prijavite se
    </a>"""

    html = _build_email_html("Dobrodošli na Saldora", content)
    return await _send_email(to_email, "Dobrodošli na Saldora", html)


async def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send a password reset email with a one-time link.

    Args:
        to_email: Recipient email address.
        reset_url: URL to reset the password (contains JWT token).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    content = f"""<p>Zatražili ste resetovanje lozinke za vaš
    Saldora nalog.</p>
    <p style="color: #6b7280; font-size: 14px;">
      Kliknite na dugme ispod da biste postavili novu lozinku.
      Link je važeći <strong>1 sat</strong>.
    </p>
    <a href="{reset_url}" style="{_BTN_STYLE}">
      Resetujte lozinku
    </a>
    <p style="color: #9ca3af; font-size: 13px; margin-top: 24px;">
      Ako niste zatražili resetovanje lozinke, ignorišite ovaj email.
    </p>"""

    html = _build_email_html("Resetovanje lozinke", content)
    return await _send_email(to_email, "Resetovanje lozinke — Saldora", html)


async def send_invoice_processed_email(
    to_email: str,
    first_name: str | None,
    invoice_number: str,
    invoice_id: str,
) -> bool:
    """Send a notification that an invoice has been verified.

    Args:
        to_email: Recipient email address.
        first_name: User's first name.
        invoice_number: Display number of the invoice.
        invoice_id: UUID of the invoice (for the detail link).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    greeting = first_name or "korisniče"
    detail_url = f"{settings.frontend_url}/invoices/{invoice_id}"

    content = f"""<p>Zdravo, <strong>{greeting}</strong>!</p>
    <p style="color: #6b7280; font-size: 14px;">
      Faktura <strong>{invoice_number}</strong> je uspešno
      obrađena i čeka vaš pregled.
    </p>
    <a href="{detail_url}" style="{_BTN_STYLE}">
      Pregledajte fakturu
    </a>"""

    html = _build_email_html("Faktura obrađena", content)
    subject = f"Faktura {invoice_number} je obrađena — Saldora"
    return await _send_email(to_email, subject, html)
