#!/usr/bin/env python3
"""
VPP Stats Socket Finder
Finds and tests VPP stats socket locations
"""

import os
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def find_vpp_stats_socket():
    """Find VPP stats socket in common locations"""
    
    possible_locations = [
        "/run/vpp/stats.sock",
        "/var/run/vpp/stats.sock",
        "/dev/shm/vpp/stats.sock",
        "/run/vpp-stats.sock",
        "/tmp/vpp/stats.sock",
    ]
    
    logging.info("🔍 Searching for VPP stats socket...")
    logging.info("="*70)
    
    found_sockets = []
    
    for location in possible_locations:
        if os.path.exists(location):
            stat_info = os.stat(location)
            logging.info(f"✓ FOUND: {location}")
            logging.info(f"  Size: {stat_info.st_size} bytes")
            logging.info(f"  Permissions: {oct(stat_info.st_mode)[-3:]}")
            found_sockets.append(location)
        else:
            logging.debug(f"✗ Not found: {location}")
    
    if not found_sockets:
        logging.warning("❌ No stats socket found in common locations")
        logging.info("\n🔍 Searching entire /run and /var/run...")
        
        # Search in /run directory
        try:
            result = subprocess.run(
                ['find', '/run', '/var/run', '-name', '*stats.sock*', '2>/dev/null'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                found = result.stdout.strip().split('\n')
                logging.info(f"Found via search: {found}")
                found_sockets.extend(found)
        except:
            pass
    
    return found_sockets

def check_vpp_stats_config():
    """Check VPP configuration for stats socket"""
    logging.info("\n📋 Checking VPP configuration...")
    logging.info("="*70)
    
    config_files = [
        "/etc/vpp/startup.conf",
        "/usr/local/etc/vpp/startup.conf",
        "/etc/vpp.conf",
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            logging.info(f"✓ Found config: {config_file}")
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'statseg' in content or 'stats' in content:
                        logging.info("  Stats configuration found:")
                        for line in content.split('\n'):
                            if 'stat' in line.lower() and not line.strip().startswith('#'):
                                logging.info(f"    {line.strip()}")
            except Exception as e:
                logging.warning(f"  Could not read: {e}")
    
def check_vpp_process():
    """Check if VPP is running and get info"""
    logging.info("\n🔄 Checking VPP process...")
    logging.info("="*70)
    
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        vpp_processes = [line for line in result.stdout.split('\n') if 'vpp' in line.lower()]
        
        if vpp_processes:
            logging.info("✓ VPP is running:")
            for proc in vpp_processes:
                logging.info(f"  {proc}")
        else:
            logging.warning("❌ VPP process not found!")
            
    except Exception as e:
        logging.error(f"Error checking processes: {e}")

def test_vpp_cli():
    """Test VPP CLI for stats info"""
    logging.info("\n🎯 Testing VPP CLI for stats info...")
    logging.info("="*70)
    
    commands = [
        "show stats segment",
        "show run | inc stats",
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(
                ['vppctl', cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logging.info(f"\n$ vppctl {cmd}")
                logging.info(result.stdout)
            else:
                logging.warning(f"Command failed: {cmd}")
                if result.stderr:
                    logging.warning(f"Error: {result.stderr}")
        except Exception as e:
            logging.warning(f"Could not run vppctl: {e}")
            break

def create_stats_socket_workaround():
    """Provide workaround instructions"""
    logging.info("\n💡 SOLUTIONS:")
    logging.info("="*70)
    
    logging.info("""
1. Check VPP startup configuration:
   sudo cat /etc/vpp/startup.conf
   
   Look for 'statseg' section. Should have:
   statseg {
       socket-name /run/vpp/stats.sock
   }

2. If missing, add to /etc/vpp/startup.conf:
   statseg {
       socket-name /run/vpp/stats.sock
   }

3. Restart VPP:
   sudo systemctl restart vpp

4. Or manually create directory:
   sudo mkdir -p /run/vpp
   sudo chmod 777 /run/vpp

5. Check if stats are disabled in VPP:
   vppctl show stats segment

6. Alternative: Use shared memory stats (older VPP versions):
   Check /dev/shm/vpp/* for any stats files
""")

def generate_fixed_code(socket_path):
    """Generate corrected Python code"""
    logging.info(f"\n✅ FIXED CODE for socket: {socket_path}")
    logging.info("="*70)
    
    code = f'''
# Use this in your connection function:

from vpp_papi.vpp_papi import VPPApiClient
from vpp_papi.vpp_stats import VPPStats

def get_vpp_connection():
    """Connect to VPP with correct stats socket"""
    global vpp, vpp_stats
    try:
        # Connect to VPP API
        vpp = VPPApiClient(server_address="/run/vpp/api.sock")
        vpp.connect("vpp-firewall-gui")
        logging.info("✓ Connected to VPP API")
        
        # Connect to VPP Stats with CORRECT PATH
        vpp_stats = VPPStats(socketname="{socket_path}")
        logging.info("✓ Connected to VPP Stats segment")
        
        vpp.vpp_stats = vpp_stats
        return vpp
    except Exception as e:
        logging.error(f"Failed to connect: {{e}}")
        return None
'''
    
    print(code)

def main():
    """Main function"""
    print("\n" + "="*70)
    print("VPP STATS SOCKET DIAGNOSTIC TOOL")
    print("="*70 + "\n")
    
    # Check VPP process
    check_vpp_process()
    
    # Find stats socket
    found_sockets = find_vpp_stats_socket()
    
    # Check VPP config
    check_vpp_stats_config()
    
    # Test VPP CLI
    test_vpp_cli()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if found_sockets:
        print(f"✓ Found {len(found_sockets)} stats socket(s):")
        for sock in found_sockets:
            print(f"  • {sock}")
        
        # Generate fixed code
        generate_fixed_code(found_sockets[0])
    else:
        print("❌ No stats socket found!")
        print("\nPossible reasons:")
        print("  1. VPP stats segment not enabled in startup.conf")
        print("  2. VPP not running")
        print("  3. Socket in non-standard location")
        
        create_stats_socket_workaround()
    
    print("\n" + "="*70)
    print("RECOMMENDED NEXT STEPS:")
    print("="*70)
    print("""
1. Run: sudo vppctl show stats segment
2. Add statseg config to /etc/vpp/startup.conf if missing
3. Restart VPP: sudo systemctl restart vpp
4. Run this script again to verify

For immediate use, your CLI method works fine!
Stats API is optional (just faster).
""")

if __name__ == "__main__":
    main()