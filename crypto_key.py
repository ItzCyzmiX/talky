from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()
import os

cipher = Fernet(os.getenv("FERNET_KEY").encode())


key = "123".encode()

encrypted = cipher.encrypt(key)


print(f"encrypted {encrypted}")

decrypted = cipher.decrypt(encrypted).decode()

print(f"decrypted {decrypted}")
