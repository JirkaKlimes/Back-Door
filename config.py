import socket

class Config:
    SERVER_IP = socket.gethostbyname(socket.gethostname())
    SERVER_PORT = 9999
    SERVER_ADDR = (SERVER_IP, SERVER_PORT)

    MASTER_PASSWORD = 'master_password'
    MASTER_PASSWORD_HASH = 'f0d7d94e52fde6905c62ddcb6a5b415e92e2a4989d20f49c93021ef03c67c2bb'