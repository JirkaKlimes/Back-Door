from src.client import Client

class BotClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)


if __name__ == "__main__":
    from config import Config

    client = BotClient(addr=Config.SERVER_ADDR, debug=True)
    client.connect()