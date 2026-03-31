"""
backup_manager.py
Backup & Recovery Module — Core Primitives
Cross-platform (Linux + Windows) | Local + SFTP storage
"""

import os
import sys
import shutil
import hashlib
import json
import logging
import platform
import zipfile
from datetime import datetime
from pathlib import Path

# Optional SFTP support
try:
    import paramiko
    SFTP_AVAILABLE = True
except ImportError:
    SFTP_AVAILABLE = False

from config import BackupConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────

def _timestamp() -> str:
    # Use microseconds to avoid collisions when creating multiple backups rapidly
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _backup_filename(source: str) -> str:
    base = Path(source).name
    return f"{base}_backup_{_timestamp()}.zip"

def _get_sftp_client(cfg: BackupConfig):
    """Returns a connected (transport, sftp) tuple or raises."""
    if not SFTP_AVAILABLE:
        raise RuntimeError("paramiko is not installed. Run: pip install paramiko")
    transport = paramiko.Transport((cfg.sftp_host, cfg.sftp_port))
    transport.connect(username=cfg.sftp_user, password=cfg.sftp_password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return transport, sftp

def _zip_source(source: str, zip_path: str):
    """Zip a file or directory into zip_path."""
    source_path = Path(source)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if source_path.is_dir():
            for file in source_path.rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(source_path.parent))
        else:
            zf.write(source_path, source_path.name)

def _compute_checksum(filepath: str) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def _metadata_path(backup_dir: str, backup_filename: str) -> str:
    return os.path.join(backup_dir, backup_filename + ".meta.json")

def _save_metadata(backup_dir: str, backup_filename: str, metadata: dict):
    path = _metadata_path(backup_dir, backup_filename)
    with open(path, 'w') as f:
        json.dump(metadata, f, indent=2)

def _load_metadata(meta_path: str) -> dict:
    with open(meta_path, 'r') as f:
        return json.load(f)


# ─────────────────────────────────────────────
# PRIMITIVE 1: create_backup(source, destination)
# ─────────────────────────────────────────────

def create_backup(source: str, destination: str, cfg: BackupConfig = None) -> dict:
    """
    Compress source (file or directory) into a .zip archive and store it
    at destination (local path or SFTP remote path based on cfg).

    Returns a result dict with backup_id, checksum, and metadata.
    """
    cfg = cfg or BackupConfig()

    if not os.path.exists(source):
        raise FileNotFoundError(f"Source not found: {source}")

    filename   = _backup_filename(source)
    tmp_zip    = os.path.join(cfg.temp_dir, filename)
    os.makedirs(cfg.temp_dir, exist_ok=True)

    logger.info(f"[create_backup] Compressing '{source}' → '{tmp_zip}'")
    _zip_source(source, tmp_zip)

    checksum = _compute_checksum(tmp_zip)

    metadata = {
        "backup_id"  : filename,
        "source"     : str(source),
        "destination": str(destination),
        "timestamp"  : _timestamp(),
        "platform"   : platform.system(),
        "checksum"   : checksum,
        "size_bytes" : os.path.getsize(tmp_zip),
        "storage"    : []
    }

    # ── Local storage ──
    if cfg.use_local:
        local_dest = os.path.join(destination, filename)
        os.makedirs(destination, exist_ok=True)
        shutil.copy2(tmp_zip, local_dest)
        _save_metadata(destination, filename, metadata)
        metadata["storage"].append({"type": "local", "path": local_dest})
        logger.info(f"[create_backup] Saved locally: {local_dest}")

    # ── SFTP storage ──
    if cfg.use_sftp:
        transport, sftp = _get_sftp_client(cfg)
        try:
            remote_dir  = destination if destination.startswith('/') else cfg.sftp_base_path
            remote_path = f"{remote_dir}/{filename}"
            # Ensure remote dir exists
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)
            sftp.put(tmp_zip, remote_path)
            metadata["storage"].append({"type": "sftp", "path": remote_path})
            logger.info(f"[create_backup] Uploaded via SFTP: {remote_path}")
        finally:
            sftp.close()
            transport.close()

    # Cleanup temp
    os.remove(tmp_zip)

    logger.info(f"[create_backup] Done. backup_id={filename}, checksum={checksum}")
    return {"status": "success", "backup_id": filename, "checksum": checksum, "metadata": metadata}


# ─────────────────────────────────────────────
# PRIMITIVE 2: restore_backup(source, target)
# ─────────────────────────────────────────────

def restore_backup(backup_id: str, target: str, cfg: BackupConfig = None) -> dict:
    """
    Restore a backup archive identified by backup_id to target directory.
    Looks in local storage first; falls back to SFTP.
    """
    cfg = cfg or BackupConfig()
    os.makedirs(target, exist_ok=True)

    zip_path = None

    # ── Try local first ──
    if cfg.use_local:
        local_path = os.path.join(cfg.local_backup_dir, backup_id)
        if os.path.exists(local_path):
            zip_path = local_path
            logger.info(f"[restore_backup] Found locally: {local_path}")

    # ── Fall back to SFTP ──
    if zip_path is None and cfg.use_sftp:
        transport, sftp = _get_sftp_client(cfg)
        try:
            tmp_zip = os.path.join(cfg.temp_dir, backup_id)
            os.makedirs(cfg.temp_dir, exist_ok=True)
            remote_path = f"{cfg.sftp_base_path}/{backup_id}"
            sftp.get(remote_path, tmp_zip)
            zip_path = tmp_zip
            logger.info(f"[restore_backup] Downloaded from SFTP: {remote_path}")
        finally:
            sftp.close()
            transport.close()

    if zip_path is None:
        raise FileNotFoundError(f"Backup not found: {backup_id}")

    logger.info(f"[restore_backup] Extracting '{zip_path}' → '{target}'")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(target)

    logger.info(f"[restore_backup] Restore complete → {target}")
    return {"status": "success", "backup_id": backup_id, "restored_to": target}


# ─────────────────────────────────────────────
# PRIMITIVE 3: list_backups(machine)
# ─────────────────────────────────────────────

def list_backups(machine: str = None, cfg: BackupConfig = None) -> list:
    """
    List all backups. If machine is provided, filter by machine name.
    Returns a list of metadata dicts.
    """
    cfg = cfg or BackupConfig()
    results = []

    # ── Scan local ──
    if cfg.use_local and os.path.isdir(cfg.local_backup_dir):
        for entry in Path(cfg.local_backup_dir).rglob("*.meta.json"):
            try:
                meta = _load_metadata(str(entry))
                meta["_storage_type"] = "local"
                results.append(meta)
            except Exception as e:
                logger.warning(f"[list_backups] Could not read meta {entry}: {e}")

    # ── Scan SFTP ──
    if cfg.use_sftp:
        transport, sftp = _get_sftp_client(cfg)
        try:
            files = sftp.listdir(cfg.sftp_base_path)
            for fname in files:
                if fname.endswith(".meta.json"):
                    remote_meta = f"{cfg.sftp_base_path}/{fname}"
                    with sftp.open(remote_meta, 'r') as f:
                        meta = json.load(f)
                    meta["_storage_type"] = "sftp"
                    results.append(meta)
        except Exception as e:
            logger.warning(f"[list_backups] SFTP scan error: {e}")
        finally:
            sftp.close()
            transport.close()

    # ── Filter by machine (matches hostname in source path or platform) ──
    if machine:
        results = [r for r in results if machine.lower() in r.get("source", "").lower()
                   or machine.lower() in r.get("platform", "").lower()]

    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    logger.info(f"[list_backups] Found {len(results)} backup(s)" +
                (f" for machine='{machine}'" if machine else ""))
    return results


# ─────────────────────────────────────────────
# PRIMITIVE 4: verify_backup(file)
# ─────────────────────────────────────────────

def verify_backup(backup_id: str, cfg: BackupConfig = None) -> dict:
    """
    Verify backup integrity by recomputing checksum and comparing with stored metadata.
    Works for both local and SFTP.
    """
    cfg = cfg or BackupConfig()
    zip_path  = None
    meta      = None
    temp_file = None

    # ── Try local ──
    if cfg.use_local:
        local_zip  = os.path.join(cfg.local_backup_dir, backup_id)
        local_meta = _metadata_path(cfg.local_backup_dir, backup_id)
        if os.path.exists(local_zip) and os.path.exists(local_meta):
            zip_path = local_zip
            meta     = _load_metadata(local_meta)

    # ── Try SFTP ──
    if zip_path is None and cfg.use_sftp:
        transport, sftp = _get_sftp_client(cfg)
        try:
            tmp = os.path.join(cfg.temp_dir, backup_id)
            os.makedirs(cfg.temp_dir, exist_ok=True)
            sftp.get(f"{cfg.sftp_base_path}/{backup_id}", tmp)
            meta_remote = f"{cfg.sftp_base_path}/{backup_id}.meta.json"
            with sftp.open(meta_remote, 'r') as f:
                meta = json.load(f)
            zip_path  = tmp
            temp_file = tmp
        finally:
            sftp.close()
            transport.close()

    if zip_path is None or meta is None:
        raise FileNotFoundError(f"Backup or metadata not found: {backup_id}")

    actual_checksum   = _compute_checksum(zip_path)
    expected_checksum = meta.get("checksum", "")
    is_valid          = actual_checksum == expected_checksum

    if temp_file and os.path.exists(temp_file):
        os.remove(temp_file)

    status = "valid" if is_valid else "CORRUPTED"
    logger.info(f"[verify_backup] {backup_id} → {status}")
    return {
        "status"           : status,
        "backup_id"        : backup_id,
        "expected_checksum": expected_checksum,
        "actual_checksum"  : actual_checksum,
        "is_valid"         : is_valid
    }


# ─────────────────────────────────────────────
# PRIMITIVE 5: delete_backup(backup_id)
# ─────────────────────────────────────────────

def delete_backup(backup_id: str, cfg: BackupConfig = None) -> dict:
    """
    Delete a backup archive and its metadata from local and/or SFTP storage.
    """
    cfg     = cfg or BackupConfig()
    deleted = []

    # ── Local ──
    if cfg.use_local:
        local_zip  = os.path.join(cfg.local_backup_dir, backup_id)
        local_meta = _metadata_path(cfg.local_backup_dir, backup_id)
        for f in [local_zip, local_meta]:
            if os.path.exists(f):
                os.remove(f)
                deleted.append(f)
                logger.info(f"[delete_backup] Deleted local: {f}")

    # ── SFTP ──
    if cfg.use_sftp:
        transport, sftp = _get_sftp_client(cfg)
        try:
            for remote in [
                f"{cfg.sftp_base_path}/{backup_id}",
                f"{cfg.sftp_base_path}/{backup_id}.meta.json"
            ]:
                try:
                    sftp.remove(remote)
                    deleted.append(remote)
                    logger.info(f"[delete_backup] Deleted SFTP: {remote}")
                except FileNotFoundError:
                    pass
        finally:
            sftp.close()
            transport.close()

    if not deleted:
        raise FileNotFoundError(f"No backup files found to delete: {backup_id}")

    return {"status": "deleted", "backup_id": backup_id, "deleted_files": deleted}


# ─────────────────────────────────────────────
# PRIMITIVE 6: schedule_backup(time, path)
# ─────────────────────────────────────────────

def schedule_backup(source: str, destination: str, interval_minutes: int,
                    cfg: BackupConfig = None) -> dict:
    """
    Schedule recurring backups using:
      - cron  (Linux/macOS)
      - Task Scheduler via schtasks (Windows)

    interval_minutes: how often to run (e.g. 60 = hourly, 1440 = daily)
    """
    cfg     = cfg or BackupConfig()
    os_name = platform.system()

    # Absolute path to this script so the scheduler can call it
    script_path = os.path.abspath(__file__)
    python_exe  = sys.executable

    task_cmd = (
        f'"{python_exe}" "{script_path}" '
        f'create_backup "{source}" "{destination}"'
    )

    if os_name == "Linux" or os_name == "Darwin":
        result = _schedule_cron(task_cmd, interval_minutes)
    elif os_name == "Windows":
        result = _schedule_windows(task_cmd, source, interval_minutes)
    else:
        raise OSError(f"Unsupported OS for scheduling: {os_name}")

    logger.info(f"[schedule_backup] Scheduled every {interval_minutes}min on {os_name}")
    return {
        "status"            : "scheduled",
        "os"                : os_name,
        "source"            : source,
        "destination"       : destination,
        "interval_minutes"  : interval_minutes,
        "scheduler_detail"  : result
    }


def _schedule_cron(task_cmd: str, interval_minutes: int) -> str:
    """Add a cron job for the given command."""
    import subprocess
    cron_expr = f"*/{interval_minutes} * * * *" if interval_minutes < 60 else \
                f"0 */{interval_minutes // 60} * * *"
    cron_line = f"{cron_expr} {task_cmd}\n"

    # Read existing crontab
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = proc.stdout if proc.returncode == 0 else ""

    if task_cmd in existing:
        return "Already scheduled in crontab"

    new_crontab = existing + cron_line
    subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
    return f"Cron job added: {cron_line.strip()}"


def _schedule_windows(task_cmd: str, source: str, interval_minutes: int) -> str:
    """Register a Windows Task Scheduler task."""
    import subprocess
    task_name = f"BackupTask_{Path(source).name}_{_timestamp()}"
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", task_cmd,
        "/sc", "MINUTE",
        "/mo", str(interval_minutes),
        "/f"
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return f"Task Scheduler task created: {task_name}"


# ─────────────────────────────────────────────
# CLI entry point (used by scheduler)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) >= 4 and sys.argv[1] == "create_backup":
        result = create_backup(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python backup_manager.py create_backup <source> <destination>")
