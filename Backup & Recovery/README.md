# Backup & Recovery Module

Part of the **Lab Automation System** — SysAdmin Domain 8.

---

## File Structure

```
backup_recovery/
├── config.py           # All config (paths, SFTP creds, OS flags)
├── backup_manager.py   # 6 core primitives
├── tasks.py            # 6 high-level tasks built on primitives
├── test_backup.py      # Unit tests (no SFTP needed)
└── README.md
```

---

## Primitives (backup_manager.py)

| Primitive | What it does |
|---|---|
| `create_backup(source, destination)` | Zips source, saves locally + SFTP, writes `.meta.json` with checksum |
| `restore_backup(backup_id, target)` | Extracts archive to target; checks local first, then SFTP |
| `list_backups(machine)` | Scans local + SFTP, returns sorted metadata list |
| `verify_backup(backup_id)` | Recomputes SHA256, compares against stored checksum |
| `delete_backup(backup_id)` | Removes `.zip` + `.meta.json` from local + SFTP |
| `schedule_backup(source, dest, interval_minutes)` | Adds cron job (Linux) or schtasks entry (Windows) |

---

## Tasks (tasks.py)

| Task | Function | Problem Solved |
|---|---|---|
| Backup config files | `backup_config_files()` | Protects `/etc/` or Windows registry/hosts |
| Restore after failure | `restore_config_after_failure(backup_id)` | Recovers network settings post-crash |
| Backup user work | `backup_user_data(username)` | Preserves data before OS reimage |
| Verify all backups | `verify_all_backups()` | Detects corrupted archives |
| Schedule auto backup | `setup_auto_backup(source, interval)` | Removes need for manual backups |
| Cleanup old backups | `cleanup_old_backups(keep_latest=5)` | Prevents storage overflow |

---

## Setup

```bash
pip install paramiko   # For SFTP support
```

Set SFTP credentials via environment variables (never hardcode):
```bash
export SFTP_HOST=192.168.1.100
export SFTP_USER=backup_admin
export SFTP_PASSWORD=yourpassword
export SFTP_BASE_PATH=/backups/lab
```

Or edit `config.py` for defaults.

---

## Quick Usage

```python
from config import BackupConfig
from backup_manager import create_backup, verify_backup
from tasks import backup_config_files, cleanup_old_backups

cfg = BackupConfig()

# Backup all critical config files
backup_config_files(cfg=cfg)

# Verify everything is intact
verify_all_backups(cfg=cfg)

# Keep only 5 most recent backups per source
cleanup_old_backups(keep_latest=5, cfg=cfg)
```

---

## Running Tests

```bash
python -m pytest test_backup.py -v
```

Tests run fully offline (no SFTP needed). All 6 primitives + 3 tasks are covered.

---

## Integration Notes for Group Project

- **Expose via API**: Wrap `tasks.py` functions in REST endpoints (FastAPI/Flask) so the frontend or other modules can call them.
- **Machine identity**: Pass `machine=socket.gethostname()` when calling `list_backups()` or `cleanup_old_backups()` to scope operations per lab PC.
- **Network module hook**: After `restore_config_after_failure()` runs, trigger a network restart (that's your Domain 1's job).
- **Log module hook**: Every function logs via Python `logging` — pipe the logger to your Domain 3 log collector.
