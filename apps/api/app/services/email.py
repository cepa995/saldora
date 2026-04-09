"""Email delivery service using Resend SDK."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Shared email template ─────────────────────────────────────────────

_LOGO_URL = "https://saldora.rs/logo.png"


def _build_email_html(title: str, content_html: str, footer_html: str = "") -> str:
    """Build a complete HTML email with Saldora branding.

    Args:
        title: Card heading text.
        content_html: Inner HTML for the card body.
        footer_html: Optional additional footer text.

    Returns:
        Full HTML document string.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">

          <!-- Header with logo -->
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <img src="{_LOGO_URL}" alt="Saldora" width="160" height="auto"
                   style="display: block; max-width: 160px; height: auto;" />
            </td>
          </tr>

          <!-- Main card -->
          <tr>
            <td style="background: #ffffff; border-radius: 16px; border: 1px solid #e5e7eb; overflow: hidden;">
              <!-- Purple accent bar -->
              <div style="height: 4px; background: linear-gradient(to right, #7c3aed, #4f46e5);"></div>
              <div style="padding: 32px 32px 24px 32px;">
                <h2 style="margin: 0 0 20px 0; font-size: 20px; font-weight: 600; color: #111827;">
                  {title}
                </h2>
                <div style="font-size: 15px; line-height: 1.6; color: #374151;">
                  {content_html}
                </div>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 0; text-align: center;">
              {f'<p style="color: #6b7280; font-size: 13px; margin: 0 0 8px 0;">{footer_html}</p>' if footer_html else ""}
              <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                &copy; 2026 Saldora &middot; saldora.rs
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _button_html(text: str, url: str) -> str:
    """Generate a styled CTA button.

    Args:
        text: Button label.
        url: Button link URL.

    Returns:
        HTML string for the button.
    """
    return (
        f'<div style="text-align: center; margin: 24px 0 8px 0;">'
        f'<a href="{url}" style="display: inline-block; padding: 12px 32px; '
        f"background: linear-gradient(to right, #7c3aed, #4f46e5); "
        f"color: #ffffff; text-decoration: none; border-radius: 10px; "
        f'font-weight: 500; font-size: 15px;">{text}</a>'
        f"</div>"
    )


def _info_box_html(text: str) -> str:
    """Generate a styled info box.

    Args:
        text: Info text content.

    Returns:
        HTML string for the info box.
    """
    return (
        f'<div style="background: #f9fafb; border: 1px solid #e5e7eb; '
        f'border-radius: 8px; padding: 16px; margin: 16px 0; font-size: 14px; color: #6b7280;">'
        f"{text}</div>"
    )


async def _send_email(to_email: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Raises if API key is not set.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html: HTML body content.

    Returns:
        True if email was sent successfully.

    Raises:
        RuntimeError: If RESEND_API_KEY is not configured.
    """
    if not settings.resend_api_key:
        raise RuntimeError(f"RESEND_API_KEY not set, cannot send email to {to_email}")

    import resend

    resend.api_key = settings.resend_api_key

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
    if inviter_name:
        intro = (
            f"<p><strong>{inviter_name}</strong> vas poziva da se pridružite "
            f"organizaciji <strong>{organization_name}</strong> kao "
            f"<strong>{role}</strong>.</p>"
        )
    else:
        intro = (
            f"<p>Pozvani ste da se pridružite organizaciji "
            f"<strong>{organization_name}</strong> kao "
            f"<strong>{role}</strong>.</p>"
        )

    content = f"""{intro}
    <p style="color: #6b7280; font-size: 14px;">Pozivnica ističe za 7 dana.</p>
    {_button_html("Prihvatite poziv", accept_url)}"""

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
    <p style="color: #6b7280;">
      Vaš nalog na Saldora je uspešno kreiran.
      Sada možete da kreirate organizaciju ili se pridružite postojećoj.
    </p>
    {_button_html("Prijavite se", f"{settings.frontend_url}/login")}"""

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
    content = f"""<p>Zatražili ste resetovanje lozinke za vaš Saldora nalog.</p>
    <p style="color: #6b7280;">
      Kliknite na dugme ispod da biste postavili novu lozinku.
      Link je važeći <strong>1 sat</strong>.
    </p>
    {_button_html("Resetujte lozinku", reset_url)}
    <p style="color: #9ca3af; font-size: 13px; margin-top: 16px;">
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
    <p style="color: #6b7280;">
      Faktura <strong>{invoice_number}</strong> je uspešno
      obrađena i čeka vaš pregled.
    </p>
    {_button_html("Pregledajte fakturu", detail_url)}"""

    html = _build_email_html("Faktura obrađena", content)
    subject = f"Faktura {invoice_number} je obrađena — Saldora"
    return await _send_email(to_email, subject, html)


async def send_archive_email(
    to_email: str,
    org_name: str,
    period: str,
    invoice_count: int,
    download_url: str,
) -> bool:
    """Send a monthly archive export email with download link.

    Args:
        to_email: Organization's billing email.
        org_name: Organization name.
        period: Period string like "2026-03".
        invoice_count: Number of invoices in the archive.
        download_url: Presigned S3 download URL (valid 24h).

    Returns:
        True if email was sent successfully, False otherwise.
    """
    content = f"""<p>Arhivski izvoz vaših faktura za period
    <strong>{period}</strong> je uspešno generisan.</p>

    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #e5e7eb;">
        <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Organizacija</td>
        <td style="padding: 8px 0; font-weight: 500; text-align: right;">{org_name}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e5e7eb;">
        <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Period</td>
        <td style="padding: 8px 0; font-weight: 500; text-align: right;">{period}</td>
      </tr>
      <tr style="border-bottom: 1px solid #e5e7eb;">
        <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Broj faktura</td>
        <td style="padding: 8px 0; font-weight: 500; text-align: right;">{invoice_count}</td>
      </tr>
    </table>

    {
        _info_box_html(
            "<strong>Sadržaj arhive:</strong><br>"
            "• Registar faktura (CSV)<br>"
            "• PDV pregled (Excel)<br>"
            "• Revizorski trag (CSV)<br>"
            "• Originalna PDF dokumenta"
        )
    }

    {_button_html("Preuzmite arhivu", download_url)}

    <p style="color: #9ca3af; font-size: 13px; margin-top: 16px;">
      Link za preuzimanje važi <strong>24 sata</strong>.
    </p>"""

    footer = (
        "Preporučujemo da ovaj fajl sačuvate na sigurnom mestu kao deo vaše "
        "računovodstvene arhive u skladu sa Zakonom o računovodstvu."
    )

    html = _build_email_html("Mesečni arhivski izvoz", content, footer_html=footer)
    subject = f"Mesečni arhivski izvoz {period} — {org_name} — Saldora"
    return await _send_email(to_email, subject, html)
