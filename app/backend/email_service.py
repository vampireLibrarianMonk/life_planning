"""Email delivery seam (AWS SES) + the user-invitation (setup-link) template.

Email is sent via AWS SES using boto3 (same credential model as the rest of the
deployment — the caller's IAM identity; no SMTP password embedded anywhere).
Only the provisioning CLI calls this — the running web app never sends email,
so there is no public email-send surface to abuse. If SES is not configured /
the sender identity isn't verified, send_email raises EmailNotConfiguredError so the
caller can fall back to printing the setup link.
"""

import os


class EmailNotConfiguredError(RuntimeError):
    """Raised when SES isn't usable — caller may fall back to --no-email."""


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """Send an email via AWS SES. Never logs the body or credentials.

    Requires:
      SES_SENDER   verified SES identity to send from (e.g. no-reply@your-domain)
      AWS_REGION   region where the SES identity is verified (default us-east-1)
    Uses the ambient AWS credentials (the admin running the CLI / an IAM role).
    """
    sender = os.getenv("SES_SENDER")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not sender:
        raise EmailNotConfiguredError(
            "SES_SENDER (a verified SES identity) must be set to send email"
        )

    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    client = boto3.client("ses", region_name=region)
    body = {"Text": {"Data": text_body, "Charset": "UTF-8"}}
    if html_body:
        body["Html"] = {"Data": html_body, "Charset": "UTF-8"}
    try:
        client.send_email(
            Source=sender,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        )
    except (BotoCoreError, ClientError) as e:
        # Surface a clean, non-sensitive error (no body/creds).
        raise EmailNotConfiguredError(f"SES send failed: {type(e).__name__}") from e


# --- Invitation template -----------------------------------------------------

_ROLE_BLURB = {
    "admin": "You'll have full access to view and manage the tracker.",
    "readonly": "You'll have view-only access to the records shared with you.",
    "child": "You'll have access to your own record.",
}


def build_invitation(
    display_name: str,
    username: str,
    role: str,
    app_url: str,
    setup_url: str,
    expires_hours: int = 24,
) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body) for a setup-link invitation.

    Contains the username, role in plain terms, the app URL, and the one-time
    setup link. Deliberately contains NO password and NO child PII.
    """
    role_line = _ROLE_BLURB.get(role, "You'll have access to the tracker.")
    subject = "Your Life Plan Tracker account — set your password"

    text_body = f"""Hello {display_name},

An account has been created for you on the Life Plan Tracker.

  Website:   {app_url}
  Username:  {username}
  Access:    {role_line}

To finish setting up, choose your own password using the secure one-time link
below. For your safety, no password was emailed — you set it yourself, and the
link works only once and expires in {expires_hours} hours:

  {setup_url}

After you set your password, sign in at {app_url} with the username above.

If you weren't expecting this, you can ignore this message — the link will
expire on its own.

— Life Plan Tracker
"""

    html_body = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:520px;margin:24px auto;background:#ffffff;border-radius:12px;
              overflow:hidden;border:1px solid #e3e8ee;">
    <div style="background:#2563b0;color:#ffffff;padding:20px 28px;">
      <h1 style="margin:0;font-size:20px;">Life Plan Tracker</h1>
    </div>
    <div style="padding:28px;color:#263238;line-height:1.6;font-size:15px;">
      <p style="margin:0 0 16px;">Hello {display_name},</p>
      <p style="margin:0 0 16px;">An account has been created for you on the
         Life Plan Tracker.</p>
      <table style="width:100%;border-collapse:collapse;margin:0 0 20px;font-size:14px;">
        <tr><td style="padding:6px 0;color:#5a6b7b;width:90px;">Website</td>
            <td style="padding:6px 0;"><a href="{app_url}" style="color:#2563b0;">{app_url}</a></td></tr>
        <tr><td style="padding:6px 0;color:#5a6b7b;">Username</td>
            <td style="padding:6px 0;"><strong>{username}</strong></td></tr>
        <tr><td style="padding:6px 0;color:#5a6b7b;">Access</td>
            <td style="padding:6px 0;">{role_line}</td></tr>
      </table>
      <p style="margin:0 0 20px;">To finish setting up, choose your own password
         using the secure one-time link below. For your safety, <strong>no password
         was emailed</strong> — you set it yourself. The link works only once and
         expires in {expires_hours} hours.</p>
      <p style="margin:0 0 24px;text-align:center;">
        <a href="{setup_url}"
           style="display:inline-block;background:#2563b0;color:#ffffff;
                  text-decoration:none;padding:12px 28px;border-radius:8px;
                  font-weight:600;">Set your password</a>
      </p>
      <p style="margin:0 0 8px;font-size:12px;color:#5a6b7b;">
        If the button doesn't work, copy this link into your browser:</p>
      <p style="margin:0 0 20px;font-size:12px;word-break:break-all;">
        <a href="{setup_url}" style="color:#2563b0;">{setup_url}</a></p>
      <p style="margin:0;font-size:12px;color:#8a97a3;">
        If you weren't expecting this, you can ignore this message — the link
        will expire on its own.</p>
    </div>
  </div>
</body>
</html>
"""
    return subject, text_body, html_body
