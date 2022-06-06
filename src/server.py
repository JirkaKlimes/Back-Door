import socket
from threading import Thread
import struct
import pickle
from cryptography.fernet import Fernet


class Connection:
    def __init__(self, addr, sock, server) -> None:
        self.addr = addr
        self.sock = sock
        self.server = server

        self.connected = True
    
    def send_bytes(self, msg: bytes, encrypt: bool = True) -> bool:
        msg = self.server.fernet.encrypt(msg) if encrypt else msg
        msg = struct.pack('>I', len(msg)) + msg
        try:
            self.sock.sendall(msg)
        except ConnectionResetError:
            if self.server.debug: print(f"[SERVER] {self.addr} disconnected.")
            self.connected = False
            return False
        return True

    def recv_bytes(self, decrypt: bool = True) -> bytes:
        try:
            raw_msglen = self._recvall(4)
        except ConnectionResetError:
            if self.server.debug: print(f"[SERVER] {self.addr} disconnected.")
            self.connected = False
            return None
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        msg = bytes(self._recvall(msglen))
        return self.server.fernet.decrypt(msg) if decrypt else msg

    def _recvall(self, n: int) -> bytearray:
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
            except ConnectionResetError:
                if self.server.debug: print(f"[SERVER] {self.addr} disconnected.")
                self.connected = False
                return None
            if not packet:
                return None
            data.extend(packet)
        return data

    def send_dict(self, data: dict) -> bool:
        pickled = pickle.dumps(data)
        res = self.send_bytes(pickled)
        return res

    def recieve_dict(self) -> dict:
        pickled = self.recv_bytes()
        if not pickled:
            return None
        msg = pickle.loads(pickled)
        return msg

class Server:
    def __init__(self, port: int, ip: str = '', debug: bool = False, start: bool = False) -> None:
        self.addr = (ip, port)
        self.debug = debug

        self._create_sock()

        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)

        self.connections = []
        if start: self.start()

    def handshake(self, conn: Connection) -> None:
        conn.send_bytes(self.encryption_key, encrypt=False)
        status = conn.recv_bytes()
        if status == b'OK':
            self.connections.append(conn)
            if self.debug: print(f"[SERVER] {conn.addr} connected")
        else:
            if self.debug: print(f"[SERVER] {conn.addr} failed to connect")

    def _create_sock(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(self.addr)
        sock.listen()
        self.sock = sock
        if self.debug: print(f"[SERVER] Socket created")
    
    def _listener(self) -> None:
        if self.debug: print(f"[SERVER] Listening on {self.addr}")
        while True:
            conn, addr = self.sock.accept()
            new_connection = Connection(addr, conn, self)
            if self.debug: print(f"[SERVER] Connection from {new_connection.addr}")
            self.handshake(new_connection)

    def start(self) -> None:
        self.listener_thread = Thread(target=self._listener, daemon=True)
        self.listener_thread.start()


if __name__ == "__main__":
    from config import Config
    
    server = Server(Config.SERVER_PORT, Config.SERVER_IP, debug=True, start=True)
    input()