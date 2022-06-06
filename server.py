from src.server import Server, Connection


class SlaveServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)

        self.master = None
        self.slaves = []

    def handle_connection(self, conn: Connection):
        if self.debug: print(f"[SERVER] Handling connection from {conn.addr}")
        identity = conn.recv_bytes()
        if identity == b'Master':
            conn.send_bytes(b'OK')
            self.master = conn
            if self.debug: print(f"[SERVER] Master connected from {conn.addr}")
            return
        if identity == b'Slave':
            conn.send_bytes(b'OK')
            self.slaves.append(conn)
            if self.debug: print(f"[SERVER] Slave connected from {conn.addr}")
            return
        conn.send_bytes(b'ERROR')
        if self.debug: print(f"[SERVER] Unknown identity from {conn.addr}")


if __name__ == "__main__":
    from config import Config

    server = SlaveServer(port=Config.SERVER_PORT, ip=Config.SERVER_IP, debug=True, start_listening=True)
