"""
main.py — Automation Platform Entry Point
Routes CLI commands to the correct domain controller.

Usage:
    python main.py backup [action]
    python main.py monitor [vitals | health | process | kill <process_name>]
    python main.py provision
    python main.py user [action]
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog="automation_platform",
        description="Lab Automation Platform — Sysadmin Control Center",
    )
    sub = parser.add_subparsers(dest="domain", help="Domain to operate on")

    # ── Domain Parsers ──────────────────────────────────────────────────────
    # Using add_help=False because child controllers handle their own help
    sub.add_parser("backup",    help="Backup & Recovery operations",   add_help=False)
    sub.add_parser("monitor",   help="System monitoring & health",     add_help=False)
    sub.add_parser("provision", help="Machine provisioning",           add_help=False)
    sub.add_parser("user",      help="User management operations",      add_help=False)
    sub.add_parser("network",   help="Network & connectivity checks",   add_help=False)
    sub.add_parser("log",       help="Log collection & auditing",       add_help=False)

    # Parse the top-level domain, keep the rest for the controllers
    args, remaining = parser.parse_known_args()

    # ── Routing Logic ───────────────────────────────────────────────────────

    if args.domain == "backup":
        # Re-using the logic from your repository for the backup domain
        sys.argv = ["backup_controller"] + remaining
        import controllers.backup_controller as bc
        bc.__name__ = "__main__"
        try:
            exec(
                open("controllers/backup_controller.py").read()
                .split("if __name__")[1],
                {**bc.__dict__, "__name__": "__main__"}
            )
        except Exception as e:
            print(f"[Error] Failed to execute backup controller: {e}")

    elif args.domain == "monitor":
        # Integrating your new monitoring_controller.py
        import controllers.monitoring_controller as mc
        
        if not remaining:
            print("\nUsage: python main.py monitor <action>")
            print("Actions: vitals, health, process, kill <process_name>")
            return

        action = remaining[0]
        
        if action == "vitals":
            mc.check_system_vitals()
        elif action == "health":
            mc.perform_health_check()
        elif action == "process":
            mc.monitor_processes()
        elif action == "kill":
            if len(remaining) > 1:
                mc.kill_heavy_processes(remaining[1])
            else:
                print("Error: Please specify a process name to kill.")
        else:
            print(f"Unknown monitoring action: {action}")

    elif args.domain == "provision":
        from controllers.provision_controller import menu
        menu()

    elif args.domain == "user":
        # Placeholder for teammate's user_controller
        print("[main] User controller delegation...")
        sys.argv = ["user_controller"] + remaining
        from controllers import user_controller

    elif args.domain in ["network", "log"]:
        print(f"[main] The {args.domain} controller is not yet wired in.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()