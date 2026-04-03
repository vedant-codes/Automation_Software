import subprocess

def run_playbook(playbook, extra_vars, target):
    cmd = [
        "ansible-playbook",
        playbook,
        "-i", "inventory/hosts.ini",
        "-l", target,   # target group (linux/windows/lab)
        "-e", extra_vars
    ]
    subprocess.run(cmd)


def handle_user_module():
    print("\n=== User Management Tasks ===")
    print("1. Create User")
    print("2. Delete User")
    print("3. Add User to Group")
    print("4. Remove User from Group")
    print("5. Grant Admin (sudo)")
    print("6. Revoke Admin")
    print("7. Grant Command Permission")
    print("8. Lock User")
    print("9. Unlock User")
    print("10. Set Password")
    print("11. List Users")

    choice = input("Select task: ")

    # 🔥 Select target group
    print("\nTarget Groups: linux / windows / lab")
    target = input("Enter target group: ")

    # -------------------------------
    # 1️⃣ CREATE USER
    # -------------------------------
    if choice == "1":
        username = input("Enter username: ")
        run_playbook(
            "primitives/create_user.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 2️⃣ DELETE USER
    # -------------------------------
    elif choice == "2":
        username = input("Enter username: ")
        run_playbook(
            "primitives/delete_user.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 3️⃣ ADD USER TO GROUP
    # -------------------------------
    elif choice == "3":
        username = input("Enter username: ")
        group = input("Enter group: ")
        run_playbook(
            "primitives/add_to_group.yml",
            f"user={username} group={group}",
            target
        )

    # -------------------------------
    # 4️⃣ REMOVE USER FROM GROUP
    # -------------------------------
    elif choice == "4":
        username = input("Enter username: ")
        group = input("Enter group: ")
        run_playbook(
            "primitives/remove_from_group.yml",
            f"user={username} group={group}",
            target
        )

    # -------------------------------
    # 5️⃣ GRANT ADMIN
    # -------------------------------
    elif choice == "5":
        username = input("Enter username: ")
        run_playbook(
            "primitives/grant_sudo.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 6️⃣ REVOKE ADMIN
    # -------------------------------
    elif choice == "6":
        username = input("Enter username: ")
        run_playbook(
            "primitives/revoke_sudo.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 7️⃣ GRANT COMMAND PERMISSION
    # -------------------------------
    elif choice == "7":
        username = input("Enter username: ")
        command = input("Enter command path: ")
        run_playbook(
            "primitives/grant_command.yml",
            f"user={username} command='{command}'",
            "linux"   # 🔥 only Linux
        )

    # -------------------------------
    # 8️⃣ LOCK USER
    # -------------------------------
    elif choice == "8":
        username = input("Enter username: ")
        run_playbook(
            "primitives/lock_user.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 9️⃣ UNLOCK USER
    # -------------------------------
    elif choice == "9":
        username = input("Enter username: ")
        run_playbook(
            "primitives/unlock_user.yml",
            f"user={username}",
            target
        )

    # -------------------------------
    # 🔟 SET PASSWORD
    # -------------------------------
    elif choice == "10":
        username = input("Enter username: ")

        if target == "windows":
            password = input("Enter password: ")
            run_playbook(
                "primitives/set_password.yml",
                f"user={username} password='{password}'",
                target
            )
        else:
            print("⚠️ For Linux, use hashed password")
            password = input("Enter hashed password: ")
            run_playbook(
                "primitives/set_password.yml",
                f"user={username} password_hash='{password}'",
                target
            )

    # -------------------------------
    # 1️⃣1️⃣ LIST USERS
    # -------------------------------
    elif choice == "11":
        run_playbook(
            "primitives/list_users.yml",
            "",
            target
        )

    else:
        print("Invalid choice")