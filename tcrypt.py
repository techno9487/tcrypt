import sys
import os
import json
import argparse
import urllib.request

class CMDHandler:
    def __init__(self) -> None:
        self.__cmds = {}

    def add_command(self, name, handler):
        self.__cmds[name] = handler

    def get_command(self, name):
        if name in self.__cmds:
            return self.__cmds[name]

        return None
    
    def __help_text(self):
        print("Valid commands are:")
        for x in self.__cmds:
            print(x)
    
    def handle(self, args):
        if len(args) < 1:
            self.__help_text()
            return

        cmd_key = args[0]
        cmd = self.get_command(cmd_key)
        if cmd == None:
            self.__help_text()
            return
        
        cmd(args[1:])

def update_address_book(module, id, key):
    with open('.tcrypt/address_book','a') as addr_book:
        meta = json.dumps({
            'module': module,
            'id': id
        })
        addr_book.write('#META: %s\n' % meta)
        addr_book.write('%s\n' % key)

def handle_key_add_github(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='username of the github user to add')
    parsed_args = parser.parse_args(args)
    
    contents = urllib.request.urlopen('https://github.com/%s.keys' % parsed_args.username)
    key_lines = contents.read().decode('utf-8').split('\n')
    for key in key_lines:
        if key == '':
            continue

        update_address_book('github', parsed_args.username, key)
    

def handle_key_add(args):
    module_handler = CMDHandler()
    module_handler.add_command('github', handle_key_add_github)
    module_handler.handle(args)

def handle_key(args):
    key_handler = CMDHandler()
    key_handler.add_command('add', handle_key_add)
    key_handler.handle(args)

def age_encrypt(content: bytes) -> bytes:
    import subprocess
    proc = subprocess.Popen(args=['age','-e','-R','.tcrypt/address_book'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = proc.communicate(input=content)
    return result[0]

def age_decrypt(content: bytes) -> bytes:
    import subprocess
    proc = subprocess.Popen(args=['age','-d','-i','%s/.ssh/tcrypt' % os.path.expanduser('~')],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = proc.communicate(input=content)
    return result[0]

def handle_filter_clean(args):
    sys.stdout.buffer.write(age_encrypt(sys.stdin.buffer.read()))
    sys.stdout.buffer.flush()

def handle_filter_smudge(args):
    sys.stdout.buffer.write(age_decrypt(sys.stdin.buffer.read()))
    sys.stdout.buffer.flush()

def handle_filter(args):
    filter_handler = CMDHandler()
    filter_handler.add_command('clean', handle_filter_clean)
    filter_handler.add_command('smudge', handle_filter_smudge)
    filter_handler.handle(args)

def handle_init(args):
    if not os.path.exists('.tcrypt'):
        os.mkdir('.tcrypt')

    if not os.path.exists('.tcrypt/address_book'):
        file = open('.tcrypt/address_book',"w")
        file.write('# tcrypt managed AGE address book, DO NOT MODIFY!\n')
        file.close()

    #TODO: Setup the git filters programmicaly
    #TODO: Handle the decryption key

def main():
    root_handler = CMDHandler()
    root_handler.add_command('key', handle_key)
    root_handler.add_command('filter', handle_filter)
    root_handler.add_command('init', handle_init)
    root_handler.handle(sys.argv[1:])

if __name__ == '__main__':
    main()