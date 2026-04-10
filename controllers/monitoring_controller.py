import subprocess

# Add 'target="all"' here to the function definition
def run_monitoring_primitive(primitive_name, target="all", extra_vars=None):
    """Executes an Ansible playbook and returns the output."""
    command = [
        "ansible-playbook",
        "-i", "inventory/hosts.ini",
        f"primitives/{primitive_name}.yml",
        "--limit", target  # Now 'target' is defined!
    ]
    
    # If we need to pass a process name (for pkill), add extra vars
    if extra_vars:
        command.extend(["--extra-vars", extra_vars])
    
    print(f"\n--- [ACTION] Executing: {primitive_name} ---")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
    except Exception as e:
        print(f"Error executing primitive: {e}")

def check_system_vitals():
    """PDF Task: Monitor disk space and memory across all machines."""
    # Problem: Admin needs to monitor disk space and memory 
    run_monitoring_primitive("check_disk")
    run_monitoring_primitive("check_memory")

def perform_health_check():
    """PDF Task: Ping / Health Check all machines."""
    # Problem: System failures detected only when users report them [cite: 62]
    # Automated Solution: ansible all -m ping 
    run_monitoring_primitive("health_check")

def monitor_processes():
    """PDF Task: Identify high CPU-consuming processes."""
    # Problem: Admin needs to identify high CPU-consuming processes 
    run_monitoring_primitive("process_monitor")

def kill_heavy_processes(process_name):
    """PDF Task: Terminate unauthorized or heavy processes."""
    # Problem: Unauthorized processes slow down lab machines 
    # We pass the process name to the YAML file
    var_string = f"target_process={process_name}"
    run_monitoring_primitive("process_monitor", extra_vars=var_string)
