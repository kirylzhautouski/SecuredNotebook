import socket
import threading
import os

import gm
import idea

from protocol import *
from transport import *

HOST = ''
PORT = 11555


FILES_DIRECTORY_PATH = 'storage/'


def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def get_file_names(files_dir_path):
    return [entry.name for entry in os.scandir(files_dir_path) if entry.is_file()] 


def handle_client(conn, addr):
    with conn:
        print('Connected by', addr)

        hello_request = Message.from_bytes(recv_msg(conn))
        if not isinstance(hello_request, ClientHelloRequest):
            raise IllegalMessageException()
        else:
            send_msg(conn, Message.to_bytes(ServerOkResponse()))

        gm_request = Message.from_bytes(recv_msg(conn))
        if not isinstance(gm_request, SendOpenKeyRequest):
            raise IllegalMessageException()
        else:
            open_gm_key = gm_request.open_key
            send_msg(conn, Message.to_bytes(ServerOkResponse()))

        session_key = None
        while True:
            request = Message.from_bytes(recv_msg(conn))
            if isinstance(request, GetSessionKeyRequest):
                session_key = idea.generate_key()
                encrypted_session_key = gm.encrypt(session_key, open_gm_key)
                send_msg(conn, Message.to_bytes(GetSessionKeyResponse(encrypted_session_key)))
            elif isinstance(request, GetFileTextRequest):
                if not session_key:
                    raise IllegalMessageException('Client should request session key before file text')

                file_name = request.file_name
                file_text = read_file(FILES_DIRECTORY_PATH + file_name)
                encrypted_file_text, initialization_list = idea.encrypt(file_text, session_key)
                send_msg(conn, Message.to_bytes(GetFileTextResponse(encrypted_file_text, initialization_list)))
            elif isinstance(request, GetFileNamesRequest):
                send_msg(conn, Message.to_bytes(GetFileNamesResponse(get_file_names(FILES_DIRECTORY_PATH))))
            else:
                raise IllegalMessageException()


def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()

            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


if __name__ == '__main__':
    run_server()
