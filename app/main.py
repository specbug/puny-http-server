import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage
    #
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    conn = server_socket.accept() # wait for client
    sender_socket, addr = conn
    # Get the GET request from the client
    req = sender_socket.recv(2048)
    reqs = req.decode().split("\r\n")
    print(reqs)
    client_req = reqs[0].split(" ")
    client_req_path = client_req[1]
    # Extract content after /echo/ prefix
    if client_req_path.startswith("/echo/"):
        s = client_req_path[6:]  # Skip "/echo/" prefix
    else:
        sender_socket.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
    s_len = len(s)
    # Send the response back to the client
    sender_socket.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: " + str(s_len).encode() + b"\r\n\r\n" + s.encode())  

if __name__ == "__main__":
    main()
