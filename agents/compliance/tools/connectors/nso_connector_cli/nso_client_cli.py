import logging
import os
import tempfile
import yaml
from typing import List, Optional
from pyats.topology import loader
from agents.compliance.tools.connectors.nso_connector_cli.exeptions import NSOCLICommandError, NSOCLIConnectionError
from config.config import (
    NSO_HOST,
    NSO_CLI_PORT,
    NSO_USERNAME,
    NSO_PASSWORD,
    NSO_CLI_PROTOCOL,
    NSO_HOST_DOWNLOAD
)

# Initialize the requested logger
logger = logging.getLogger("devnet.compliance.tools.nso_client_cli")


def generate_testbed_from_env() -> str:
    """
    Generates a pyATS testbed YAML file from environment variables.
    
    Uses configuration from config/config.py:
        NSO_HOST: NSO server IP address (default: 127.0.0.1)
        NSO_CLI_PORT: NSO SSH port (default: 2024)
        NSO_USERNAME: NSO username (default: admin)
        NSO_PASSWORD: NSO password (default: admin)
        NSO_PROTOCOL: Connection protocol (default: ssh)
        NSO_DEFAULT_USERNAME: Default testbed username (default: admin)
        NSO_DEFAULT_PASSWORD: Default testbed password (default: cisco123)
        NSO_ENABLE_PASSWORD: Enable password (default: cisco123)
    
    Returns:
        Path to the generated temporary testbed YAML file.
    """
    # Build testbed dictionary using config values
    testbed_dict = {
        "testbed": {
            "name": "NSO-Testbed",
            "credentials": {
                "default": {
                    "username": "admin",
                    "password": "cisco123"
                },
                "enable": {
                    "password": "cisco123"
                }
            }
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
                        "ssh_options": "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
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
    
    # Write to a temporary file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.yaml', 
        prefix='nso_testbed_',
        delete=False
    )
    yaml.dump(testbed_dict, temp_file, default_flow_style=False)
    temp_file.close()
    
    logger.info(f"Generated testbed from environment variables: {temp_file.name}")
    logger.debug(f"NSO connection: {NSO_CLI_PROTOCOL}://{NSO_USERNAME}@{NSO_HOST}:{NSO_CLI_PORT}")
    
    return temp_file.name


class NSOCLIClient:
    """Handles low-level pyATS communication with Cisco NSO."""

    def __init__(self, testbed_path: Optional[str] = None, device_name: str = "nso"):
        """
        Initialize NSO Client.
        
        Args:
            testbed_path: Path to testbed YAML file. If None, generates from environment variables.
            device_name: Name of the NSO device in the testbed (default: "nso")
        """
        # If no testbed path provided, generate from environment variables
        if testbed_path is None:
            testbed_path = generate_testbed_from_env()
            self._temp_testbed = True
        elif not os.path.exists(testbed_path):
            logger.warning(f"Testbed file not found: {testbed_path}. Generating from environment variables.")
            testbed_path = generate_testbed_from_env()
            self._temp_testbed = True
        else:
            self._temp_testbed = False
        
        self._testbed_path = testbed_path
        self.testbed = loader.load(testbed_path)
        try:
            self.device = self.testbed.devices[device_name]
        except KeyError:
            raise ValueError(f"Device '{device_name}' not found in testbed.")
        
        self._connected = False

    def connect(self):
        """Ensures the device is connected."""
        if not self._connected:
            logger.info(f"Establishing connection to NSO device: {self.device.name}")
            try:
                self.device.connect(log_stdout=False)
                self._connected = True
            except Exception as e:
                logger.error(f"Failed to connect to NSO: {e}")
                raise NSOCLIConnectionError(str(e))

    def disconnect(self):
        """Gracefully closes the connection."""
        if self._connected:
            logger.info("Disconnecting from NSO.")
            self.device.disconnect()
            self._connected = False
        
        # Cleanup temporary testbed file
        if self._temp_testbed and os.path.exists(self._testbed_path):
            try:
                os.unlink(self._testbed_path)
                logger.debug(f"Cleaned up temporary testbed: {self._testbed_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp testbed: {e}")

    def execute_read(self, command: str) -> str:
        """Executes an operational mode command."""
        self.connect()
        logger.debug(f"Executing operational command: {command}")
        return self.device.execute(command)

    def execute_config_dry_run(self, commands: List[str]) -> str:
        """
        Executes configuration commands in dry-run mode (preview only, no commit).
        
        Follows the NSO J-style CLI workflow:
        1. config - enter configuration mode terminal
        2. Execute set commands
        3. top - return to config root
        4. commit dry-run outformat cli - preview changes
        5. exit + no - discard uncommitted changes
        
        Args:
            commands: List of configuration commands to execute
        
        Returns:
            Dry-run output showing what would be configured (CLI diff format)
        """
        from unicon.eal.dialogs import Dialog, Statement
        
        self.connect()
        logger.info(f"Starting DRY-RUN config transaction with {len(commands)} commands")
        
        try:
            # Build dialog to handle the "Uncommitted changes" prompt
            # When exiting config mode with uncommitted changes, NSO asks:
            # "Uncommitted changes found, commit them? [yes/no/CANCEL]"
            uncommitted_dialog = Dialog([
                Statement(
                    pattern=r'Uncommitted changes found.*\[yes/no/CANCEL\]',
                    action='sendline(no)',
                    loop_continue=True
                ),
                Statement(
                    pattern=r'commit them\?.*\[yes,no\]',
                    action='sendline(no)',
                    loop_continue=True
                )
            ])
            
            # Step 1: Enter config mode
            self.device.execute("config")
            logger.debug("Entered config mode")
            
            # Step 2: Execute all set commands
            for cmd in commands:
                self.device.execute(cmd)
                logger.debug(f"Executed: {cmd}")
            
            # Step 3: Go to top level
            self.device.execute("top")
            
            # Step 4: Run commit dry-run to get the preview
            dry_run_output = self.device.execute("commit dry-run outformat cli")
            logger.debug(f"Dry-run output:\n{dry_run_output}")
            
            # Step 5: Exit config mode WITHOUT committing
            # Use dialog to handle the confirmation prompt
            self.device.execute("exit", reply=uncommitted_dialog)
            logger.debug("Exited config mode (changes discarded)")
            
            return dry_run_output
            
        except Exception as e:
            logger.exception("Unexpected error during NSO dry-run configuration.")
            # Try to recover and exit config mode
            try:
                self.device.execute("exit", timeout=5)
            except Exception:
                pass
            raise NSOCLICommandError(str(e))

    def execute_config(self, commands: List[str], dry_run: bool = False) -> str:
        """
        Executes configuration commands using NSO's configure service.
        
        Args:
            commands: List of configuration commands to execute
            dry_run: If True, performs 'commit dry-run outformat cli' to preview changes without applying
        
        Returns:
            Command output string (for dry_run: CLI diff format showing what would change)
        """
        if dry_run:
            return self.execute_config_dry_run(commands)
        
        self.connect()
        logger.info(f"Starting config transaction with {len(commands)} commands. dry_run={dry_run}")
        
        try:
            # Use unicon's configure service - it handles config mode entry/exit properly
            # Join commands with newlines for bulk execution
            output = self.device.configure("\n".join(commands))
            logger.debug(f"Config Output: {output}")
            return output
        except Exception as e:
            logger.exception("Unexpected error during NSO configuration.")
            raise NSOCLICommandError(str(e))