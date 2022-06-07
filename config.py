import socket

class Config:
    SERVER_IP = socket.gethostbyname(socket.gethostname())
    SERVER_PORT = 9999
    SERVER_ADDR = (SERVER_IP, SERVER_PORT)