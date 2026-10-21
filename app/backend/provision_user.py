#!/usr/bin/env python3
"""Provision a Life Plan Tracker user and send a setup-link invitation.

Run locally by an admin. Maps a friendly --type to the app's role, creates the
user via the admin-only register endpoint, issues a one-time setup token, and
emails the person a link to set their OWN password (no password is ever
generated-and-emailed or stored in plaintext).

Examples
--------
  # Father/admin, emailed invitation:
  python provision_user.py --type father --username pmflani \
    --display-name "P. Flanigan" --email you@example.com \
    --app-url https://life-planning.my-deployment.com

  # Print the setup link to the terminal instead of emailing:
  python provision_user.py --type visitor --username aunt_jane \
    --display-name "Aunt Jane" --app-url https://life-planning.my-deployment.com --no-email

Admin credentials are read from --admin-user/--admin-pass or the ADMIN_USERNAME/
ADMIN_PASSWORD env vars. Email transport uses SMTP_* env vars (see email_service).
"""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

# Friendly type -> real role. Child defaults to readonly unless --child-write.
TYPE_TO_ROLE = {
    "father": "admin",
    "mother": "admin",
    "child": "readonly",  # overridden to "child" only with --child-write
    "visitor": "readonly",
}


def _post(base, path, payload, token=None):
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base.rstrip("/") + path
    # Guard against non-HTTP schemes (e.g. file://) in the admin-supplied URL.
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Refusing non-HTTP(S) URL: {url}")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")  # nosec B310 - scheme validated above
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {"detail": body}


def main():
    ap = argparse.ArgumentParser(description="Provision a Life Plan Tracker user.")
    ap.add_argument("--type", required=True, choices=list(TYPE_TO_ROLE))
    ap.add_argument("--username", required=True)
    ap.add_argument("--display-name", required=True)
    ap.add_argument("--email", help="delivery address (required unless --no-email)")
    ap.add_argument("--app-url", required=True, help="e.g. https://life-planning.my-deployment.com")
    ap.add_argument("--api-url", help="API base if different from --app-url")
    ap.add_argument(
        "--issue-child-login", action="store_true", help="only meaningful with --type child"
    )
    ap.add_argument(
        "--child-write",
        action="store_true",
        help="with --issue-child-login, grant true child (write) role",
    )
    ap.add_argument(
        "--no-email", action="store_true", help="print the setup link instead of emailing it"
    )
    ap.add_argument("--admin-user", default=os.getenv("ADMIN_USERNAME"))
    ap.add_argument("--admin-pass", default=os.getenv("ADMIN_PASSWORD"))
    ap.add_argument("--expires-hours", type=int, default=24)
    args = ap.parse_args()

    if not args.no_email and not args.email:
        ap.error("--email is required unless --no-email is set")
    if not args.admin_user or not args.admin_pass:
        ap.error(
            "admin credentials required (--admin-user/--admin-pass or ADMIN_USERNAME/ADMIN_PASSWORD)"
        )

    base = args.app_url
    api = args.api_url or args.app_url

    # Resolve role.
    role = TYPE_TO_ROLE[args.type]
    if args.type == "child":
        if not args.issue_child_login:
            print(
                "type=child without --issue-child-login: no login issued "
                "(create/link the profile separately). Nothing to do."
            )
            return 0
        if args.child_write:
            role = "child"

    # 1. Admin login.
    code, data = _post(
        api, "/api/auth/login", {"username": args.admin_user, "password": args.admin_pass}
    )
    if code != 200:
        print(f"ERROR: admin login failed ({code}): {data.get('detail')}", file=sys.stderr)
        return 1
    admin_token = data["access_token"]

    # 2. Register the user with a throwaway random password (discarded).
    placeholder = secrets.token_urlsafe(24)
    code, data = _post(
        api,
        "/api/auth/register",
        {
            "username": args.username,
            "password": placeholder,
            "display_name": args.display_name,
            "role": role,
        },
        token=admin_token,
    )
    if code == 409:
        print(f"ERROR: username '{args.username}' already exists.", file=sys.stderr)
        return 1
    if code not in (200, 201):
        print(f"ERROR: register failed ({code}): {data.get('detail')}", file=sys.stderr)
        return 1

    # 3. Issue a one-time setup token (also stores the email).
    code, data = _post(
        api,
        f"/api/auth/setup-token/{args.username}",
        {"email": args.email, "expires_hours": args.expires_hours},
        token=admin_token,
    )
    if code != 200:
        print(f"ERROR: setup-token failed ({code}): {data.get('detail')}", file=sys.stderr)
        return 1
    raw_token = data["setup_token"]
    expires_at = data["expires_at"]
    setup_url = f"{base.rstrip('/')}/setup?token={raw_token}"

    # 4. Deliver.
    if args.no_email:
        print("\n=== Setup link (deliver out-of-band; do NOT paste into chat/logs) ===")
        print(f"User:     {args.username}  (role: {role})")
        print(f"Expires:  {expires_at}")
        print(f"Link:     {setup_url}\n")
    else:
        from email_service import EmailNotConfiguredError, build_invitation, send_email

        subject, text_body, html_body = build_invitation(
            display_name=args.display_name,
            username=args.username,
            role=role,
            app_url=base,
            setup_url=setup_url,
            expires_hours=args.expires_hours,
        )
        try:
            send_email(args.email, subject, text_body, html_body)
            print(f"Invitation emailed to {args.email}.")
        except EmailNotConfiguredError as e:
            print(f"WARNING: email not sent ({e}). Falling back to printing the link:")
            print(f"\nLink: {setup_url}\n(expires {expires_at})")

    print(
        f"Done. User '{args.username}' created as role '{role}'. "
        f"They set their own password via the link (expires {expires_at})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
