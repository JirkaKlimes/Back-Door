from src.client import Client
import os
import sys

class MasterClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)

        self.commands = Commands(self)

        self.available_slaves = []
        self.selected_slaves = []

        self.password = None

    def handle_connection(self) -> bool:
        if self.debug: print(f"[CLIENT] Sending identity to server")
        self.send_bytes(b'Master')
        if self.recv_bytes() == b'OK':
            byte_passwd = self.password.encode('utf-8')
            if self.debug: print(f"[CLIENT] Sending password to server")
            self.send_bytes(byte_passwd)
            if self.recv_bytes() == b'OK':
                if self.debug: print(f"[CLIENT] Server accepted identity")
                return True
        return False

    def show_prompt(self) -> str:
        if len(self.selected_slaves) > 0:
            selected = ""
            for i, slave in enumerate(self.selected_slaves):
                if i == 0:
                    selected += f"┌[{slave['username']}@{slave['hostname']}]\n"
                else:
                    selected += f"├[{slave['username']}@{slave['hostname']}]\n"
            print(selected, end="")
            command = input("└ $ ")
        else:
            command = input("$ ")
        return command

    def pop_slave(self, addr):
        slaves = []
        removed = None
        for slave in self.selected_slaves:
            if slave['addr'] != addr:
                slaves.append(slave)
            else:
                removed = slave
        self.selected_slaves = slaves
        return removed

    def execute(self, command):
        first_arg = command.split()[0]
        try:
            getattr(self.commands, first_arg)(command)
        except AttributeError:
            print(f"Unknown command.\n\t-> {command}")

    def command_loop(self):
        while True:
            if not self.connected:
                self.connect()
                continue

            command = self.show_prompt()
            self.execute(command)


class Commands:
    def __init__(self, master):
        self.master = master

    def list(self, command):
        msg = {
            'type': 'command',
            'command': 'list',
            }
        self.master.send_dict(msg)
        print('sent')
        msg = self.master.recieve_dict()
        print('recieved')
        if not msg: print("No response from server.")
        index_len = 5
        username_len = 10
        hostname_len = 19
        os_version_len = 14
        addr_len = 22
        print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        print(f"|{'INDEX'.center(index_len)}|{'USERNAME'.center(username_len)}|{'HOSTNAME'.center(hostname_len)}|{'OS VER'.center(os_version_len)}|{'ADDRESS'.center(addr_len)}|")
        print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        slaves = msg['slaves']
        for i, slave in enumerate(slaves):
            slave.update({'index': i})
            address = f"{slave['addr'][0]}:{slave['addr'][1]}"
            print(f"|{str(i).center(index_len)}|{slave['username'].center(username_len)}|{slave['hostname'].center(hostname_len)}|{slave['os_version'].center(os_version_len)}|{address.center(addr_len)}|")
            print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")

        self.master.available_slaves = slaves

    def select(self, command):
        command = command.split()[1:]
        if 'all' in command:
            self.master.selected_slaves = [slave for slave in self.master.available_slaves]
            return
        try:
            indexes = [int(i) for i in command]
        except ValueError:
            print("Invalid index.")
            return
        slaves = [slave for slave in self.master.available_slaves if slave['index'] in indexes]
        if not slaves:
            print("Invalid index.")
            return
        self.master.selected_slaves = slaves

    def selected(self, command):
        index_len = 5
        username_len = 10
        hostname_len = 19
        os_version_len = 14
        addr_len = 22
        print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        print(f"|{'INDEX'.center(index_len)}|{'USERNAME'.center(username_len)}|{'HOSTNAME'.center(hostname_len)}|{'OS VER'.center(os_version_len)}|{'ADDRESS'.center(addr_len)}|")
        print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        for slave in master.selected_slaves:
            address = f"{slave['addr'][0]}:{slave['addr'][1]}"
            print(f"|{str(slave['index']).center(index_len)}|{slave['username'].center(username_len)}|{slave['hostname'].center(hostname_len)}|{slave['os_version'].center(os_version_len)}|{address.center(addr_len)}|")
            print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")

    def clear(self, command):
        os.system('cls')

    def cmd(self, command):
        command = " ".join(command.split()[1:])
        msg = {
            'type': 'command',
            'command': 'cmd',
            'command_string': command,
            'slaves': [slave['addr'] for slave in self.master.selected_slaves],
        }
        self.master.send_dict(msg)
        msg = self.master.recieve_dict()
        if not msg: print("No response from server.")
        for response in msg['responses']:
            if response['response'] is None:
                slave = self.master.pop_slave(response['addr'])
                print(f"┌[{slave['username']}@{slave['hostname']}]")
                print('└> Disconnected!\n')
            for slave in self.master.selected_slaves:
                if slave['addr'] == response['addr']:
                    print(f"┌[{slave['username']}@{slave['hostname']}]")
                    print('└>',end='')
                    output = response['response']['cmd_output'].split('\n')
                    for line in output:
                        print(f"\t{line}")

    def exit(self, command):
        self.master.client.sock.close()
        sys.exit()

if __name__ == "__main__":
    from config import Config

    master = MasterClient(addr=Config.SERVER_ADDR, debug=True)
    master.password = Config.MASTER_PASSWORD

    master.command_loop()