#!/usr/bin/env python3
"""Debug test script for NSO CLI connection with verbose output."""
import sys
import os
import tempfile
import yaml
import logging

# Enable verbose logging
logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, '.')

from config.config import NSO_HOST, NSO_CLI_PORT, NSO_USERNAME, NSO_PASSWORD, NSO_CLI_PROTOCOL

print('=' * 60)
print(' NSO CLI Connection Debug Test')
print('=' * 60)
print(f'NSO Host: {NSO_HOST}')
print(f'NSO CLI Port: {NSO_CLI_PORT}')
print(f'Protocol: {NSO_CLI_PROTOCOL}')
print(f'Username: {NSO_USERNAME}')
print(f'Password: {NSO_PASSWORD}')
print()

# Create testbed with explicit settings
testbed_dict = {
    "testbed": {
        "name": "NSO-Testbed"
    },
    "devices": {
        "nso": {
            "os": "nso",
            "type": "nso", 
            "platform": "nso",
            "connections": {
                "defaults": {
                    "class": "unicon.Unicon"
                },
                "cli": {
                    "protocol": NSO_CLI_PROTOCOL,
                    "ip": NSO_HOST,
                    "port": NSO_CLI_PORT,
                    "ssh_options": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                    "arguments": {
                        "connection_timeout": 120,
                        "login_timeout": 60,
                        "init_exec_commands": [],
                        "init_config_commands": []
                    }
                }
            },
            "credentials": {
                "default": {
                    "username": NSO_USERNAME,
                    "password": NSO_PASSWORD
                }
            }
        }
    }
}

# Write testbed
temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', prefix='nso_testbed_debug_', delete=False)
yaml.dump(testbed_dict, temp_file, default_flow_style=False)
temp_file.close()

print(f"Generated testbed: {temp_file.name}")
print("-" * 40)
print("Testbed content:")
with open(temp_file.name) as f:
    print(f.read())
print("-" * 40)

try:
    from pyats.topology import loader
    print("Loading testbed...")
    testbed = loader.load(temp_file.name)
    device = testbed.devices["nso"]
    
    print(f"Device: {device.name}")
    print(f"Device OS: {device.os}")
    print(f"Connections: {list(device.connections.keys())}")
    
    print()
    print("=" * 60)
    print("Attempting connection with log_stdout=True for debug...")
    print("=" * 60)
    device.connect(log_stdout=True)
    
    print()
    print("✅ CONNECTION SUCCESSFUL!")
    
    print()
    print("Running: show packages")
    result = device.execute("show packages")
    print(result)
    
    device.disconnect()
    print()
    print("✅ All CLI tests passed!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)
