from src.server import Server, Connection
from threading import Thread
from pprint import pprint

class Master:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

class Slave:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

class SlaveServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)

        self.slaves = []
        self.master = None

    def handle_connection(self, conn: Connection):
        if self.debug: print(f"[SERVER] Handling connection from {conn.addr}")
        identity = conn.recv_bytes()
        if identity == b'Master':
            if self.master is None:
                conn.send_bytes(b'OK')
                master = Master(conn)
                master.connection.start()
                self.master = master
            else:
                conn.send_bytes(b'NOK')
                if self.debug: print(f"[SERVER] Master already connected")
            if self.debug: print(f"[SERVER] Master connected from {conn.addr}")
            return
        if identity == b'Slave':
            conn.send_bytes(b'OK')
            slave = Slave(conn)
            slave.connection.start()
            self.slaves.append(slave)
            if self.debug: print(f"[SERVER] Slave connected from {conn.addr}")
            return
        conn.send_bytes(b'ERROR')
        if self.debug: print(f"[SERVER] Unknown identity from {conn.addr}")

    def handle_message(self, conn: Connection, msg: dict):
        if self.debug: print(f"[SERVER] Handling message from {conn.addr}")
        pprint(msg)

if __name__ == "__main__":
    from config import Config
    import time

    server = SlaveServer(port=Config.SERVER_PORT, ip=Config.SERVER_IP, debug=True, start_listening=True)