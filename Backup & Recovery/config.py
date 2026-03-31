"""
config.py
Centralized configuration for the Backup & Recovery module.
Edit the defaults here or pass env variables.
"""

import os
import platform
from dataclasses import dataclass, field


@dataclass
class BackupConfig:
    # ── Storage mode ──────────────────────────────
    use_local : bool = True
    use_sftp  : bool = True

    # ── Local paths ───────────────────────────────
    # Default local backup root differs per OS
    local_backup_dir: str = field(default_factory=lambda: (
        r"C:\BackupStorage" if platform.system() == "Windows"
        else "/var/backups/lab_backups"
    ))

    # Temp dir for zipping before upload
    temp_dir: str = field(default_factory=lambda: (
        os.path.join(os.environ.get("TEMP", r"C:\Temp"), "backup_tmp")
        if platform.system() == "Windows"
        else "/tmp/backup_tmp"
    ))

    # ── SFTP settings ─────────────────────────────
    sftp_host    : str = os.environ.get("SFTP_HOST",     "192.168.1.100")
    sftp_port    : int = int(os.environ.get("SFTP_PORT", "22"))
    sftp_user    : str = os.environ.get("SFTP_USER",     "backup_admin")
    sftp_password: str = os.environ.get("SFTP_PASSWORD", "")
    sftp_base_path: str = os.environ.get("SFTP_BASE_PATH", "/backups/lab")

    # ── Windows-specific config paths ─────────────
    # These are the critical config files to protect
    WINDOWS_CONFIG_PATHS: tuple = (
        r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",  # Network registry
        r"C:\Windows\System32\drivers\etc\hosts",
    )

    # ── Linux-specific config paths ───────────────
    LINUX_CONFIG_PATHS: tuple = (
        "/etc/network/interfaces",
        "/etc/resolv.conf",
        "/etc/hosts",
        "/etc/hostname",
    )
