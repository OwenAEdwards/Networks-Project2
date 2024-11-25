import socket
import threading
from socket_protocol import parse_client_command
from bulletin_board import BulletinBoard
from private_board import PrivateBoard

# Unique delimiter
CRLF = "\r\n"

# Dictionary to keep track of session data for each client
client_sessions = {}

def handle_client(client_socket, public_board, private_boards):
    """
    Handles communication with a single connected client.
    Continuously listens for client commands, processes them, and sends responses back.
    """
    # Initialize client session data
    client_sessions[client_socket] = {'username': None}
    try:
        # Continuously listen for client commands in a loop.
        while True:
            # Receive up to 1024 bytes from the client.
            message = client_socket.recv(1024).decode('utf-8')

            # If we receive an empty message, continue waiting for a valid message.
            if not message.strip():
                continue

            # Parse the command and parameters from the client's message.
            print(f"Raw message received: {message}")  # Debugging info.
            command, params = parse_client_command(message)
            print(f"Command: {command}, Params: {params}")  # Debugging line

            # Handle the different commands the client can send.
            if command == '%connect':
                # Connect command expected two parameters: address and port.
                if len(params) == 2:
                    address = params[0]
                    port = params[1]
                    response = f"Connected to the bulletin board server at {address}:{port}."
                else:
                    response = "Error: %connect requires address and port."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%join':
                # Join command expects one parameter: the username.
                if len(params) == 1:
                    username = params[0]
                    print("Calling add_user with:", username)
                    # Set username in session data
                    client_sessions[client_socket]['username'] = username
                    # Add the user to the bulletin board.
                    public_board.add_user(username)
                    response = f"{username} has joined the bulletin board."
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: Incorrect parameters for %join."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%post':
                # Ensure the client has provided the correct number of parameters (4: sender, post_date, subject, content).
                if len(params) == 4:
                    sender = params[0]
                    post_date = params[1]
                    subject = params[2]
                    content = params[3]

                    # Verify that the sender has joined the bulletin board.
                    if sender not in public_board.list_users():
                        response = "Error: You must join the bulletin board first using %join <username>."
                    else:
                        # Generate a unique message ID and add the post to the bulletin board
                        message_id = public_board.add_post(sender, post_date, subject, content)
                        print(f"Calling add_post with: sender={sender}, post_date={post_date}, subject={subject}")
                        
                        response = f"Message posted with ID {message_id}."
                        print(f"[DEBUG] %post response: {response}")  # Debug line
                else:
                    # Error message if the wrong number of parameters is provided
                    response = "Error: Incorrect parameters for %post. Usage: %post <subject> <content>."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%users':
                # Retrieve the list of users from the bulletin board.
                users = public_board.list_users()
                # Format the list of users as a newline-separated string if there are any users.
                # If the list is empty, send a response indicating no users are in the group.
                response = "\n".join(users) if users else "No users in the group."
                client_socket.send((response + CRLF).encode('utf-8'))

            # Handle the %leave command to remove the user
            elif command == '%leave':
                username = client_sessions[client_socket].get('username')
                if username:
                    public_board.remove_user(username)
                    response = f"{username} has left the bulletin board."
                    # Clear session data
                    client_sessions[client_socket]['username'] = None
                else:
                    response = "Error: You are not currently joined to leave."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%message':
                # Message command expects one parameter: message_id.
                if len(params) == 1:
                    message_id = int(params[0])
                    # Retrieve the content of the specified message from the bulletin board.
                    message_content = public_board.get_message_content(message_id)
                    # If the message is found, send its content; otherwise, indicate that it wasn't found.
                    response = message_content if message_content else "Message not found."
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %message requires a message ID."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%exit':
                # Exit command terminates client session.
                # Send a farewell message to the client.
                response = "Goodbye!"
                client_socket.send((response + CRLF).encode('utf-8'))
                # Break the loop to end the connection with the client.
                break

            ### Part 2 commands ###
            
            elif command == '%groups':
                # Ensure private_boards is a list of PrivateBoard instances
                if private_boards:
                    # Retrieve group names and IDs from each PrivateBoard instance
                    groups = [f"ID: {board.group_id}, Name: {board.group_name}" for board in private_boards]
                    # Format the list as a newline-separated string if there are groups available
                    response = "\n".join(groups)
                else:
                    # Indicate that no groups are available
                    response = "No groups available."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%groupjoin':
                # Group Join command expects one parameter: group_id.
                if len(params) == 1:
                    group_id = params[0]
                    # Attempt to join the specified group by ID/name.
                    response = bulletin_board.join_group(group_id)
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %groupjoin requires group ID/name."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%grouppost':
                # Group Post command expects at least three parameters: group_id, subject, and content.
                if len(params) >= 3:
                    group_id = params[0]
                    subject = params[1]
                    # Join the remaining parameters to form the message content/body.
                    content = " ".join(params[2:])
                    # Post the message to the specified group and return a response indicating success.
                    response = bulletin_board.post_to_group(group_id, subject, content)
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %grouppost requires group ID, subject, and content."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%groupusers':
                # Group Users command expects one parameter: group_id.
                if len(params) == 1:
                    group_id = params[0]
                    # Retrieve the list of users in the specified group.
                    users = bulletin_board.list_group_users(group_id)
                    # Format the list as a newline-separated string if there are users in the group;
                    # otherwise, send a response indicating no users are in the group.
                    response = "\n".join(users) if users else "No users in the group."
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %groupusers requires group ID/name."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%groupleave':
                # Group Leave command expects one parameter: group_id.
                if len(params) == 1:
                    group_id = params[0]
                    # Attempt to leave the specified group.
                    response = bulletin_board.leave_group(group_id)
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %groupleave requires group ID/name."
                client_socket.send((response + CRLF).encode('utf-8'))

            elif command == '%groupmessage':
                # Group Message command expects two parameters: group_id and message_id.
                if len(params) == 2:
                    group_id = params[0]
                    message_id = params[1]
                    # Retrieve the message content for the specified message ID in the specified group.
                    response = bulletin_board.get_group_message(group_id, message_id)
                else:
                    # Error message if the wrong number of parameters is provided.
                    response = "Error: %groupmessage requires group ID and message ID."
                client_socket.send((response + CRLF).encode('utf-8'))

            else:
                # Send an error response if the command is not recognized.
                response = "Unknown command."
                client_socket.send((response + CRLF).encode('utf-8'))
    
    except ValueError as ve:
        print(f"ValueError encountered: {ve}")
        response = "Error: Invalid parameters."
        client_socket.send((response + CRLF).encode('utf-8'))
    except socket.error as se:
        print(f"Socket error: {se}")
        response = "Error: Socket communication failure."
        client_socket.send((response + CRLF).encode('utf-8'))
    except Exception as e:
        print(f"Unexpected error handling client: {e}")
    finally:
        # Clean up session data
        if client_socket in client_sessions:
            del client_sessions[client_socket]
        # Ensure the client socket is closed, whether or not an error occurred.
        # This releases resources associated with the client connection.
        client_socket.close()
        print("Client disconnected.")

def start_server(host, port):
    """
    Initializes and starts the server, listening for client connections.
    Spawns a new thread for each connected client to handle communications.
    """

    # Create a new socket using IPv4 (AF_INET) and TCP (SOCK_STREAM).
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the server to the specified host and port.
    server.bind((host, port))

    # Start listening for incoming connections; '5' is the max number of queued connections.
    server.listen(5)
    print(f"[*] Listening on {host}:{port}")

    # Initialize a BulletinBoard instance to store messages from clients for the public bulletin board.
    public_board = BulletinBoard()

    # Initialize 5 BulletinBoard instances to store messages from clients for the private bulletin boards.
    custom_group_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    private_boards = [PrivateBoard(f"Group {name}") for name in custom_group_names]

    # Continuously accept new client connections.
    while True:
        # Accept a new client connection; returns a new socket and the address of the client.
        client_socket, client_address = server.accept()
        print(f"[*] Accepted connection from {client_address}")

        # Create a new thread to handle communication with this client.
        # Each client connection is managed independently to allow simultaneous clients.
        client_handler_thread = threading.Thread(target=handle_client, args=(client_socket, public_board, private_boards))

        # Start the client handler thread.
        client_handler_thread.start()

if __name__ == "__main__":
    start_server('127.0.0.1', 5000)  # or 'localhost'