from src.client import Client

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
    client.connect()