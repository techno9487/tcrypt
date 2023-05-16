import sys
import os
import json
import argparse
import urllib.request
import subprocess

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

class KeyManager:
    def __init__(self) -> None:
        self.idenity_file_location = '.git/.tcrypt_key'

    def update_address_book(self, module, id, key):
        with open('.tcrypt/address_book','a') as addr_book:
            meta = json.dumps({
                'module': module,
                'id': id
            })
            addr_book.write('#META: %s\n' % meta)
            addr_book.write('%s\n' % key)

    def __check_valid_identity(self, identity_file_path: str) -> bool:
        import secrets
        n = secrets.token_bytes()
        encrypted_data = age_encrypt(n)
        decrypted_data = age_decrypt(encrypted_data, identity_file_path)

        return n == decrypted_data
    
    def store_decrypt_identity(self, identity: str):
        if not self.__check_valid_identity(identity):
            print("ERROR: Identity is invalid")
            return
    
        with open(self.idenity_file_location,'w') as tcrypt_config:
            tcrypt_config.write(json.dumps({
                'identity': identity
            }))

    def get_decryption_identity(self) -> str:
        with open(self.idenity_file_location, 'r') as tcrypt_key:
            key_obj = json.loads(
                tcrypt_key.read()
            )

            return key_obj['identity']

def handle_key_add_github(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='username of the github user to add')
    parsed_args = parser.parse_args(args)

    mgr = KeyManager()
    
    contents = urllib.request.urlopen('https://github.com/%s.keys' % parsed_args.username)
    key_lines = contents.read().decode('utf-8').split('\n')
    for key in key_lines:
        if key == '':
            continue

        mgr.update_address_book('github', parsed_args.username, key)
    

def handle_key_add(args):
    module_handler = CMDHandler()
    module_handler.add_command('github', handle_key_add_github)
    module_handler.handle(args)

def handle_key(args):
    key_handler = CMDHandler()
    key_handler.add_command('add', handle_key_add)
    key_handler.handle(args)

def age_encrypt(content: bytes) -> bytes:
    proc = subprocess.Popen(args=['age','-e','-R','.tcrypt/address_book'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = proc.communicate(input=content)
    return result[0]

def age_decrypt(content: bytes, identity_file: str) -> bytes:
    proc = subprocess.Popen(args=['age','-d','-i',os.path.expanduser(identity_file)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    result = proc.communicate(input=content)
    return result[0]

def handle_filter_clean(args):
    sys.stdout.buffer.write(age_encrypt(sys.stdin.buffer.read()))
    sys.stdout.buffer.flush()

def handle_filter_smudge(args):
    mgr = KeyManager()
    sys.stdout.buffer.write(age_decrypt(sys.stdin.buffer.read(),mgr.get_decryption_identity()))
    sys.stdout.buffer.flush()

def handle_filter(args):
    filter_handler = CMDHandler()
    filter_handler.add_command('clean', handle_filter_clean)
    filter_handler.add_command('smudge', handle_filter_smudge)
    filter_handler.handle(args)

def set_git_config(key, value):
    result = subprocess.run(args=['git','config',key, value],
                            capture_output=True)
    result.check_returncode()

def handle_init(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('identity', help='path to SSH identity file to use for decrypt')
    parsed_args = parser.parse_args(args)

    if not os.path.exists('.tcrypt'):
        os.mkdir('.tcrypt')

    if not os.path.exists('.tcrypt/address_book'):
        file = open('.tcrypt/address_book',"w")
        file.write('# tcrypt managed AGE address book, DO NOT MODIFY!\n')
        file.close()

    set_git_config('filter.tcrypt.clean', 'python3 tcrypt.py filter clean')
    set_git_config('filter.tcrypt.smudge', 'python3 tcrypt.py filter smudge')
    
    mgr = KeyManager()
    mgr.store_decrypt_identity(parsed_args.identity)

def main():
    root_handler = CMDHandler()
    root_handler.add_command('key', handle_key)
    root_handler.add_command('filter', handle_filter)
    root_handler.add_command('init', handle_init)
    root_handler.handle(sys.argv[1:])

if __name__ == '__main__':
    main()