import subprocess


def run_playbook(playbook, extra_vars=None):
    cmd = ["ansible-playbook", playbook]

    if extra_vars:
        for k, v in extra_vars.items():
            cmd.extend(["-e", f"{k}={v}"])

    print(f"\n[Provision] Running: {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Success\n")
    except subprocess.CalledProcessError:
        print("\n❌ Failed\n")


def provision_machine():
    print("\n=== Provision New Machine ===")

    host = input("Target host (default: localhost): ").strip() or "localhost"
    user = input("Username: ").strip()
    group = input("Group (default: labusers): ").strip() or "labusers"
    hostname = input("Hostname (leave empty to skip): ").strip()
    dns = input("DNS (default: 8.8.8.8): ").strip() or "8.8.8.8"

    # 🔥 SAFETY FLAGS
    safe_mode = input("Enable SAFE MODE? (y/n, default=y): ").strip().lower() != "n"
    modify_file_flag = input("Modify config files? (y/n): ").strip().lower() == "y"
    run_cmd = input("Run custom command? (y/n): ").strip().lower() == "y"

    extra_vars = {
        "target_hosts": host,
        "user": user,
        "group": group,
        "hostname": hostname,
        "dns_server": dns,
        "safe_mode": safe_mode,
        "modify_file_flag": modify_file_flag,
        "run_cmd": run_cmd,
    }

    run_playbook("playbooks/provision_machine.yml", extra_vars)


def menu():
    while True:
        print("\n========== Provisioning Menu ==========")
        print("1. Full Provision Machine")
        print("2. Exit")

        choice = input("Enter choice: ").strip()

        if choice == "1":
            provision_machine()
        elif choice == "2":
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    menu()