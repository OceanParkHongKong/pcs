import json
import hashlib
import os
import sys

def create_admin_user(username, password):
    users_file = 'users.json'
    
    # Load existing users if file exists
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        users = {}
    
    # Create or update admin user
    users[username] = {
        'password_hash': hashlib.sha256(password.encode()).hexdigest(),
        'role': 'admin'
    }
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"Admin user '{username}' created/updated successfully")

def update_user_password(username, new_password):
    users_file = 'users.json'
    
    # Check if users file exists
    if not os.path.exists(users_file):
        print(f"Error: Users file not found")
        return False
    
    # Load existing users
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    # Check if user exists
    if username not in users:
        print(f"Error: User '{username}' not found")
        return False
    
    # Update password
    users[username]['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"Password for user '{username}' updated successfully")
    return True

def list_users():
    users_file = 'users.json'
    
    # Check if users file exists
    if not os.path.exists(users_file):
        print("No users found - users file does not exist")
        return False
    
    # Load existing users
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    if not users:
        print("No users found in the system")
        return False
    
    print("\nExisting Users:")
    print("-" * 20)
    for username, user_data in users.items():
        role = user_data.get('role', 'user')
        print(f"Username: {username}")
        print(f"Role: {role}")
        print("-" * 20)
    
    return True

def delete_user(username):
    users_file = 'users.json'
    
    # Check if users file exists
    if not os.path.exists(users_file):
        print(f"Error: Users file not found")
        return False
    
    # Load existing users
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    # Check if user exists
    if username not in users:
        print(f"Error: User '{username}' not found")
        return False
    
    # Delete user
    del users[username]
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=4)
    
    print(f"User '{username}' deleted successfully")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Create admin: python user_management.py add <username> <password>")
        print("  Update password: python user_management.py update <username> <password>")
        print("  List users: python user_management.py list")
        print("  Delete user: python user_management.py delete <username>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_users()
    elif command == "delete":
        if len(sys.argv) != 3:
            print("Error: delete command requires username")
            sys.exit(1)
        username = sys.argv[2]
        delete_user(username)
    elif command in ["add", "update"]:
        if len(sys.argv) != 4:
            print(f"Error: {command} command requires username and password")
            sys.exit(1)
        username = sys.argv[2]
        password = sys.argv[3]
        
        if command == "add":
            create_admin_user(username, password)
        else:
            update_user_password(username, password)
    else:
        print("Invalid command. Use 'add', 'update', 'list', or 'delete'")
        sys.exit(1) 