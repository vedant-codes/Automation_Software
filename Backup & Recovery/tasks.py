"""
tasks.py
High-level Backup & Recovery Tasks
Each task maps directly to the problem statements in the spec.
Built entirely on top of the 6 core primitives in backup_manager.py
"""

import os
import platform
import subprocess
import logging
from pathlib import Path

from config import BackupConfig
from backup_manager import (
    create_backup,
    restore_backup,
    list_backups,
    verify_backup,
    delete_backup,
    schedule_backup,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# TASK 1: Backup Critical Configuration Files
# Problem: If system config files are lost, network settings break.
# ─────────────────────────────────────────────────────────────────

def backup_config_files(destination: str = None, cfg: BackupConfig = None) -> list:
    """
    Backs up all critical OS network/config files to the backup destination.

    Linux  : /etc/network/interfaces, /etc/resolv.conf, /etc/hosts, /etc/hostname
    Windows: hosts file + exports network registry key to a .reg file first
    """
    cfg         = cfg or BackupConfig()
    destination = destination or cfg.local_backup_dir
    os_name     = platform.system()
    results     = []

    if os_name == "Windows":
        paths_to_backup = list(cfg.WINDOWS_CONFIG_PATHS)

        # Export network registry key to a temp .reg file before backing it up
        reg_export_path = os.path.join(cfg.temp_dir, "network_registry.reg")
        os.makedirs(cfg.temp_dir, exist_ok=True)
        try:
            subprocess.run(
                ["reg", "export",
                 r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                 reg_export_path, "/y"],
                check=True, capture_output=True
            )
            paths_to_backup = [reg_export_path, r"C:\Windows\System32\drivers\etc\hosts"]
            logger.info("[backup_config_files] Registry exported to .reg file")
        except subprocess.CalledProcessError as e:
            logger.warning(f"[backup_config_files] Registry export failed: {e}")

    else:  # Linux / macOS
        paths_to_backup = [p for p in cfg.LINUX_CONFIG_PATHS if os.path.exists(p)]

    for path in paths_to_backup:
        if not os.path.exists(path):
            logger.warning(f"[backup_config_files] Skipping missing: {path}")
            continue
        try:
            result = create_backup(path, destination, cfg)
            results.append(result)
            logger.info(f"[backup_config_files] ✓ Backed up: {path}")
        except Exception as e:
            logger.error(f"[backup_config_files] ✗ Failed for {path}: {e}")
            results.append({"status": "error", "source": path, "error": str(e)})

    return results


# ─────────────────────────────────────────────────────────────────
# TASK 2: Restore Configuration After Failure
# Problem: A lab computer loses network settings after system crash.
# ─────────────────────────────────────────────────────────────────

def restore_config_after_failure(backup_id: str, cfg: BackupConfig = None) -> dict:
    """
    Restores a previously saved config backup to its original OS location.

    Linux  : restores to /etc/
    Windows: restores to C:\\Windows\\System32\\drivers\\etc\\
             and re-imports .reg files into the registry.
    """
    cfg     = cfg or BackupConfig()
    os_name = platform.system()

    restore_target = (
        r"C:\Windows\System32\drivers\etc"
        if os_name == "Windows"
        else "/etc"
    )

    result = restore_backup(backup_id, restore_target, cfg)

    # On Windows, if the restored archive contains a .reg file, re-import it
    if os_name == "Windows":
        reg_file = os.path.join(restore_target, "network_registry.reg")
        if os.path.exists(reg_file):
            try:
                subprocess.run(
                    ["reg", "import", reg_file],
                    check=True, capture_output=True
                )
                result["registry_restored"] = True
                logger.info("[restore_config] Registry re-imported successfully")
            except subprocess.CalledProcessError as e:
                result["registry_restored"] = False
                result["registry_error"]    = str(e)
                logger.error(f"[restore_config] Registry import failed: {e}")

    logger.info(f"[restore_config_after_failure] Config restored → {restore_target}")
    return result


# ─────────────────────────────────────────────────────────────────
# TASK 3: Backup User Work Before System Reimage
# Problem: Before reinstalling OS, user work must be preserved.
# Targets: Desktop, Documents, lab project folders
# ─────────────────────────────────────────────────────────────────

def backup_user_data(username: str, extra_paths: list = None,
                     destination: str = None, cfg: BackupConfig = None) -> list:
    """
    Backs up a user's Desktop, Documents, and any extra project folders
    before a system reimage.

    username    : OS username (e.g. 'john' or 'DOMAIN\\john')
    extra_paths : additional lab project folders to include
    destination : where to store backups (defaults to cfg.local_backup_dir)
    """
    cfg         = cfg or BackupConfig()
    destination = destination or cfg.local_backup_dir
    os_name     = platform.system()
    results     = []

    # Build standard user paths per OS
    if os_name == "Windows":
        user_home = Path(f"C:\\Users\\{username}")
        standard_paths = [
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads",
        ]
    else:
        user_home = Path(f"/home/{username}")
        standard_paths = [
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "projects",
        ]

    all_paths = list(standard_paths) + (extra_paths or [])

    for path in all_paths:
        path = Path(path)
        if not path.exists():
            logger.warning(f"[backup_user_data] Skipping missing: {path}")
            continue
        try:
            result = create_backup(str(path), destination, cfg)
            results.append(result)
            logger.info(f"[backup_user_data] ✓ {path}")
        except Exception as e:
            logger.error(f"[backup_user_data] ✗ {path}: {e}")
            results.append({"status": "error", "source": str(path), "error": str(e)})

    logger.info(f"[backup_user_data] User '{username}': {len(results)} folder(s) backed up")
    return results


# ─────────────────────────────────────────────────────────────────
# TASK 4: Verify Backup Integrity
# Problem: Backups might get corrupted due to storage issues.
# ─────────────────────────────────────────────────────────────────

def verify_all_backups(machine: str = None, cfg: BackupConfig = None) -> dict:
    """
    Lists all backups (optionally filtered by machine) and verifies each one.
    Returns a summary of valid vs corrupted backups.
    """
    cfg     = cfg or BackupConfig()
    backups = list_backups(machine, cfg)

    summary = {"total": len(backups), "valid": 0, "corrupted": 0, "errors": 0, "details": []}

    for backup in backups:
        bid = backup.get("backup_id")
        try:
            result = verify_backup(bid, cfg)
            if result["is_valid"]:
                summary["valid"] += 1
            else:
                summary["corrupted"] += 1
            summary["details"].append(result)
        except Exception as e:
            summary["errors"] += 1
            summary["details"].append({"backup_id": bid, "status": "error", "error": str(e)})
            logger.error(f"[verify_all_backups] Error verifying {bid}: {e}")

    logger.info(
        f"[verify_all_backups] {summary['total']} checked — "
        f"{summary['valid']} valid, {summary['corrupted']} corrupted, {summary['errors']} errors"
    )
    return summary


# ─────────────────────────────────────────────────────────────────
# TASK 5: Scheduled Automatic Backups
# Problem: Admin cannot manually backup every lab computer.
# ─────────────────────────────────────────────────────────────────

def setup_auto_backup(source: str, destination: str = None,
                      interval_minutes: int = 1440,
                      cfg: BackupConfig = None) -> dict:
    """
    Schedules automatic recurring backups for a given source path.

    interval_minutes defaults to 1440 (daily).
    Uses cron on Linux, Task Scheduler on Windows.
    """
    cfg         = cfg or BackupConfig()
    destination = destination or cfg.local_backup_dir
    return schedule_backup(source, destination, interval_minutes, cfg)


def setup_config_auto_backup(interval_minutes: int = 1440,
                              cfg: BackupConfig = None) -> list:
    """
    Convenience: schedules automatic backups for ALL critical config paths
    on the current OS.
    """
    cfg     = cfg or BackupConfig()
    os_name = platform.system()
    paths   = cfg.WINDOWS_CONFIG_PATHS if os_name == "Windows" else cfg.LINUX_CONFIG_PATHS
    results = []

    for path in paths:
        if os_name != "Windows" and not os.path.exists(path):
            continue
        try:
            result = setup_auto_backup(path, interval_minutes=interval_minutes, cfg=cfg)
            results.append(result)
        except Exception as e:
            logger.error(f"[setup_config_auto_backup] Failed for {path}: {e}")
            results.append({"status": "error", "path": path, "error": str(e)})

    return results


# ─────────────────────────────────────────────────────────────────
# TASK 6: Manage Backup Storage
# Problem: Backup storage fills up over time.
# ─────────────────────────────────────────────────────────────────

def cleanup_old_backups(machine: str = None, keep_latest: int = 5,
                        cfg: BackupConfig = None) -> dict:
    """
    Lists all backups for a machine, keeps the N most recent, deletes the rest.

    machine     : hostname filter (None = all)
    keep_latest : how many recent backups to retain per source
    """
    cfg     = cfg or BackupConfig()
    backups = list_backups(machine, cfg)  # already sorted newest-first

    # Group by source path so we keep N per source independently
    from collections import defaultdict
    by_source = defaultdict(list)
    for b in backups:
        by_source[b.get("source", "unknown")].append(b)

    deleted = []
    errors  = []

    for source, source_backups in by_source.items():
        to_delete = source_backups[keep_latest:]   # everything beyond keep_latest
        for backup in to_delete:
            bid = backup.get("backup_id")
            try:
                result = delete_backup(bid, cfg)
                deleted.append(bid)
                logger.info(f"[cleanup_old_backups] Deleted old backup: {bid}")
            except Exception as e:
                errors.append({"backup_id": bid, "error": str(e)})
                logger.error(f"[cleanup_old_backups] Failed to delete {bid}: {e}")

    summary = {
        "total_found"  : len(backups),
        "kept"         : len(backups) - len(deleted),
        "deleted_count": len(deleted),
        "deleted_ids"  : deleted,
        "errors"       : errors
    }
    logger.info(
        f"[cleanup_old_backups] Kept {summary['kept']}, "
        f"deleted {summary['deleted_count']}, errors {len(errors)}"
    )
    return summary
