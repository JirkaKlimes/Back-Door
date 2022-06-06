from src.server import Server, Connection



class BotServer(Server):
    def __init__(self, port: int, ip: str = '', debug: bool = False, start_listening: bool = False) -> None:
        super().__init__(port, ip, debug, start_listening)
    
    def handle_connection(self, conn: Connection):
        print(f"handling connection from {conn.addr}")



if __name__ == "__main__":
    from config import Config

    server = BotServer(port=Config.SERVER_PORT, ip=Config.SERVER_IP, debug=True, start_listening=True)
