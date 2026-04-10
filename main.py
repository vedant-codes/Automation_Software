"""
main.py — Automation Platform Entry Point
Routes CLI commands to the correct domain controller.

Usage:
    python main.py backup backup-config
    python main.py backup restore hosts_backup_20250401.tar.gz
    python main.py backup backup-user john
    python main.py backup verify
    python main.py backup schedule --interval 60
    python main.py backup cleanup --keep 3

    # Your teammates' domains (add their imports once ready):
    python main.py user   create --username alice
    python main.py network check-connectivity
    python main.py log    collect --since 24h
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="automation_platform",
        description="Lab Automation Platform — Sysadmin Control Center",
    )
    sub = parser.add_subparsers(dest="domain", help="Domain to operate on")

    # ── Backup & Recovery (this module) ─────────────────────────────────────
    sub.add_parser("backup",  help="Backup & Recovery operations",  add_help=False)

    # ── Placeholders for teammates — they fill these in ──────────────────────
    sub.add_parser("user",    help="User management operations",     add_help=False)
    sub.add_parser("network", help="Network & connectivity checks",  add_help=False)
    sub.add_parser("log",     help="Log collection & auditing",      add_help=False)
    sub.add_parser("provision", help="Machine provisioning", add_help=False)

    # Parse just the domain arg, pass the rest to the child controller
    args, remaining = parser.parse_known_args()

    if args.domain == "backup":
        # Delegate everything to backup_controller's own argparse
        sys.argv = ["backup_controller"] + remaining
        from controllers.backup_controller import (
            backup_config_files, restore_config, backup_user_data,
            verify_backups, schedule_backup, cleanup_backups,
        )
        import controllers.backup_controller as bc
        bc.__name__ = "__main__"
        # Re-run the CLI block inside backup_controller
        exec(
            open("controllers/backup_controller.py").read()
            .split("if __name__")[1],
            {**bc.__dict__, "__name__": "__main__"}
        )

    elif args.domain == "user":
        # TODO: teammate imports user_controller here
        sys.argv = ["user_controller"] + remaining
        from controllers import user_controller   # noqa: F401

    elif args.domain == "network":
        # TODO: teammate imports network_controller here
        print("[main] network controller — not yet wired in")

    elif args.domain == "log":
        # TODO: teammate imports log_controller here
        print("[main] log controller — not yet wired in")
    
    elif args.domain == "provision":
        from controllers.provision_controller import menu
        menu()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
