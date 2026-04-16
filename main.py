"""
main.py — Automation Platform Entry Point
Routes CLI commands to the correct domain controller.

Usage:
    python main.py backup [action]
    python main.py monitor [vitals | health | process | kill <process_name>] [--target <host>]
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
        import controllers.monitoring_controller as mc
        
        # --- NEW LOGIC: Extract Target ---
        target_host = "all"  # Default to all machines
        if "--target" in remaining:
            idx = remaining.index("--target")
            if idx + 1 < len(remaining):
                target_host = remaining[idx + 1]
                # Remove them from 'remaining' so they don't break the 'action' index
                remaining.pop(idx + 1)
                remaining.pop(idx)

        if not remaining:
            print("\nUsage: python main.py monitor <action> [--target <host>]")
            print("Actions: vitals, health, process, kill <process_name>")
            return

        action = remaining[0]
        
        # Pass target_host to each function
        if action == "vitals":
            mc.check_system_vitals(target=target_host)
        elif action == "health":
            mc.perform_health_check(target=target_host)
        elif action == "process":
            mc.monitor_processes(target=target_host)
        elif action == "kill":
            if len(remaining) > 1:
                mc.kill_heavy_processes(remaining[1], target=target_host)
            else:
                print("Error: Please specify a process name to kill.")
        else:
            print(f"Unknown monitoring action: {action}")

    elif args.domain == "provision":
        from controllers.provision_controller import menu
        menu()

    elif args.domain == "user":
        print("[main] User controller delegation...")
        sys.argv = ["user_controller"] + remaining
        from controllers import user_controller

    elif args.domain in ["network", "log"]:
        print(f"[main] The {args.domain} controller is not yet wired in.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()