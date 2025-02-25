"""Integration tests for the valory/counter skill."""
import subprocess
from pathlib import Path
from aea.test_tools.test_cases import AEATestCaseMany
AGENT_NAME = 'asylum_abci_app'
AUTHOR = 'zarathustra'
VERSION = '0.1.0'
DEFAULT_LAUNCH_TIMEOUT = 10
LAUNCH_SUCCEED_MESSAGE = 'Start processing'

class TestAgentLaunch(AEATestCaseMany):
    """Test that the Agent launches."""
    IS_LOCAL = True
    capture_log = True
    cli_log_options = ['-v', 'DEBUG']
    package_registry_src_rel = Path(__file__).parent.parent.parent.parent.parent

    def test_run(self) -> None:
        """Run the ABCI skill."""
        agent_name = 'base'
        self.fetch_agent(f'{AUTHOR}/{AGENT_NAME}:{VERSION}', agent_name, is_local=self.IS_LOCAL)
        self.set_agent_context(agent_name)
        self.generate_private_key('ethereum')
        self.add_private_key('ethereum', 'ethereum_private_key.txt')
        self.invoke('install')
        process = self.run_agent()
        is_running = self.is_running(process)
        assert is_running, 'AEA not running within timeout!'

    @classmethod
    def is_running(cls, process: subprocess.Popen, timeout: int=DEFAULT_LAUNCH_TIMEOUT) -> bool:
        """Check if the AEA is launched and running (ready to process messages)."""
        missing_strings = cls.missing_from_output(process, (LAUNCH_SUCCEED_MESSAGE,), timeout, is_terminating=False)
        return missing_strings == []