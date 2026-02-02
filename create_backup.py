import os
import shutil
import subprocess
import datetime
import zipfile
import fnmatch
from pathlib import Path
from decouple import config, RepositoryEnv

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "skkp_project"
BACKUP_DIR = BASE_DIR / "backups"
PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"

# Try to find .env file
ENV_PATH = PROJECT_DIR / ".env"
if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / ".env"

# Load config
if ENV_PATH.exists():
    print(f"Loading environment from {ENV_PATH}")
    config_env = config
else:
    print("No .env file found, using defaults")
    config_env = config

DB_NAME = config_env('DB_NAME', default='skkp_db')
DB_USER = config_env('DB_USER', default='postgres')
DB_PASSWORD = config_env('DB_PASSWORD', default='postgres')
DB_HOST = config_env('DB_HOST', default='localhost')
DB_PORT = config_env('DB_PORT', default='5432')

def zip_folder(folder_path, output_path, exclude_patterns=None):
    if exclude_patterns is None:
        exclude_patterns = []
        
    print(f"Zipping {folder_path} to {output_path}...")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, p) for p in exclude_patterns)]
            
            for file in files:
                if any(fnmatch.fnmatch(file, p) for p in exclude_patterns):
                    continue
                    
                file_path = os.path.join(root, file)
                # Create arcname relative to the parent of folder_path so the folder itself is included
                # e.g. if zipping /path/to/project, we want 'project/file.txt' in zip
                arcname = os.path.relpath(file_path, folder_path.parent)
                zipf.write(file_path, arcname)
    print("Zip complete.")

def create_backup():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}"
    current_backup_dir = BACKUP_DIR / backup_name
    
    if not current_backup_dir.exists():
        os.makedirs(current_backup_dir)
        
    print(f"Creating backup in {current_backup_dir}...")
    
    # 1. Database Backup
    print("Backing up database...")
    dump_file = current_backup_dir / f"{DB_NAME}.sql"
    env = os.environ.copy()
    env['PGPASSWORD'] = DB_PASSWORD
    
    cmd = [
        PG_DUMP_PATH,
        "-h", DB_HOST,
        "-p", DB_PORT,
        "-U", DB_USER,
        "-F", "p", # plain text sql
        "-f", str(dump_file),
        DB_NAME
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"Database dumped to {dump_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error dumping database: {e}")
    except FileNotFoundError:
        print(f"pg_dump not found at {PG_DUMP_PATH}")
    except Exception as e:
        print(f"Unexpected error during DB backup: {e}")
        
    # 2. Files Backup
    print("Backing up files...")
    exclude_patterns = ['__pycache__', '*.pyc', '.git', '.vscode', '.idea', 'venv', 'venv_new', 'env', '.hypothesis', 'node_modules']
    
    # Zip skkp_project
    zip_folder(PROJECT_DIR, str(current_backup_dir / "skkp_project.zip"), exclude_patterns)
    
    # Zip tenant_media if exists
    tenant_media = BASE_DIR / "tenant_media"
    if tenant_media.exists():
        zip_folder(tenant_media, str(current_backup_dir / "tenant_media.zip"), exclude_patterns)
    
    # Zip glob_templ if exists
    glob_templ = BASE_DIR / "glob_templ"
    if glob_templ.exists():
        zip_folder(glob_templ, str(current_backup_dir / "glob_templ.zip"), exclude_patterns)

    print(f"\nBackup completed successfully!\nLocation: {current_backup_dir}")

if __name__ == "__main__":
    create_backup()
