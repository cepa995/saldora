#!/usr/bin/env python3
"""Interactive admin tool for managing organization subscription status.

Pick an environment (staging / production), browse every org with its
current `subscription_status`, and flip a chosen org to `active` or
`trial` (or back to `pending` / `canceled`).

"staging" here is the local docker compose stack — Saldora doesn't have
a separate staging server. "production" SSHes into the Hetzner box and
runs psql in the prod postgres container.

This is the manual-payment workflow: a customer registers → the
require_role gate blocks them with `subscription_pending_approval` →
admin runs this script → admin approves → customer can use the app.

Usage:
    python scripts/admin_orgs.py

Requires:
    - For staging: local docker compose stack running (`saldora-postgres`).
    - For production: SSH access to saldora@178.104.205.37.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Environment:
    name: str
    ssh_host: str | None  # None = run locally (no SSH wrapper)
    container: str
    db_user: str = "saldora"
    db_name: str = "saldora"


ENVIRONMENTS: dict[str, Environment] = {
    "staging": Environment(
        name="staging",
        ssh_host=None,  # local docker compose
        container="saldora-postgres",
    ),
    "production": Environment(
        name="production",
        ssh_host="saldora@178.104.205.37",
        container="saldora-postgres",
    ),
}

APPROVED_STATUSES = ("active", "trial")
PENDING_STATUSES = ("pending", "canceled")
# Mirrors PlanTier in apps/api/app/plans.py — keep in sync.
PLAN_TIERS = ("free", "starter", "pro", "agency")


def _psql_argv(env: Environment) -> list[str]:
    """Build the argv that runs psql against the target environment.

    SQL is piped via stdin (subprocess.run input=...) to avoid quoting hell.
    """
    docker_part = [
        "docker",
        "exec",
        "-i",
        env.container,
        "psql",
        "-U",
        env.db_user,
        "-d",
        env.db_name,
        "-t",
        "-A",  # tuples-only, unaligned — clean for parsing
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if env.ssh_host:
        return ["ssh", env.ssh_host, *docker_part]
    return docker_part


def run_sql(env: Environment, sql: str) -> str:
    """Run *sql* against *env*'s postgres container; return stdout."""
    try:
        result = subprocess.run(
            _psql_argv(env),
            input=sql,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"\n[error] psql failed:\n{exc.stderr}\n")
        sys.exit(1)
    return result.stdout.strip()


def list_orgs(env: Environment) -> list[dict]:
    """Fetch every org with status, plan, member count, owner email."""
    sql = """
SELECT row_to_json(o)
FROM (
    SELECT
        org.id::text                AS id,
        org.name                    AS name,
        org.pib                     AS pib,
        org.plan                    AS plan,
        org.subscription_status     AS status,
        org.created_at::text        AS created_at,
        (SELECT COUNT(*) FROM users u WHERE u.organization_id = org.id) AS member_count,
        (
            SELECT u.email FROM users u
            WHERE u.organization_id = org.id AND u.role = 'admin'
            ORDER BY u.created_at ASC LIMIT 1
        )                           AS owner_email
    FROM organizations org
    ORDER BY org.created_at DESC
) o;
"""
    out = run_sql(env, sql)
    if not out:
        return []
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def update_status(env: Environment, org_id: str, new_status: str) -> None:
    """Flip subscription_status on a specific org."""
    # The set of allowed values is enforced at the prompt layer; we still
    # parameterise via psql's :var syntax so a stray quote can't sneak in.
    sql = (
        "\\set status '"  # psql variable
        + new_status.replace("'", "''")
        + "'\n"
        "\\set org_id '" + org_id.replace("'", "''") + "'\n"
        "UPDATE organizations "
        "SET subscription_status = :'status' "
        "WHERE id = :'org_id'::uuid;"
    )
    run_sql(env, sql)


def update_plan(env: Environment, org_id: str, new_plan: str) -> None:
    """Set the org's plan tier (free / starter / pro / agency)."""
    sql = (
        "\\set plan '" + new_plan.replace("'", "''") + "'\n"
        "\\set org_id '" + org_id.replace("'", "''") + "'\n"
        "UPDATE organizations "
        "SET plan = :'plan' "
        "WHERE id = :'org_id'::uuid;"
    )
    run_sql(env, sql)


# ── UI helpers ────────────────────────────────────────────────────────


def _color(text: str, code: str) -> str:
    """Wrap *text* in an ANSI color code if stdout is a TTY."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _status_pill(status: str | None) -> str:
    if status in APPROVED_STATUSES:
        return _color(f"{status:<8}", "32")  # green
    if status == "pending":
        return _color(f"{status:<8}", "33")  # yellow
    if status in ("canceled", "expired"):
        return _color(f"{status:<8}", "31")  # red
    return _color(f"{status or '—':<8}", "90")  # grey for null/unknown


def _prompt(question: str, allowed: list[str] | None = None) -> str:
    while True:
        answer = input(question).strip()
        if allowed is None or answer in allowed:
            return answer
        print(f"  invalid; expected one of {allowed}")


def pick_environment() -> Environment:
    print("\nWhich environment?\n")
    keys = list(ENVIRONMENTS.keys())
    for i, key in enumerate(keys, 1):
        env = ENVIRONMENTS[key]
        tag = (
            _color(env.ssh_host, "36")
            if env.ssh_host
            else _color("(local docker)", "36")
        )
        print(f"  {i}) {key:<11} {tag}")
    print()
    while True:
        choice = _prompt(f"Choose [1-{len(keys)}]: ")
        if not choice.isdigit() or not (1 <= int(choice) <= len(keys)):
            print("  invalid")
            continue
        return ENVIRONMENTS[keys[int(choice) - 1]]


def render_table(orgs: list[dict]) -> None:
    print()
    if not orgs:
        print("  (no organizations)")
        return
    name_w = max(min(40, max((len(o["name"]) for o in orgs), default=4)), 4)
    email_w = max(
        min(35, max((len(o.get("owner_email") or "—") for o in orgs), default=12)), 12
    )
    header = (
        f"  {'#':>3}  STATUS    {'PLAN':<8}  {'NAME':<{name_w}}  "
        f"{'PIB':<10}  {'OWNER':<{email_w}}  {'MEMBERS':<7}  CREATED"
    )
    print(_color(header, "1"))
    print(_color("  " + "─" * (len(header) - 2), "90"))
    for i, o in enumerate(orgs, 1):
        owner = o.get("owner_email") or "—"
        if len(owner) > email_w:
            owner = owner[: email_w - 1] + "…"
        name = o["name"]
        if len(name) > name_w:
            name = name[: name_w - 1] + "…"
        print(
            f"  {i:>3}  {_status_pill(o.get('status'))}  "
            f"{(o.get('plan') or '—'):<8}  {name:<{name_w}}  "
            f"{(o.get('pib') or '—'):<10}  {owner:<{email_w}}  "
            f"{o.get('member_count', 0):<7}  {o['created_at'][:10]}"
        )
    print()


def pick_new_status(current: str | None) -> str | None:
    options = ["active", "trial", "pending", "canceled"]
    print("\n  Set status to:")
    for i, opt in enumerate(options, 1):
        marker = "  ← current" if opt == current else ""
        print(f"    {i}) {opt}{marker}")
    print("    s) skip — keep current")
    print()
    choice = _prompt("  Choose: ", allowed=[*("1234"), "s"])
    if choice == "s":
        return None
    return options[int(choice) - 1]


def pick_new_plan(current: str | None) -> str | None:
    print("\n  Set plan to:")
    for i, opt in enumerate(PLAN_TIERS, 1):
        marker = "  ← current" if opt == current else ""
        print(f"    {i}) {opt}{marker}")
    print("    s) skip — keep current")
    print()
    choice = _prompt("  Choose: ", allowed=[*("1234"), "s"])
    if choice == "s":
        return None
    return PLAN_TIERS[int(choice) - 1]


def main() -> int:
    print(_color("Saldora — admin org tool", "1"))
    env = pick_environment()
    print(f"\nConnected to: {_color(env.name, '36')}")

    while True:
        orgs = list_orgs(env)
        render_table(orgs)
        if not orgs:
            print("  Nothing to approve; exiting.")
            return 0

        choice = _prompt(
            f"Org # to change (1-{len(orgs)}, q to quit): ",
        )
        if choice.lower() in ("q", "quit", "exit"):
            return 0
        if not choice.isdigit() or not (1 <= int(choice) <= len(orgs)):
            print("  invalid")
            continue

        org = orgs[int(choice) - 1]
        current_status = org.get("status") or "—"
        current_plan = org.get("plan") or "—"
        print(
            f"\n  Org: {_color(org['name'], '1')}  "
            f"(id={org['id']}, status={current_status}, plan={current_plan})"
        )

        new_status = pick_new_status(org.get("status"))
        if new_status == org.get("status"):
            new_status = None  # no actual change

        new_plan = pick_new_plan(org.get("plan"))
        if new_plan == org.get("plan"):
            new_plan = None

        if new_status is None and new_plan is None:
            print("  nothing to change.\n")
            continue

        # Single combined confirmation summarising both changes.
        change_lines = []
        if new_status is not None:
            change_lines.append(f"status: {current_status} → {new_status}")
        if new_plan is not None:
            change_lines.append(f"plan:   {current_plan} → {new_plan}")
        print("\n  Pending changes:")
        for line in change_lines:
            print(f"    {line}")
        confirm = _prompt(f"\n  Apply to '{org['name']}'? [y/N]: ").lower()
        if confirm not in ("y", "yes"):
            print("  cancelled.\n")
            continue

        if new_status is not None:
            update_status(env, org["id"], new_status)
        if new_plan is not None:
            update_plan(env, org["id"], new_plan)
        print(_color("  ✓ applied\n", "32"))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[interrupted]")
        sys.exit(130)
