import subprocess


# ─────────────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────────────
def run_playbook(playbook, extra_vars=None):
    cmd = ["ansible-playbook", playbook]

    if extra_vars:
        for k, v in extra_vars.items():
            cmd.extend(["-e", f"{k}={v}"])

    print(f"\n[Provision] Running: {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Operation completed successfully\n")
    except subprocess.CalledProcessError:
        print("\n❌ Operation failed\n")


# ─────────────────────────────────────────────
# TASK: Provision Machine
# ─────────────────────────────────────────────
def provision_machine():
    print("\n=== Provision New Machine ===")

    host = input("Target host (e.g., localhost or linux-pc-01): ").strip()
    user = input("Username to create: ").strip()
    group = input("Group (default: labusers): ").strip() or "labusers"
    hostname = input("Hostname: ").strip()
    dns = input("DNS server (default: 8.8.8.8): ").strip() or "8.8.8.8"

    extra_vars = {
        "target_hosts": host,
        "user": user,
        "group": group,
        "hostname": hostname,
        "dns_server": dns,
    }

    run_playbook("playbooks/provision_machine.yml", extra_vars)


# ─────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────
def menu():
    while True:
        print("\n========== Provisioning Menu ==========")
        print("1. Provision New Machine")
        print("2. Exit")
        print("=======================================")

        choice = input("Enter choice: ").strip()

        if choice == "1":
            provision_machine()
        elif choice == "2":
            print("Exiting Provisioning Module.")
            break
        else:
            print("Invalid choice. Try again.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    menu()