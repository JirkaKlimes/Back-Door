from src.server import Server, Connection
from threading import Thread
from pprint import pprint
import hashlib
from rich.console import Console


class SlaveServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)

        self.slaves = []
        self.master = None
        self.commands = Commands(self)
        self.master_passwd_hash = None
        self.console = Console()

    def start_listener(self) -> None:
        self.console.print(f"[SERVER] Listening on {self.addr[0]}:{self.addr[1]}")
        super().start_listener()

    def _handle_master_connection(self, conn) -> bool:
        if self.master_passwd_hash == None:
            self.console.print(f"\tRegistering master")
            conn.send_bytes(b'REGISTER')
            passwd = conn.recv_bytes()
            self.console.print(f"\tClient sent password")
            self.master_passwd_hash = hashlib.sha256(passwd).hexdigest()
            conn.send_bytes(b'OK')
            conn.identity = 'master'
            self.master = conn
            self.console.print(f"[green]\tMaster connected[/]")
            return True
        else:
            conn.send_bytes(b'LOGIN')
            self.console.print(f"\tRequesting login")
            passwd = conn.recv_bytes()
            self.console.print(f"\tClient sent password")
            hashed = hashlib.sha256(passwd).hexdigest()
            if hashed == self.master_passwd_hash:
                conn.send_bytes(b'OK')
                conn.identity = 'master'
                self.master = conn
                self.console.print(f"\t[green]Master connected[/]")
                return True
        self.console.print(f"\t[red]Master rejected[/]")
        return False

    def handle_connection(self, conn: Connection):
        self.console.print(f"[SERVER] Handling connection from {conn.addr[0]}:{conn.addr[1]}")
        identity = conn.recv_bytes()
        if identity == b'Master':
            conn.send_bytes(b'OK')
            if self._handle_master_connection(conn):
                return
        if identity == b'Slave':
            conn.send_bytes(b'OK')
            conn.identity = 'slave'
            self.slaves.append(conn)
            self.console.print(f"\t[green]Slave connected[/]")
            return
        conn.send_bytes(b'ERROR')
        self.console.print(f"\t[red]Unknown identity[/]")
        conn.close()

    def paralle_wait(self, slaves, msg):
        responses = [{'addr': slave.addr, 'response': None} for slave in slaves]
        def wait_for_respones(i, slave):
            slave.send_dict(msg)
            res = slave.recieve_dict()
            if res:
                responses[i]['response'] = res
        threads = []
        for i, slave in enumerate(slaves):
            t = Thread(target=wait_for_respones, args=(i, slave))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        return responses

    def execute_command(self, msg: dict):
        try:
            hasattr(self.commands, msg['command'])(msg)
        except AttributeError:
            self.console.print(f"[red][SERVER] Command {msg['command']} not implemented[/]")

    def forward_loop(self):
        while True:
            time.sleep(0.1)
            if self.master:
                if not self.master.connected: continue
                msg = self.master.recieve_dict()
                if not msg: continue
                if self.debug: pprint(msg)
                if msg['type'] == 'command':
                    self.execute_command(msg)
                    continue

                print(f"[red][SERVER] {msg['type']} not implemented.[/]")
                pprint(msg)

class Commands:
    def __init__(self, server) -> None:
        self.server = server
    
    def cmd(self, msg):
        slave_msg = {
            'type': 'command',
            'command': 'cmd',
            'command_string': msg['command_string'],
        }

        slaves = []
        for slave in self.server.slaves:
            if slave.addr in msg['slaves']:
                slaves.append(slave)
        responses = self.server.paralle_wait(slaves, slave_msg)
        msg = {
            'responses': responses,
        }
        self.server.master.send_dict(msg)

    def list(self):
        slaves = []
        request_msg = {
            'type': 'command',
            'command': 'pc_info',
        }
        responses = self.server.paralle_wait(self.server.slaves, request_msg)
        slaves = []
        for response in responses:
            if response['response']:
                data = response['response']
                data.update({'addr': response['addr']})
                slaves.append(data)
        msg = {
            'slaves': slaves,
            }
        self.server.master.send_dict(msg)


if __name__ == "__main__":
    from config import Config
    import time

    server = SlaveServer(port=Config.SERVER_PORT, ip=Config.SERVER_IP)

    server.master_passwd_hash = Config.MASTER_PASSWORD_HASH

    server.start_listener()
    server.forward_loop()