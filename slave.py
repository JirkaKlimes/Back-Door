from regex import P
from src.client import Client
from pprint import pprint
from threading import Thread

class SlaveClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)

    def handle_connection(self) -> bool:
        if self.debug: print(f"[CLIENT] Sending identity to server")
        self.send_bytes(b'Slave')
        if self.recv_bytes() == b'OK':
            if self.debug: print(f"[CLIENT] Server accepted identity")
            return True
        return False


if __name__ == "__main__":
    from config import Config

    client = SlaveClient(addr=Config.SERVER_ADDR, debug=True)

    while True:
        if not client.connected:
            client.connect()
            continue
        if not client.recieving:
            client.start_reciever()
        
        msg = {
            'type': 'test',
            'data': input()
        }
        client.send_dict(msg)