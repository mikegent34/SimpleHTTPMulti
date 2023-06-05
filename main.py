from socket import *
import argparse
import threading
import time

PORT = 8000
LOCALHOST = '0.0.0.0'
HTTP_VERSION = b'HTTP/1.1'
g_thread_semaphore = None
g_sleep = 0


def process_commands():
    parser = argparse.ArgumentParser(
        prog='HTTP Server', description='Simple HTTP server that serves static content.')
    parser.add_argument("-t",
                        "--threads",
                        type=int,
                        help="The amount of concurrent threads allowed. This defaults to 5",
                        default=5)
    parser.add_argument('-s',
                        '--sleep',
                        type=int,
                        help='The amount of time to sleep in a thread after we have processed. This is to show thrading',
                        default=0)
    parser.add_argument('-k',
                        '--knock',
                        help='Turn on port knocking',
                        default=False,
                        action='store_true',
                        )
    args = parser.parse_args()
    return args


def get_knock(knock_port):
    got_connection = False
    knock_socket = socket(AF_INET, SOCK_STREAM)
    knock_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    knock_socket.bind((LOCALHOST, knock_port))

    # We could make this configurable but I think that's beyond the point.
    knock_socket.settimeout(30)
    knock_socket.listen(1)
    try:
        # Just give it one byte so that it shows the connection as being reset.
        if knock_socket.recv(1):
            got_connection = True
    except OSError:
        got_connection = True
    finally:
        knock_socket.close()
    return got_connection


def get_knock_sequence():
    # Consecutive ports aren't good but it illustrates the point.
    KNOCK_PORTS = [9000, 9001, 9002]
    try:
        while True:
            for i in range(len(KNOCK_PORTS)):
                got_knock = get_knock(KNOCK_PORTS[i])
                if got_knock:
                    if i == len(KNOCK_PORTS) - 1:
                        return True
                else:
                    i = 0
    except Exception as e:
        print("Something bad happened handling the knocks.")
        print(str(e))
        return False


def handle_connection(client_socket):
    print("Handling connection")

    incoming_data = client_socket.recv(1024)
    decoded_data = incoming_data.decode()
    headers = decoded_data.split("\n")

    response_method = b'400 Bad Request'
    response = b'Invalid request'
    # I don't think I care about any of the other headers.

    if headers[0]:
        http_request = headers[0]
        request_method, request_uri, _ = http_request.split()
        if request_method and request_method == 'GET':
            if request_uri and request_uri == '/':
                response_method = b'200 OK'
                response = b'We are a webserver that serves nothing good'
            elif request_uri:
                response_method = b'404 Not Found'
                response = b'We may not have that page.'
        elif request_method:
            response_method = b'405 Method Not Allowed'
            response = b'This is an error'

    # We could implement Content-Length here, but it doesn't seem necessary for the barebones.

    final_response = HTTP_VERSION + b' ' + response_method + b'\n\n' + response
    try:
        client_socket.sendall(final_response)
    except:
        print("An exception was thrown attempting to send a response.")
    finally:
        client_socket.close()
        # This is only here to show off multithreading.
        if args.sleep:
            time.sleep(args.sleep)
        g_thread_semaphore.release()


"""
Passing a kwargs argument here is not a preferred good practice.

This is to keep the program nimble but it makes it less maintainable.
"""


def socket_worker(args):
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcp_socket.bind((LOCALHOST, PORT))

    tcp_socket.listen(1)

    try:
        while True:
            g_thread_semaphore.acquire()
            try:
                client_socket, _ = tcp_socket.accept()
                new_thread = threading.Thread(
                    target=handle_connection, args=(client_socket,))
                # Making this a daemon or not is a difficult decision.
                # They are shut down abruptly on shutdown
                new_thread.daemon = True
                new_thread.start()
            finally:
                pass
    except:
        tcp_socket.close()
        # Removing this because we are using daemon threads, which should die on shutdown.
        '''
        for thread in threading.enumerate():
            # This is really best effort. There's not much you can do here.
            if thread.is_alive():
                thread.join()
        '''

if __name__ == "__main__":
    args = process_commands()
    '''
    I am fully aware that putting this knock sequence here does not allow it to be multithreaded
    This is because the way I'd like to see the port knocking "idea" interpreted is like that in malware.
    If you give it the specified requests on the specified ports it will then allow you to access the "meat" of the server.
    That would give us a multithreaded client
    
    Multithreading the port knocking adds a layer of complexity that doesn't seem worth the effort.
    '''
    can_start_webserver = True
    if args.knock:
        if get_knock_sequence():
            can_start_webserver = True
        else:
            can_start_webserver = False
    if can_start_webserver:
        g_thread_semaphore = threading.BoundedSemaphore(args.threads)
        socket_worker(args)
    else:
        print("Something went wrong and we never served content.")
