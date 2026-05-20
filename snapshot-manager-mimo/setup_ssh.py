#!/usr/bin/env python3
import paramiko
import os

# Server info
host = '10.242.10.5'
port = 22
username = 'root'
password = 'Iamadm1n!!'

# Read public key
with open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r') as f:
    public_key = f.read().strip()

print(f"Connecting to {host}...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, port=port, username=username, password=password, timeout=30)
    print("Connected!")

    # Create .ssh directory and add key
    cmd = f'mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo "{public_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
    print(f"Adding SSH key...")
    stdin, stdout, stderr = client.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()
    if error:
        print(f"Error: {error}")
    else:
        print(f"Success!")

    # Verify
    stdin, stdout, stderr = client.exec_command('cat ~/.ssh/authorized_keys')
    key_content = stdout.read().decode()
    print(f"Authorized keys contains {len(key_content.split())} keys")

    client.close()
    print("\nSSH key authentication configured!")
except Exception as e:
    print(f"Failed: {e}")
