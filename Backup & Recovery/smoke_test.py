from config import BackupConfig
from backup_manager import create_backup, verify_backup, list_backups, delete_backup
from tasks import backup_user_data, verify_all_backups, cleanup_old_backups

cfg = BackupConfig()
cfg.use_sftp = False  # disable SFTP for local testing
cfg.local_backup_dir = "./test_backups"

# 1. Create a backup of any folder you have
result = create_backup(".", "./test_backups", cfg) 
print("Created:", result["backup_id"])

# 2. Verify it
v = verify_backup(result["backup_id"], cfg)
print("Valid:", v["is_valid"])

# 3. List all
backups = list_backups(cfg=cfg)
print("Total backups:", len(backups))

# 4. Cleanup keeping 2
cleanup_old_backups(keep_latest=2, cfg=cfg)