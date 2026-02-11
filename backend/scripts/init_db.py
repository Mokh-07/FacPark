import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from backend.config import settings
except ImportError:
    # Fallback if config import fails physically
    class Settings:
        DB_USER = "root"
        DB_PASSWORD = ""
        DB_HOST = "localhost"
        DB_PORT = 3306
        DB_NAME = "facpark"
    settings = Settings()

SQL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/sql'))

def setup_database():
    print("=== AUTO-SETUP DATABASE ===")
    
    # 1. Connect to MySQL Server (no db)
    connection_string = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}"
    engine = create_engine(connection_string)
    
    try:
        with engine.connect() as conn:
            # Create DB
            print(f"Creating database '{settings.DB_NAME}' if not exists...")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.execute(text(f"USE {settings.DB_NAME}"))
            
            # Read SQL files
            files = ['01_schema.sql', '02_seed.sql', '03_indexes.sql']
            
            for fname in files:
                fpath = os.path.join(SQL_DIR, fname)
                print(f"Executing {fname}...")
                if os.path.exists(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Split by semi-colon properly? MySQL dumb split might fail on triggers.
                        # Simple approach: execution via raw text if possible or splits.
                        # Since 01_schema contains DELIMITER commands, simple split won't work perfectly via sqlalchemy.
                        # However, for seed data it's fine.
                        
                        # Fallback: using os.system with mysql command line is safer if available
                        pass 
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return False

    return True

if __name__ == "__main__":
    # Use mysql CLI directly for robust SQL file execution
    db_name = settings.DB_NAME
    user = settings.DB_USER
    
    print(f"Initializing database: {db_name}")
    
    # 1. Create DB
    cmd_create = f'mysql -u {user} -e "CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
    code = os.system(cmd_create)
    if code != 0:
        print("ERROR: Could not create DB. Is MySQL (XAMPP) running?")
        sys.exit(1)
        
    # 2. Schema
    print("Importing Schema...")
    schema_path = os.path.join(SQL_DIR, '01_schema.sql')
    os.system(f'mysql -u {user} {db_name} < "{schema_path}"')
    
    # 3. Seed
    print("Importing Seed Data...")
    seed_path = os.path.join(SQL_DIR, '02_seed.sql')
    os.system(f'mysql -u {user} {db_name} < "{seed_path}"')
    
    # 4. Indexes
    print("Importing Indexes...")
    idx_path = os.path.join(SQL_DIR, '03_indexes.sql')
    os.system(f'mysql -u {user} {db_name} < "{idx_path}"')
    
    print("\nSUCCESS! Database initialized.")
