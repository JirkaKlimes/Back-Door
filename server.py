from src.server import Server, Connection
from threading import Thread
from pprint import pprint
import hashlib
import json


class SlaveServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)

        self.slaves = []
        self.master = None
        self.commands = Commands(self)

        self.load_data()

    def load_data(self):
        with open('data.json', 'r') as f:
            self.data = json.load(f)
    
    def save_data(self):
        with open('data.json', 'w') as f:
            json.dump(self.data, f, indent=4, sort_keys=False)

    def _handle_master_connection(self, conn) -> bool:
        if self.data['master_password_hash'] == None:
            if self.debug: print(f"\tRegistering master")
            conn.send_bytes(b'REGISTER')
            passwd = conn.recv_bytes()
            if self.debug: print(f"\tClient sent password")
            self.data['master_password_hash'] = hashlib.sha256(passwd).hexdigest()
            self.save_data()
            conn.send_bytes(b'OK')
            conn.identity = 'master'
            self.master = conn
            if self.debug: print(f"\tMaster connected")
            if not self.debug: print(f"[SERVER] Master connected")
            return True
        else:
            conn.send_bytes(b'LOGIN')
            if self.debug: print(f"\tRequesting login")
            passwd = conn.recv_bytes()
            if not passwd:
                if self.debug: print(f"\tNo password sent")
                return False
            if self.debug: print(f"\tClient sent password")
            hashed = hashlib.sha256(passwd).hexdigest()
            if hashed == self.data['master_password_hash']:
                conn.send_bytes(b'OK')
                conn.identity = 'master'
                self.master = conn
                if self.debug: print(f"\tMaster connected")
                if not self.debug: print(f"[SERVER] Master connected")
                return True
            else:
                if self.debug: print(f"\tMaster sent wrong password")
                return False

    def handle_connection(self, conn: Connection):
        if self.debug: print(f"[SERVER] Handling connection from {conn.addr[0]}:{conn.addr[1]}")
        identity = conn.recv_bytes()
        if identity == b'Master':
            conn.send_bytes(b'OK')
            if self._handle_master_connection(conn):
                return
        elif identity == b'Slave':
            conn.send_bytes(b'OK')
            conn.identity = 'slave'
            self.slaves.append(conn)
            if self.debug: print(f"\tSlave connected")
            if not self.debug: print(f"[SERVER] Slave connected")
            return
        else:
            conn.send_bytes(b'ERROR')
            if self.debug: print(f"\tUnknown identity")
        conn.sock.close()

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
            getattr(self.commands, msg['command'])(msg)
        except AttributeError:
            print(f"[SERVER] Command {msg['command']} not implemented")

    def forward_command(self, msg: dict):
        msg.pop('type')
        recipients = msg.pop('recipients')
        if recipients == 'all':
            slaves = self.slaves
        else:
            slaves = [slave for slave in self.slaves if slave.addr in recipients]
        responses = self.paralle_wait(slaves, msg)
        if self.debug: print(f"[SERVER] Received responses")
        msg = {
            'responses': responses,
        }
        self.master.send_dict(msg)

    def forward_loop(self):
        while True:
            time.sleep(0.1)
            if self.master:
                if not self.master.connected: continue
                msg = self.master.recieve_dict()
                if not msg: continue
                if msg['type'] == 'slave_command':
                    self.forward_command(msg)
                    continue

                print(f"[SERVER] {msg['type']} not implemented.")
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

    def list(self, msg):
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

    print(f"[SERVER] listening on {server.addr[0]}:{server.addr[1]}")
    server.start_listener()
    server.forward_loop()