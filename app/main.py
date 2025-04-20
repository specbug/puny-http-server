import socket  # noqa: F401

def parse_request(request_bytes):
    """Parses the raw HTTP request and returns method and path."""
    request_lines = request_bytes.decode().split("\r\n")
    start_line = request_lines[0]
    method, path, _ = start_line.split(" ")
    # TODO: Parse headers if needed
    return method, path

def handle_echo(req_path, sender_socket):
    # Extract content after /echo/ prefix
    if req_path.startswith("/echo/"):
        s = req_path[6:]  # Skip "/echo/" prefix
    else:
        # This case should ideally not be reached if routing is correct
        sender_socket.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
        return

    s_len = len(s)
    response_body = s.encode()
    response_headers = f"Content-Type: text/plain\r\nContent-Length: {s_len}\r\n"
    response = f"HTTP/1.1 200 OK\r\n{response_headers}\r\n".encode() + response_body
    sender_socket.sendall(response)

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    conn = server_socket.accept()  # wait for client
    sender_socket, addr = conn

    # Get the request from the client
    req_bytes = sender_socket.recv(2048)
    method, path = parse_request(req_bytes)
    print(f"Received request: {method} {path}")

    if path == "/":
        sender_socket.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
    elif path.startswith("/echo/"):
        handle_echo(path, sender_socket)
    else:
        sender_socket.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")

    # Close the connection
    sender_socket.close()
    server_socket.close()

if __name__ == "__main__":
    main()
