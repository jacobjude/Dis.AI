from cryptography.fernet import Fernet
import json

def generate_key():
    key=""
    with open('key.txt', "w") as f:
        key = Fernet.generate_key()
        global fernet
        fernet = Fernet(key)
        f.write(str(key.decode()))
    return key

# get key if there is one
with open('key.txt', "r") as f:
    key = f.read()
    if not key:
        key = generate_key()
    else:
        key = key.encode()
    fernet = Fernet(key)

def get_key(delete_key=True):
    try:
        key=""
        with open('key.txt', "r") as f:
            key = f.read().encode()
            if not key:
                key = generate_key()
        if delete_key:
            with open('key.txt', "w") as f:
                f.write("")
        global fernet
        fernet = Fernet(key)
        return key  
    except Exception as e:
        print(f"encrypt err: {e}")
    
def encrypt_string(string):
    return fernet.encrypt(string.encode())
     
def decrypt_string(string):
    try:
        if isinstance(string, bytes):
            return fernet.decrypt(string).decode()
        elif isinstance(string,list):
            return json.dumps(string)
        else:
            return string
    except Exception as e:
        print(f"decrypt err: {e} - {string}")
