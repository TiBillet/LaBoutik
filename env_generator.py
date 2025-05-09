#!/usr/bin/env python3
import os
import sys
import secrets
import string
from cryptography.fernet import Fernet
import argparse

def generate_random_string(length=50):
    """Generate a random string of fixed length"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_fernet_key():
    """Generate a Fernet key for encryption"""
    return Fernet.generate_key().decode('utf-8')

def read_env_example():
    """Read the env_example file and return its contents as a dictionary"""
    env_example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env_example')
    
    if not os.path.exists(env_example_path):
        print(f"Error: env_example file not found at {env_example_path}")
        sys.exit(1)
    
    env_vars = {}
    current_comment = ""
    
    with open(env_example_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Collect comments
            if line.startswith('#'):
                current_comment += line + "\n"
                continue
            
            # Process variable lines
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = {
                    'value': value.strip("'\""),
                    'comment': current_comment.strip()
                }
                current_comment = ""
    
    return env_vars

def generate_env_file(interactive=True, test_mode=False):
    """Generate a .env file based on user input or default values"""
    env_vars = read_env_example()
    new_env = {}
    
    # Set default values for required fields
    new_env['DJANGO_SECRET'] = generate_random_string()
    new_env['FERNET_KEY'] = generate_fernet_key()
    new_env['POSTGRES_PASSWORD'] = generate_random_string(20)
    
    if test_mode:
        # Set test values
        new_env['POSTGRES_USER'] = 'laboutik_user'
        new_env['POSTGRES_DB'] = 'laboutik'
        new_env['DOMAIN'] = 'laboutik.tibillet.localhost'
        new_env['FEDOW_URL'] = 'https://fedow.tibillet.localhost/'
        new_env['LESPASS_TENANT_URL'] = 'https://lespass.tibillet.localhost/'
        new_env['MAIN_ASSET_NAME'] = 'TestCoin'
        new_env['ADMIN_EMAIL'] = 'admin@example.com'
        new_env['TIME_ZONE'] = 'Europe/Paris'
        new_env['LANGUAGE_CODE'] = 'fr'
        new_env['DEBUG'] = '1'
        new_env['TEST'] = '1'
        new_env['DEMO'] = '1'
        new_env['DEMO_TAGID_CM'] = 'EE144CE8'
        new_env['DEMO_TAGID_CLIENT1'] = '41726643'
        new_env['DEMO_TAGID_CLIENT2'] = '93BD3684'
        new_env['DEMO_TAGID_CLIENT3'] = 'F18923CB'
    elif interactive:
        # Interactive mode - prompt for values
        print("TiBillet .env Generator")
        print("======================")
        print("Please provide the following information:")
        
        new_env['POSTGRES_USER'] = input("PostgreSQL username [laboutik_user]: ") or 'laboutik_user'
        new_env['POSTGRES_DB'] = input("PostgreSQL database name [laboutik]: ") or 'laboutik'
        new_env['DOMAIN'] = input("Domain (e.g., laboutik.tibillet.localhost): ")
        new_env['FEDOW_URL'] = input("Fedow URL (e.g., https://fedow.tibillet.localhost/): ")
        new_env['LESPASS_TENANT_URL'] = input("LesPass tenant URL (e.g., https://lespass.tibillet.localhost/): ")
        new_env['MAIN_ASSET_NAME'] = input("Main asset name (e.g., TestCoin): ")
        new_env['ADMIN_EMAIL'] = input("Admin email: ")
        new_env['TIME_ZONE'] = input("Time zone [Europe/Paris]: ") or 'Europe/Paris'
        new_env['LANGUAGE_CODE'] = input("Language code [fr]: ") or 'fr'
        
        debug = input("Enable debug mode? (0/1) [0]: ") or '0'
        new_env['DEBUG'] = debug
        
        if debug == '1':
            test = input("Enable test mode? (0/1) [0]: ") or '0'
            new_env['TEST'] = test
            
            demo = input("Enable demo mode? (0/1) [0]: ") or '0'
            new_env['DEMO'] = demo
            
            if demo == '1':
                new_env['DEMO_TAGID_CM'] = input("Demo tag ID CM [EE144CE8]: ") or 'EE144CE8'
                new_env['DEMO_TAGID_CLIENT1'] = input("Demo tag ID Client 1 [41726643]: ") or '41726643'
                new_env['DEMO_TAGID_CLIENT2'] = input("Demo tag ID Client 2 [93BD3684]: ") or '93BD3684'
                new_env['DEMO_TAGID_CLIENT3'] = input("Demo tag ID Client 3 [F18923CB]: ") or 'F18923CB'
    else:
        # Non-interactive mode with minimal defaults
        new_env['POSTGRES_USER'] = 'laboutik_user'
        new_env['POSTGRES_DB'] = 'laboutik'
        new_env['DOMAIN'] = 'laboutik.example.com'
        new_env['FEDOW_URL'] = 'https://fedow.example.com/'
        new_env['LESPASS_TENANT_URL'] = 'https://lespass.example.com/'
        new_env['MAIN_ASSET_NAME'] = 'MainCoin'
        new_env['ADMIN_EMAIL'] = 'admin@example.com'
        new_env['TIME_ZONE'] = 'Europe/Paris'
        new_env['LANGUAGE_CODE'] = 'fr'
        new_env['DEBUG'] = '0'
        new_env['TEST'] = '0'
        new_env['DEMO'] = '0'
    
    # Write the .env file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    with open(env_path, 'w') as f:
        f.write("##########################\n")
        f.write("# TiBillet / LaBoutik\n")
        f.write("# Generated .env file\n")
        f.write("##########################\n\n")
        
        for key in env_vars:
            if key in new_env:
                if env_vars[key]['comment']:
                    f.write(f"{env_vars[key]['comment']}\n")
                f.write(f"{key}='{new_env[key]}'\n\n")
            else:
                if env_vars[key]['comment']:
                    f.write(f"{env_vars[key]['comment']}\n")
                f.write(f"{key}='{env_vars[key]['value']}'\n\n")
    
    print(f".env file generated at {env_path}")
    return env_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a .env file for TiBillet/LaBoutik')
    parser.add_argument('--non-interactive', action='store_true', help='Run in non-interactive mode with default values')
    parser.add_argument('--test', action='store_true', help='Generate a test .env file')
    
    args = parser.parse_args()
    
    generate_env_file(
        interactive=not args.non_interactive,
        test_mode=args.test
    )