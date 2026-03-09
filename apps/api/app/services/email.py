"""Email delivery service using Resend SDK."""

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set, skipping email to %s", to_email)
        return False

    import resend

    resend.api_key = settings.resend_api_key

    subject = f"Poziv za {organization_name} — FakturaAI"

    html_body = _build_invitation_html(
        organization_name=organization_name,
        role=role,
        accept_url=accept_url,
        inviter_name=inviter_name,
    )

    try:
        resend.Emails.send(
            {
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
        )
        logger.info("Invitation email sent to %s for org %s", to_email, organization_name)
        return True
    except Exception:
        logger.exception("Failed to send invitation email to %s", to_email)
        return False


def _build_invitation_html(
    organization_name: str,
    role: str,
    accept_url: str,
    inviter_name: str | None = None,
) -> str:
    """Build HTML body for invitation email.

    Args:
        organization_name: Name of the inviting organization.
        role: Offered role.
        accept_url: URL to accept the invitation.
        inviter_name: Name of the inviter.

    Returns:
        HTML string for the email body.
    """
    inviter_line = (
        f"<p>{inviter_name} vas poziva da se pridružite organizaciji "
        f"<strong>{organization_name}</strong> kao <strong>{role}</strong>.</p>"
        if inviter_name
        else f"<p>Pozvani ste da se pridružite organizaciji "
        f"<strong>{organization_name}</strong> kao <strong>{role}</strong>.</p>"
    )

    body_style = (
        "font-family: -apple-system, BlinkMacSystemFont, "
        "'Segoe UI', Roboto, sans-serif; "
        "max-width: 600px; margin: 0 auto; "
        "padding: 40px 20px; color: #1f2937;"
    )
    card_style = (
        "background: #f9fafb; border: 1px solid #e5e7eb; "
        "border-radius: 12px; padding: 32px; text-align: center;"
    )
    btn_style = (
        "display: inline-block; margin-top: 24px; "
        "padding: 12px 32px; "
        "background: linear-gradient(to right, #7c3aed, #4f46e5); "
        "color: white; text-decoration: none; "
        "border-radius: 8px; font-weight: 500;"
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="{body_style}">
  <div style="text-align: center; margin-bottom: 32px;">
    <h1 style="color: #7c3aed; font-size: 24px; margin: 0;">
      FakturaAI
    </h1>
  </div>

  <div style="{card_style}">
    <h2 style="font-size: 20px; margin: 0 0 16px 0;">
      Poziv za pridruživanje
    </h2>
    {inviter_line}
    <p style="color: #6b7280; font-size: 14px;">
      Pozivnica ističe za 7 dana.
    </p>
    <a href="{accept_url}" style="{btn_style}">
      Prihvatite poziv
    </a>
  </div>

  <p style="text-align: center; color: #9ca3af; font-size: 12px; margin-top: 32px;">
    Ako niste očekivali ovaj email, možete ga ignorisati.
  </p>
</body>
</html>"""


async def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Send password reset email (stub for future implementation).

    Args:
        to_email: Recipient email address.
        reset_url: URL to reset password.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    logger.info("Password reset email would be sent to %s (not implemented)", to_email)
    return True
