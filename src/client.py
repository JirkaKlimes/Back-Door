import socket
import struct
import pickle
from cryptography.fernet import Fernet
from threading import Thread
from pprint import pprint


class Client:
    def  __init__(self, addr: tuple, debug: bool = False) -> None:
        self.addr = addr
        self.debug = debug
        self.connected = False
        self.recieving = False
    
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', 0))
        try:
            self.sock.connect(self.addr)
            if self.debug: print(f"[CLIENT] Connected to {self.addr}")
        except ConnectionRefusedError:
            if self.debug: print(f"[CLIENT] Connection to {self.addr} refused.")
            return False
        
        if self.handshake():
            if self.handle_connection():
                self.connected = True
                return True
        self.connected = False
        return False

    def handle_connection(self):
        pass

    def handshake(self) -> bool:
        msg = self.recv_bytes(decrypt=False)
        if not msg:
            if self.debug: print(f"[CLIENT] Failed to handshake with server")
            return False
        if self.debug: print(f"[CLIENT] Handshake with server successful")
        self.fernet = Fernet(msg)
        self.send_bytes(b'OK')
        return True

    def send_bytes(self, msg: bytes, encrypt: bool = True) -> None:
        msg = self.fernet.encrypt(msg) if encrypt else msg
        msg = struct.pack('>I', len(msg)) + msg
        try:
            self.sock.sendall(msg)
        except ConnectionResetError:
            self.connected = False
            if self.debug: print(f"[CLIENT] Disconected from {self.addr}")

    def recv_bytes(self, decrypt: bool = True) -> bytes:
        try:
            raw_msglen = self._recvall(4)
        except ConnectionResetError:
            self.connected = False
            if self.debug: print(f"[CLIENT] Disconected from {self.addr}")
            return None
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        msg = bytes(self._recvall(msglen))
        return self.fernet.decrypt(msg) if decrypt else msg

    def _recvall(self, n: int) -> bytearray:
        data = bytearray()
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data
    
    def send_dict(self, data: dict) -> None:
        pickled = pickle.dumps(data)
        self.send_bytes(pickled)

    def recieve_dict(self) -> dict:
        pickled = self.recv_bytes()
        if not pickled:
            return False
        msg = pickle.loads(pickled)
        return msg

    def reciever(self):
        while True:
            if not self.connected:
                self.recieving = False
                break
            msg = self.recieve_dict()
            self.handle_message(msg)
    
    def start_reciever(self):
        self.recieving = True
        Thread(target=self.reciever, daemon=True).start()
    
    def handle_message(self, msg):
        if self.debug: print(f"[CLIENT] Handling message from server")
        pprint(msg)

if __name__ == '__main__':
    from config import Config

    client = Client(Config.SERVER_ADDR, debug=True)
    client.connect()
