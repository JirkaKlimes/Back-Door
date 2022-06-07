from src.server import Server, Connection
from threading import Thread
from pprint import pprint
import hashlib


class SlaveServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)

        self.slaves = []
        self.master = None
        self.commands = Commands(self)
        self.master_passwd_hash = None
    
    def validate_passwd(self, byte_passwd: bytes) -> bool:
        hashed = hashlib.sha256(byte_passwd).hexdigest()
        return hashed == self.master_passwd_hash

    def handle_connection(self, conn: Connection):
        if self.debug: print(f"[SERVER] Handling connection from {conn.addr}")
        identity = conn.recv_bytes()
        if identity == b'Master':
            conn.send_bytes(b'OK')
            byte_passwd = conn.recv_bytes()
            if self.validate_passwd(byte_passwd):
                conn.send_bytes(b'OK')
                conn.identity = 'master'
                self.master = conn
                if self.debug: print(f"[SERVER] Master connected from {conn.addr}")
            else:
                conn.send_bytes(b'NOK')
                conn.close()
                if self.debug: print(f"[SERVER] Master rejected from {conn.addr}")
            return
        if identity == b'Slave':
            conn.send_bytes(b'OK')
            conn.identity = 'slave'
            self.slaves.append(conn)
            if self.debug: print(f"[SERVER] Slave connected from {conn.addr}")
            return
        conn.send_bytes(b'ERROR')
        if self.debug: print(f"[SERVER] Unknown identity from {conn.addr}")

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

    def forward_loop(self):
        while True:
            time.sleep(0.1)
            if self.master:
                if not self.master.connected: continue
                msg = self.master.recieve_dict()
                if not msg: continue
                if self.debug: pprint(msg)
                if msg['type'] == 'command':
                    if msg['command'] == 'list':
                        self.commands.list()
                        continue
                    
                    if msg['command'] == 'cmd':
                        self.commands.cmd(msg)
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

    server = SlaveServer(port=Config.SERVER_PORT, ip=Config.SERVER_IP, debug=True)

    server.master_passwd_hash = Config.MASTER_PASSWORD_HASH

    server.start_listener()
    server.forward_loop()