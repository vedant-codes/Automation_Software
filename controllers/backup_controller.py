"""
controllers/backup_controller.py
Backup & Recovery controller — mirrors user_controller.py pattern.

Each public method maps to one of the 6 task playbooks and runs it
via ansible-playbook as a subprocess, collecting stdout/stderr.
"""

import subprocess
import json
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent   # automation_platform/
PLAYBOOKS_DIR = BASE_DIR / "playbooks"
INVENTORY     = BASE_DIR / "inventory" / "hosts.ini"


# ── Internal helper ────────────────────────────────────────────────────────

def _run_playbook(playbook: str, extra_vars: dict = None, hosts: str = "lab") -> dict:
    """
    Run an Ansible playbook and return a result dict:
        {
            "success": bool,
            "playbook": str,
            "stdout": str,
            "stderr": str,
            "returncode": int
        }
    """
    cmd = [
        "ansible-playbook",
        str(PLAYBOOKS_DIR / playbook),
        "-i", str(INVENTORY),
        "-e", f"target_hosts={hosts}",
    ]

    if extra_vars:
        for k, v in extra_vars.items():
            # Lists / dicts need JSON serialisation
            if isinstance(v, (list, dict)):
                cmd += ["-e", f"{k}={json.dumps(v)}"]
            else:
                cmd += ["-e", f"{k}={v}"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    return {
        "success":    result.returncode == 0,
        "playbook":   playbook,
        "stdout":     result.stdout,
        "stderr":     result.stderr,
        "returncode": result.returncode,
    }


# ── Public API ─────────────────────────────────────────────────────────────

def backup_config_files(hosts: str = "lab") -> dict:
    """
    Task 1 — Backup Critical Configuration Files.
    Backs up /etc/hosts, /etc/resolv.conf, /etc/network/interfaces on Linux
    and network registry + hosts file on Windows.

    Args:
        hosts: Ansible host pattern (default: 'lab' = all lab PCs)

    Returns:
        result dict with success flag, stdout, stderr
    """
    print(f"[backup] Backing up config files on: {hosts}")
    return _run_playbook("backup_config_files.yml", hosts=hosts)


def restore_config(backup_id: str, hosts: str = "lab") -> dict:
    """
    Task 2 — Restore Configuration After Failure.
    Restores a previously created backup archive to the correct system path.

    Args:
        backup_id: Archive filename, e.g. 'hosts_backup_20250401_143005.tar.gz'
        hosts    : Ansible host pattern

    Returns:
        result dict
    """
    if not backup_id:
        raise ValueError("backup_id is required")
    print(f"[backup] Restoring '{backup_id}' on: {hosts}")
    return _run_playbook(
        "restore_config.yml",
        extra_vars={"backup_id": backup_id},
        hosts=hosts,
    )


def backup_user_data(username: str, hosts: str = "lab", extra_paths: list = None) -> dict:
    """
    Task 3 — Backup User Work Before Reimage.
    Backs up Desktop, Documents, Downloads, projects for the given user.

    Args:
        username   : OS username whose data to back up
        hosts      : Ansible host pattern
        extra_paths: Additional paths to include, e.g. ['/home/john/myproject']

    Returns:
        result dict
    """
    if not username:
        raise ValueError("username is required")
    evars = {"target_user": username}
    if extra_paths:
        evars["extra_paths"] = extra_paths
    print(f"[backup] Backing up user data for '{username}' on: {hosts}")
    return _run_playbook("backup_user_data.yml", extra_vars=evars, hosts=hosts)


def verify_backups(machine: str = None, hosts: str = "lab") -> dict:
    """
    Task 4 — Verify Backup Integrity.
    Runs SHA256 checksum comparison on every backup for a given machine.

    Args:
        machine: Hostname to verify backups for (default: each managed node itself)
        hosts  : Ansible host pattern

    Returns:
        result dict
    """
    evars = {}
    if machine:
        evars["target_machine"] = machine
    print(f"[backup] Verifying backups for machine: {machine or '(each node)'}")
    return _run_playbook("verify_backups.yml", extra_vars=evars, hosts=hosts)


def schedule_backup(interval_minutes: int = 1440, hosts: str = "lab") -> dict:
    """
    Task 5 — Schedule Automatic Backups.
    Installs cron (Linux) or Task Scheduler (Windows) entries.

    Args:
        interval_minutes: How often to run backup in minutes (default 1440 = daily)
        hosts           : Ansible host pattern

    Returns:
        result dict
    """
    print(f"[backup] Scheduling auto-backup every {interval_minutes} min on: {hosts}")
    return _run_playbook(
        "schedule_backup.yml",
        extra_vars={"sched_interval_min": interval_minutes},
        hosts=hosts,
    )


def cleanup_backups(keep_latest: int = 5, machine: str = "all") -> dict:
    """
    Task 6 — Manage Backup Storage.
    Lists all backups on the backup server and deletes old ones,
    keeping only the N most recent per machine.

    Args:
        keep_latest: Number of most recent backups to keep (default 5)
        machine    : Specific hostname to clean, or 'all'

    Returns:
        result dict
    """
    print(f"[backup] Cleaning up backups — keeping {keep_latest} per machine, target: {machine}")
    return _run_playbook(
        "cleanup_backups.yml",
        extra_vars={
            "keep_latest":      keep_latest,
            "cleanup_machine":  machine,
        },
        hosts="localhost",   # runs on control node, SSHes to backup server
    )


# ── CLI entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backup & Recovery Controller")
    sub    = parser.add_subparsers(dest="command")

    # backup-config
    p1 = sub.add_parser("backup-config", help="Backup config files on lab PCs")
    p1.add_argument("--hosts", default="lab")

    # restore
    p2 = sub.add_parser("restore", help="Restore a backup by ID")
    p2.add_argument("backup_id")
    p2.add_argument("--hosts", default="lab")

    # backup-user
    p3 = sub.add_parser("backup-user", help="Backup a user's data")
    p3.add_argument("username")
    p3.add_argument("--hosts",  default="lab")
    p3.add_argument("--extra",  nargs="*", default=[], metavar="PATH",
                    help="Extra paths to include")

    # verify
    p4 = sub.add_parser("verify", help="Verify integrity of all backups")
    p4.add_argument("--machine", default=None)
    p4.add_argument("--hosts",   default="lab")

    # schedule
    p5 = sub.add_parser("schedule", help="Schedule automatic backups")
    p5.add_argument("--interval", type=int, default=1440, metavar="MINUTES")
    p5.add_argument("--hosts",    default="lab")

    # cleanup
    p6 = sub.add_parser("cleanup", help="Delete old backups, keep N newest")
    p6.add_argument("--keep",    type=int, default=5, metavar="N")
    p6.add_argument("--machine", default="all")

    args = parser.parse_args()

    result = None
    if args.command == "backup-config":
        result = backup_config_files(hosts=args.hosts)
    elif args.command == "restore":
        result = restore_config(backup_id=args.backup_id, hosts=args.hosts)
    elif args.command == "backup-user":
        result = backup_user_data(username=args.username, hosts=args.hosts,
                                  extra_paths=args.extra or None)
    elif args.command == "verify":
        result = verify_backups(machine=args.machine, hosts=args.hosts)
    elif args.command == "schedule":
        result = schedule_backup(interval_minutes=args.interval, hosts=args.hosts)
    elif args.command == "cleanup":
        result = cleanup_backups(keep_latest=args.keep, machine=args.machine)
    else:
        parser.print_help()
        exit(0)

    if result:
        print(result["stdout"])
        if result["stderr"]:
            print("[stderr]", result["stderr"])
        exit(0 if result["success"] else 1)
