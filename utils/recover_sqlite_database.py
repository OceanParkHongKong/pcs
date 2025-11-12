#!/usr/bin/env python3
"""
SQLite Database Recovery Script for people_count_database.db

This script attempts to recover a malformed SQLite database and sets up WAL mode
for better performance and concurrency. It includes multiple recovery strategies
and creates a backup of the original database.

Usage:
    python recover_database.py [database_path]
    
If no path is provided, it will search for people_count_database.db in common locations.
"""

import sqlite3
import os
import shutil
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_recovery.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseRecovery:
    def __init__(self, db_path=None):
        self.db_path = db_path or self.find_database()
        self.backup_path = None
        self.recovered_path = None
        
    def find_database(self):
        """Find people_count_database.db in common locations"""
        possible_paths = [
            'people_count_database.db',
            './people_count_database.db',
            '../swift/people_count_database.db',
            './swift/people_count_database.db',
            '/app/people_count_database.db',
        ]
        
        logger.info("🔍 Searching for people_count_database.db...")
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"✅ Found database at: {path}")
                return path
                
        raise FileNotFoundError(
            f"❌ people_count_database.db not found in any of these locations: {possible_paths}"
        )
    
    def create_backup(self):
        """Create a backup of the original database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_path = f"{self.db_path}.backup_{timestamp}"
        
        try:
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"✅ Backup created: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False
    
    def check_database_integrity(self, db_path):
        """Check if database is accessible and get integrity status"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            table_count = cursor.fetchone()[0]
            
            # Check integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            # Check if traffic table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traffic'")
            traffic_table_exists = cursor.fetchone() is not None
            
            # Get row count if traffic table exists
            row_count = 0
            if traffic_table_exists:
                cursor.execute("SELECT COUNT(*) FROM traffic")
                row_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'accessible': True,
                'integrity': integrity_result,
                'table_count': table_count,
                'traffic_table_exists': traffic_table_exists,
                'row_count': row_count
            }
            
        except Exception as e:
            logger.warning(f"⚠️  Database check failed: {e}")
            return {
                'accessible': False,
                'error': str(e)
            }
    
    def recover_using_dump(self):
        """Attempt recovery using .dump command"""
        logger.info("🔧 Attempting recovery using .dump method...")
        
        self.recovered_path = f"{self.db_path}.recovered"
        dump_file = f"{self.db_path}.dump"
        
        try:
            # Try to dump the database
            dump_cmd = f'sqlite3 "{self.db_path}" ".dump" > "{dump_file}"'
            result = os.system(dump_cmd)
            
            if result != 0:
                logger.error("❌ Failed to dump database")
                return False
            
            if not os.path.exists(dump_file) or os.path.getsize(dump_file) == 0:
                logger.error("❌ Dump file is empty or doesn't exist")
                return False
            
            # Create new database from dump
            restore_cmd = f'sqlite3 "{self.recovered_path}" < "{dump_file}"'
            result = os.system(restore_cmd)
            
            if result == 0:
                logger.info("✅ Successfully recovered database using dump method")
                # Clean up dump file
                os.remove(dump_file)
                return True
            else:
                logger.error("❌ Failed to restore from dump")
                return False
                
        except Exception as e:
            logger.error(f"❌ Dump recovery failed: {e}")
            return False
    
    def recover_using_python_dump(self):
        """Attempt recovery using Python sqlite3 with iterdump"""
        logger.info("🔧 Attempting recovery using Python iterdump method...")
        
        self.recovered_path = f"{self.db_path}.recovered_python"
        
        try:
            # Open corrupted database
            source_conn = sqlite3.connect(self.db_path)
            
            # Create new database
            dest_conn = sqlite3.connect(self.recovered_path)
            
            # Dump and restore
            with dest_conn:
                for line in source_conn.iterdump():
                    dest_conn.execute(line)
            
            source_conn.close()
            dest_conn.close()
            
            logger.info("✅ Successfully recovered database using Python dump method")
            return True
            
        except Exception as e:
            logger.error(f"❌ Python dump recovery failed: {e}")
            return False
    
    def recover_partial_data(self):
        """Attempt to recover partial data from corrupted database"""
        logger.info("🔧 Attempting partial data recovery...")
        
        self.recovered_path = f"{self.db_path}.recovered_partial"
        
        try:
            source_conn = sqlite3.connect(self.db_path)
            dest_conn = sqlite3.connect(self.recovered_path)
            
            # Create the traffic table structure
            self.setup_database_schema(dest_conn)
            
            # Try to recover data from traffic table
            try:
                source_cursor = source_conn.cursor()
                source_cursor.execute("SELECT * FROM traffic ORDER BY id")
                
                dest_cursor = dest_conn.cursor()
                recovered_rows = 0
                
                while True:
                    try:
                        rows = source_cursor.fetchmany(1000)  # Process in batches
                        if not rows:
                            break
                        
                        for row in rows:
                            try:
                                dest_cursor.execute('''
                                    INSERT INTO traffic (id, timestamp, in_count, out_count, region_count, camera_name, ip)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', row)
                                recovered_rows += 1
                            except Exception as row_error:
                                logger.warning(f"⚠️  Skipped corrupted row: {row_error}")
                                continue
                        
                        dest_conn.commit()
                        
                    except Exception as batch_error:
                        logger.warning(f"⚠️  Batch processing error: {batch_error}")
                        break
                
                logger.info(f"✅ Recovered {recovered_rows} rows from traffic table")
                
            except Exception as table_error:
                logger.warning(f"⚠️  Could not recover traffic table: {table_error}")
            
            source_conn.close()
            dest_conn.close()
            
            return recovered_rows > 0
            
        except Exception as e:
            logger.error(f"❌ Partial recovery failed: {e}")
            return False
    
    def setup_database_schema(self, conn):
        """Setup the expected database schema"""
        cursor = conn.cursor()
        
        # Create traffic table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                in_count INTEGER NOT NULL,
                out_count INTEGER NOT NULL,
                region_count INTEGER NULL,
                camera_name TEXT NOT NULL,
                ip TEXT NULL
            )
        ''')
        
        # Create index for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_camera_name_timestamp 
            ON traffic (camera_name, timestamp)
        ''')
        
        conn.commit()
        cursor.close()
    
    def setup_wal_mode(self, db_path):
        """Setup WAL mode and optimize database settings"""
        logger.info("⚙️  Setting up WAL mode and optimizations...")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Set WAL mode
            cursor.execute("PRAGMA journal_mode=WAL")
            result = cursor.fetchone()[0]
            logger.info(f"✅ Journal mode set to: {result}")
            
            # Additional optimizations
            optimizations = [
                ("PRAGMA synchronous=NORMAL", "Synchronous mode"),
                ("PRAGMA cache_size=10000", "Cache size"),
                ("PRAGMA temp_store=memory", "Temp store"),
                ("PRAGMA mmap_size=268435456", "Memory map size (256MB)"),
            ]
            
            for pragma, description in optimizations:
                try:
                    cursor.execute(pragma)
                    logger.info(f"✅ {description} configured")
                except Exception as e:
                    logger.warning(f"⚠️  Could not set {description}: {e}")
            
            # Verify WAL mode is active
            cursor.execute("PRAGMA journal_mode")
            current_mode = cursor.fetchone()[0]
            
            conn.close()
            
            if current_mode.upper() == 'WAL':
                logger.info("✅ WAL mode successfully activated")
                return True
            else:
                logger.warning(f"⚠️  WAL mode not active. Current mode: {current_mode}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to setup WAL mode: {e}")
            return False
    
    def validate_recovered_database(self, db_path):
        """Validate the recovered database"""
        logger.info("🔍 Validating recovered database...")
        
        check_result = self.check_database_integrity(db_path)
        
        if not check_result['accessible']:
            logger.error(f"❌ Recovered database is not accessible: {check_result.get('error')}")
            return False
        
        if check_result['integrity'] != 'ok':
            logger.warning(f"⚠️  Database integrity check: {check_result['integrity']}")
        
        logger.info(f"✅ Database validation results:")
        logger.info(f"   - Tables: {check_result['table_count']}")
        logger.info(f"   - Traffic table exists: {check_result['traffic_table_exists']}")
        logger.info(f"   - Records in traffic table: {check_result['row_count']}")
        logger.info(f"   - Integrity: {check_result['integrity']}")
        
        return True
    
    def recover(self):
        """Main recovery process"""
        logger.info(f"🚀 Starting database recovery for: {self.db_path}")
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            logger.error(f"❌ Database file not found: {self.db_path}")
            return False
        
        # Initial database check
        initial_check = self.check_database_integrity(self.db_path)
        logger.info(f"📊 Initial database status: {initial_check}")
        
        if initial_check['accessible'] and initial_check['integrity'] == 'ok':
            logger.info("✅ Database appears to be healthy, setting up WAL mode...")
            return self.setup_wal_mode(self.db_path)
        
        # Create backup
        if not self.create_backup():
            logger.error("❌ Cannot proceed without backup")
            return False
        
        # Try different recovery methods
        recovery_methods = [
            self.recover_using_dump,
            self.recover_using_python_dump,
            self.recover_partial_data
        ]
        
        for method in recovery_methods:
            if method():
                # Validate recovered database
                if self.validate_recovered_database(self.recovered_path):
                    # Setup WAL mode on recovered database
                    if self.setup_wal_mode(self.recovered_path):
                        # Replace original with recovered
                        shutil.move(self.recovered_path, self.db_path)
                        logger.info("✅ Database recovery completed successfully!")
                        logger.info(f"📁 Original database backed up to: {self.backup_path}")
                        return True
                    else:
                        logger.warning("⚠️  Recovery successful but WAL setup failed")
                        return True
                else:
                    logger.error("❌ Recovered database validation failed")
        
        logger.error("❌ All recovery methods failed")
        return False

def main():
    """Main function"""
    print("🔧 SQLite Database Recovery Tool")
    print("=" * 50)
    
    # Get database path from command line argument or auto-detect
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        recovery = DatabaseRecovery(db_path)
        success = recovery.recover()
        
        if success:
            print("\n✅ Recovery completed successfully!")
            print(f"📊 Check the log file 'database_recovery.log' for details")
        else:
            print("\n❌ Recovery failed!")
            print("📊 Check the log file 'database_recovery.log' for details")
            sys.exit(1)
            
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
