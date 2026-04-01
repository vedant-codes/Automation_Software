# Backup & Recovery Module — automation_platform

## Folder Structure

```
automation_platform/
├── main.py                            ← entry point, routes all domains
├── ansible.cfg                        ← Ansible settings
├── inventory/
│   └── hosts.ini                      ← ✏️  EDIT THIS FIRST — put your real IPs here
├── controllers/
│   └── backup_controller.py           ← Python glue, calls playbooks via subprocess
├── primitives/                        ← 6 low-level Ansible building blocks
│   ├── create_backup.yml
│   ├── restore_backup.yml
│   ├── list_backups.yml
│   ├── verify_backup.yml
│   ├── delete_backup.yml
│   └── schedule_backup.yml
└── playbooks/                         ← 6 high-level task playbooks
    ├── backup_config_files.yml        ← Task 1
    ├── restore_config.yml             ← Task 2
    ├── backup_user_data.yml           ← Task 3
    ├── verify_backups.yml             ← Task 4
    ├── schedule_backup.yml            ← Task 5
    └── cleanup_backups.yml            ← Task 6
```

---

## Step 0 — Prerequisites

```bash
pip install ansible
# Linux managed nodes need:  python3, rsync, openssh-server
# Windows managed nodes need: WinRM enabled (see below)
```

### Enable WinRM on Windows lab PCs (run as admin in PowerShell):
```powershell
winrm quickconfig -q
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

---

## Step 1 — Edit inventory/hosts.ini

Replace all placeholder IPs with your actual lab PC IPs and backup server IP.

---

## Step 2 — Test Connectivity

```bash
# From the admin/control node:
ansible linux_lab  -m ping      -i inventory/hosts.ini
ansible windows_lab -m win_ping -i inventory/hosts.ini
ansible backup_server -m ping   -i inventory/hosts.ini
```

---

## Step 3 — Run Playbooks Directly

```bash
# Task 1 — Backup config files on ALL lab PCs
ansible-playbook playbooks/backup_config_files.yml

# Task 2 — Restore a specific backup
ansible-playbook playbooks/restore_config.yml \
    -e "backup_id=hosts_backup_20250401_143005_123456.tar.gz" \
    -e "target_hosts=linux-pc-01"

# Task 3 — Backup user data before reimage
ansible-playbook playbooks/backup_user_data.yml \
    -e "target_user=john" \
    -e "target_hosts=win-pc-01"

# Task 4 — Verify all backups
ansible-playbook playbooks/verify_backups.yml

# Task 5 — Schedule daily auto-backup
ansible-playbook playbooks/schedule_backup.yml \
    -e "sched_interval_min=1440"

# Task 6 — Cleanup old backups, keep 5 per machine
ansible-playbook playbooks/cleanup_backups.yml \
    -e "keep_latest=5"
```

---

## Step 4 — Use the Python Controller

```bash
cd automation_platform

python controllers/backup_controller.py backup-config
python controllers/backup_controller.py restore hosts_backup_20250401.tar.gz
python controllers/backup_controller.py backup-user john --extra /home/john/myproject
python controllers/backup_controller.py verify --machine linux-pc-01
python controllers/backup_controller.py schedule --interval 60
python controllers/backup_controller.py cleanup --keep 3 --machine all
```

Or through main.py (once teammates wire their controllers in):

```bash
python main.py backup backup-config
python main.py backup verify
```

---

## Primitives Reference

| Primitive              | Variables Required                                                   |
|------------------------|----------------------------------------------------------------------|
| `create_backup.yml`    | `backup_source`, `backup_dest`, `backup_server_ip/user/base_path`   |
| `restore_backup.yml`   | `backup_id`, `restore_target`, `backup_server_ip/user/base_path`    |
| `list_backups.yml`     | `backup_server_ip/user/base_path`, `filter_machine` (optional)      |
| `verify_backup.yml`    | `backup_id`, `backup_server_ip/user/base_path`                      |
| `delete_backup.yml`    | `backup_id`, `backup_server_ip/user/base_path`, `filter_machine`    |
| `schedule_backup.yml`  | `sched_source`, `sched_dest`, `sched_interval_min`, `sched_job_name`|

---

## Integration With Teammates

- **Network module**: Call `restore_config` → then trigger network restart in network_controller.
- **Log module**: All playbooks emit standard stdout — log_controller can scrape or redirect to syslog.
- **User module**: Call `backup_user_data(username)` before any `delete_user` operation.
