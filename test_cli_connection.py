#!/usr/bin/env python3
"""Quick test script for NSO CLI connection."""
import sys
sys.path.insert(0, '.')

from agents.compliance.tools.connectors.nso_connector_cli.nso_client_cli import NSOCLIClient
from config.config import NSO_HOST, NSO_CLI_PORT, NSO_USERNAME, NSO_CLI_PROTOCOL

NSO_HOST = "localhost"
print('=' * 60)
print(' NSO CLI Connection Test')
print('=' * 60)
print(f'NSO Host: {NSO_HOST}')
print(f'NSO CLI Port: {NSO_CLI_PORT}')
print(f'Protocol: {NSO_CLI_PROTOCOL}')
print(f'Username: {NSO_USERNAME}')
print()

try:
    print('Creating NSO CLI client...')
    client = NSOCLIClient()
    
    print('Connecting to NSO via CLI (SSH)...')
    client.connect()
    print('✅ CONNECTION SUCCESSFUL!')
    
    print()
    print('Running test command: show packages')
    result = client.execute_read('show packages')
    print('-' * 40)
    print(result[:1000] if len(result) > 1000 else result)
    
    print()
    print('Running: show devices list')
    result = client.execute_read('show devices list')
    print('-' * 40)
    print(result)
    
    client.disconnect()
    print()
    print('✅ All CLI tests passed!')
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
