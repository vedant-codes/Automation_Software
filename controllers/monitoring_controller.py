import subprocess
import os
import warnings

# Use a more robust way to silence the warning 
# This looks for the "DependencyWarning" by name without needing a direct import
warnings.filterwarnings("ignore", message=".*urllib3.*match a supported version.*")

def run_monitoring_primitive(primitive_name, target="all", extra_vars=None):
    # ... rest of your code stays the same
    """Executes an Ansible playbook and returns the output."""
    
    # Ensure target is treated as a string and not empty
    target = target if target else "all"

    command = [
        "ansible-playbook",
        "-i", "inventory/hosts.ini",
        f"primitives/{primitive_name}.yml",
        "--limit", target
    ]
    
    if extra_vars:
        command.extend(["--extra-vars", extra_vars])
    
    print(f"\n🚀 [ACTION] Running: {primitive_name}")
    print(f"📍 [TARGET] {target}")
    
    try:
        # We use env=os.environ to ensure the environment path is preserved
        result = subprocess.run(command, capture_output=True, text=True, env=os.environ)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ STDOUT ERROR:")
            print(result.stdout)
            print("⚠️  STDERR DETAILS:")
            print(result.stderr)
            
    except Exception as e:
        print(f"🛑 Critical Error executing primitive: {e}")

# --- Domain Functions (The "Logic" Layers) ---

def check_system_vitals(target="all"):
    """Monitor disk space and memory across targets."""
    run_monitoring_primitive("check_disk", target=target)
    run_monitoring_primitive("check_memory", target=target)

def perform_health_check(target="all"):
    """Ping / Health Check all targets."""
    run_monitoring_primitive("health_check", target=target)

def monitor_processes(target="all"):
    """Identify high CPU-consuming processes."""
    run_monitoring_primitive("process_monitor", target=target)

def kill_heavy_processes(process_name, target="all"):
    """Terminate unauthorized or heavy processes."""
    if not process_name:
        print("Error: No process name provided to kill.")
        return
        
    # We pass the process name to the YAML file via extra-vars
    var_string = f"target_process={process_name}"
    run_monitoring_primitive("process_monitor", target=target, extra_vars=var_string)