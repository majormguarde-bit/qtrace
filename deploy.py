import subprocess
import sys
import argparse
import datetime

# Configuration
REMOTE_USER = "s1147486"
REMOTE_HOST = "qtrace.ru"
REMOTE_DIR = "~/domains/qtrace.ru/qtrace"
RESTART_COMMAND = "touch tmp/restart.txt"

def run_command(command, shell=False, check=True):
    """Run a shell command and return output."""
    print(f"Executing: {' '.join(command) if isinstance(command, list) else command}")
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            check=check, 
            text=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_current_branch():
    return run_command(["git", "branch", "--show-current"]).strip()

def deploy(message=None):
    # 1. Git Operations
    print("=== Step 1: Local Git Operations ===")
    
    # Check status
    status = run_command(["git", "status", "--porcelain"])
    
    if status:
        if not message:
            message = f"Auto-deploy: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        print(f"Changes detected. Committing with message: '{message}'")
        run_command(["git", "add", "."])
        run_command(["git", "commit", "-m", message])
    else:
        print("No local changes to commit.")

    current_branch = get_current_branch()
    print(f"Pushing branch '{current_branch}' to origin...")
    run_command(["git", "push", "origin", current_branch])

    # 2. Remote Operations
    print("\n=== Step 2: Remote Operations ===")
    
    remote_commands = [
        f"cd {REMOTE_DIR}",
        f"git pull origin {current_branch}",
        "source .venv/bin/activate",
        "pip install -r requirements.txt",
        "python manage.py migrate",
        "python manage.py collectstatic --noinput",
        RESTART_COMMAND
    ]
    
    full_remote_command = " && ".join(remote_commands)
    
    ssh_command = [
        "ssh", 
        f"{REMOTE_USER}@{REMOTE_HOST}", 
        full_remote_command
    ]
    
    print(f"Connecting to {REMOTE_HOST}...")
    run_command(ssh_command)
    
    print("\n=== Deployment Completed Successfully! ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Deployment Script")
    parser.add_argument("-m", "--message", help="Commit message")
    args = parser.parse_args()
    
    deploy(args.message)
