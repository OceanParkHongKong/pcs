import paramiko
import logging
import json
import os
import time
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RemoteMacExecutor:
    def __init__(self, hostname, username, password=None, key_filename=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.client = None

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_filename:
                self.client.connect(self.hostname, username=self.username, key_filename=self.key_filename)
            else:
                self.client.connect(self.hostname, username=self.username, password=self.password)
            
            logging.info(f"Successfully connected to {self.hostname}")
        except Exception as e:
            logging.error(f"Failed to connect to {self.hostname}: {str(e)}")
            raise

    def execute_command(self, command):
        if not self.client:
            raise Exception("Not connected. Call connect() first.")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                output = stdout.read().decode('utf-8').strip()
                logging.info(f"Command executed successfully: {command}")
                return output
            else:
                error = stderr.read().decode('utf-8').strip()
                logging.error(f"Command failed: {command}\nError: {error}")
                raise Exception(f"Command failed with exit status {exit_status}: {error}")
        except Exception as e:
            logging.error(f"Failed to execute command: {command}\nError: {str(e)}")
            raise

    def execute_script(self, script_content):
        if not self.client:
            raise Exception("Not connected. Call connect() first.")
        
        try:
            # Create a temporary file on the remote machine
            temp_script = f"/tmp/temp_script_{int(time.time())}.sh"
            self.execute_command(f"echo '{script_content}' > {temp_script}")
            self.execute_command(f"chmod +x {temp_script}")
            
            # Execute the script
            output = self.execute_command(f"bash {temp_script} &")
            
            # Clean up the temporary file
            self.execute_command(f"rm {temp_script}")
            
            return output
        except Exception as e:
            logging.error(f"Failed to execute script: {str(e)}")
            raise

    def disconnect(self):
        if self.client:
            self.client.close()
            logging.info(f"Disconnected from {self.hostname}")

class ProductionHost:
    def __init__(self, id, priority, hostname):
        self.id = id
        self.priority = priority
        self.hostname = hostname
        self.is_down = False

import fcntl
class BackupSystem:
    def __init__(self, backup_config, production_hosts):
        self.backup_config = backup_config
        self.production_hosts = sorted(production_hosts, key=lambda x: x.priority)
        self.backup_in_use = False
        self.backup_in_use_for = None
        self.lock_file = '/tmp/backup_system.lock'

    def check_and_failover(self, failed_host_id):
        with open(self.lock_file, 'w') as lock_file:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                failed_host = next((host for host in self.production_hosts if host.id == failed_host_id), None)
                if not failed_host:
                    logging.error(f"No production host found with ID {failed_host_id}")
                    return

                failed_host.is_down = True

                if self.backup_in_use:
                    current_backup_host = next((host for host in self.production_hosts if host.id == self.backup_in_use_for), None)
                    if current_backup_host and current_backup_host.priority < failed_host.priority:
                        logging.info(f"Backup already in use for higher priority host {current_backup_host.id}. Skipping failover for host {failed_host_id}")
                        return

                self.start_backup(failed_host)
                
            except IOError:
                logging.warning("Another process is currently handling a failover. Skipping this request.")
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def start_backup(self, failed_host):
        executor = RemoteMacExecutor(
            self.backup_config['hostname'],
            self.backup_config['username'],
            password=self.backup_config['password']
        )

        try:
            executor.connect()
            script_content = f"""
#!/bin/bash
echo "start backup People Count System for production host {failed_host.id}"
date
whoami
open /Applications/Docker.app
# cd ~/people_count_swift{failed_host.id}
cd ~/people_count_swift
pwd
# replace start_people_count.py with target host's start_people_count.py here?
source start_people_count_ALL.sh
            """
            result = executor.execute_script(script_content)
            logging.info(f"Backup started for production host {failed_host.id}")
            logging.info(f"Script output: {result}")
            
            self.backup_in_use = True
            self.backup_in_use_for = failed_host.id

        except Exception as e:
            logging.error(f"Failed to start backup for host {failed_host.id}: {str(e)}")
        finally:
            executor.disconnect()

def start_backup(failed_host_id=None):
    # Read configuration from JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'config.json')
    
    try:
        with open(json_path, 'r') as json_file:
            config = json.load(json_file)
        
        backup_config = config['backup_mac']
        production_hosts = [ProductionHost(host['id'], host['priority'], host['hostname']) 
                            for host in config['production_hosts']]
        
        backup_system = BackupSystem(backup_config, production_hosts)

        if failed_host_id is not None:
            backup_system.check_and_failover(int(failed_host_id))
        else:
            logging.warning("No failed host ID provided. No action taken.")

    except FileNotFoundError:
        logging.error(f"Error: {json_path} not found. Please create this file with the required configuration.")
    except json.JSONDecodeError:
        logging.error(f"Error: {json_path} is not a valid JSON file.")
    except KeyError as e:
        logging.error(f"Error: Missing key {e} in {json_path}. Make sure the file contains the required configuration.")
    except ValueError:
        logging.error(f"Error: Invalid failed_host_id. Please provide a valid integer.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backup System for Production Hosts')
    parser.add_argument('--failed-host-id', type=int, help='ID of the failed production host')
    args = parser.parse_args()

    start_backup(args.failed_host_id)
