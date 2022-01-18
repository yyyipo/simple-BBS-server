import socket
import threading
import sqlite3
import sys
import re
import datetime

# server information
HOST = "127.0.0.1"
PORT = int(sys.argv[1]) 

# declare a list to store all the data of the boards and the posts
# [[board1[post1[S/N, title, author, date, content, command]], [post2], [post3], ...], [board2], [board3], ...]
board_list = []
post_in_board = []
SN = 0
mutex = threading.Lock()

# key:chatroom name, value:(port, status)
chatroom_dict = dict()


def handle_register(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db):
    #the in put format of register is correct
    if (len(request_udp_split) == 4):
        cursor_db.execute('''SELECT username
                          FROM users
                          WHERE username = ?''', (request_udp_split[1], ))
        #get the result of the sql query, and store the list in check_username
        check_username = cursor_db.fetchall()
        
        #username is available
        if (len(check_username) == 0):                    
            cursor_db.execute("INSERT INTO users VALUES(?, ?, ?)", (request_udp_split[1], request_udp_split[2], request_udp_split[3],))
            connect_db.commit()
            response_udp = "Register successfully."
        #username unavailable
        else:                    
            response_udp = "Username is already used."
    #the input format of register is wrong        
    else:
        response_udp = "Usage: register <username> <email> <password>"
    socket_udp.sendto(response_udp.encode(), addr_udp)

    
def handle_whoami(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db):
    cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (request_udp_split[1], ))
    #get the result of the sql query, and store the list in check_username
    check_username = cursor_db.fetchall()
    if (len(check_username) == 0):
        response_udp = "Please login first."
    else:
        response_udp = check_username[0][0]
    socket_udp.sendto(response_udp.encode(), addr_udp)

    
def handle_login(request_tcp_split, client, connect_db, cursor_db):
    if(len(request_tcp_split) == 4):
        #the user has login already
        if (request_tcp_split[3] != "aaa"):
            response_tcp = "Please logout first.#aaa"
            client.send(response_tcp.encode()) 
        #the user hasn't log in 
        else:
            cursor_db.execute('''SELECT username, password
                      FROM users
                      WHERE username = ?''', (request_tcp_split[1],))
            check_login = cursor_db.fetchall()
            #username or password incorrect
            if (len(check_login) == 0) or (check_login[0][0] != request_tcp_split[2]):
                response_tcp = "Login failed." + "#" + request_tcp_split[3]
                client.send(response_tcp.encode()) 
            #username and password correct
            else:
                cursor_db.execute("INSERT INTO login_user (username) VALUES(?)", (request_tcp_split[1],))
                connect_db.commit()
                cursor_db.execute('''SELECT random_num
                                  FROM login_user
                                  WHERE username = ?
                                  ORDER BY random_num DESC''', (request_tcp_split[1],))
                random = cursor_db.fetchone()
                random = str(random[0])
                response_tcp = "Welcome, " + request_tcp_split[1] + ".#" + random + "#" + check_login[0][0]
                client.send(response_tcp.encode())
                                                
    #login format wrong
    else:
        response_tcp = "Usage: login <username> <password>"
        client.send(response_tcp.encode())

        
def handle_listuser(request_tcp_split, client, connect_db, cursor_db):
    cursor_db.execute('''SELECT username, email
                        FROM users''')
    list_users = cursor_db.fetchall()
    
    response_tcp = "Name\tEmail"
    for i in range (len(list_users)):
        user_information = list_users[i]
        response_tcp = response_tcp + "\n" + user_information[0] + "\t" + user_information[1]
        #response_tcp = response_tcp + user_information[1]
    client.send(response_tcp.encode()) 


def handle_logout(request_tcp_split, client, connect_db, cursor_db):
    cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (request_tcp_split[1], ))

    #get the result of the sql query, and store the list in check_username
    check_username = cursor_db.fetchone()
    if (check_username == None):
        response_tcp = "Please login first." + "#" + request_tcp_split[1]
        client.send(response_tcp.encode()) 
    else:
        #print(chatroom_dict.get(check_username[0]))
        if(chatroom_dict.get(check_username[0]) != None and chatroom_dict.get(check_username[0])[1] == "open"):
            response_tcp = "Please do \"attach\" and \"leave-chatroom\" first.#" + request_tcp_split[1]
        else:
            cursor_db.execute('''DELETE 
                            FROM login_user 
                            WHERE random_num = ?''', (request_tcp_split[1], ))
            connect_db.commit()
            response_tcp = "Bye, " + check_username[0] + ".#aaa"
        client.send(response_tcp.encode())


def handle_create_board(request_tcp_split, client, connect_db, cursor_db):
    #request_tcp_split[0]: create-board, request_tcp_split[1]: board_name, request_tcp_split[2]: random_num

    #command incomplete
    if(len(request_tcp_split) < 3):
        response_tcp = "Usage: login <name>"
    #hasn't login yet
    elif (request_tcp_split[2] == "aaa"):
        response_tcp = "Please login first."
    else:
        cursor_db.execute('''SELECT board_name
                        FROM board
                        WHERE board_name = ?''', (request_tcp_split[1], ))
        #get the result of the sql query, and store the result in check_board
        check_board = cursor_db.fetchone()

        #the board already exists 
        if (check_board != None):
            response_tcp = "Board already exists."
        #the board doesn't exist, create the board
        else:
            global board_list, mutex

            mutex.acquire()
            cursor_db.execute('''SELECT username
                                FROM login_user
                                WHERE random_num = ?''', (request_tcp_split[2],))
            moderator = check_board = cursor_db.fetchone()[0]
            cursor_db.execute("INSERT INTO board (board_name, board_moderator) VALUES(?, ?)", (request_tcp_split[1], moderator,))
            connect_db.commit()

            new_board = []
            board_list.append(new_board)
            mutex.release()

            response_tcp = "Create board successfully."



    #send the response message to the client
    client.send(response_tcp.encode())


def handle_create_post(request_tcp, client, connect_db, cursor_db):
    create_post_split = re.split("create-post | --title | --content |#####", request_tcp)
    #create_post_split[1]: board-name, create_post_split[2]:title, create_post_split[3]:content, create_post_split[4]: random_num

    #command incomplete
    if(len(create_post_split) < 5):
        response_tcp = "Usage: create-post <board-name> --title <title> --content <content>"
    #hasn't login yet
    elif(create_post_split[4] == "aaa"):
        response_tcp = "Please login first."

    else:
        cursor_db.execute('''SELECT board_index
                        FROM board
                        WHERE board_name = ?''', (create_post_split[1], ))
        check_board = cursor_db.fetchone()

        #the board aldoesn't exist 
        if (check_board == None):
            response_tcp = "Board does not exist."
        else:
            global board_list, SN, post_in_board, mutex
            
            mutex.acquire()
            cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (create_post_split[4], ))
            author = cursor_db.fetchone()

            #[[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]
            board_idx = check_board[0] - 1
            SN = SN + 1
            author = author[0]
            title = create_post_split[2]
            time = datetime.datetime.now()
            date = str(time.month) + "/" + str(time.day)
            content = create_post_split[3]
            command = []
            new_post = [SN, author, title, date, content, command]
            board_list[board_idx].append(new_post)
            post_in_board.append(board_idx)

            #print(new_post)
            #print(board_list)
            mutex.release()

            response_tcp = "Create post successfully."

    #send the response message to the client
    client.send(response_tcp.encode())   


def handle_list_board(request_tcp_split, client, connect_db, cursor_db):
    #request_tcp_split[0]: list-board
    global mutex

    mutex.acquire()
    cursor_db.execute('''SELECT board_index, board_name, board_moderator
                        FROM board''')
    #get the result of the sql query, and store the result in list_boards
    list_boards = cursor_db.fetchall()
    
    response_tcp = "Index\tName\tModerator"
    for i in range (len(list_boards)):
        board_information = list_boards[i]
        response_tcp = response_tcp + "\n" + str(board_information[0]) + "\t" + board_information[1] + "\t" + board_information[2]

    mutex.release()

    #send the response message to the client
    client.send(response_tcp.encode()) 


def handle_list_post(request_tcp_split, client, connect_db, cursor_db):
    #request_tcp_split[0]: list-post #request_tcp_split[1]: board-name

    #command incomplete
    if(len(request_tcp_split) < 2):
        response_tcp = "Usage: list-post <board-name>"
    else:

        cursor_db.execute('''SELECT board_index
                            FROM board
                            WHERE board_name = ?''', (request_tcp_split[1], ))
        #get the result of the sql query, and store the result in check_board
        check_board = cursor_db.fetchone()
        
        #the board doesn't exist
        if (check_board == None):
            response_tcp = "Board does not exist."

        #the board exists
        else:
            global mutex

            mutex.acquire()
            response_tcp = "S/N\t\tTitle\t\t\t\tAuthor\t\t\t\tDate" # 0 
            #[[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]
            board_idx = check_board[0] - 1
            post_num = len(board_list[board_idx])
            for i in range(post_num):
                response_tcp = response_tcp + "\n" + str(board_list[board_idx][i][0]) + "\t\t" + board_list[board_idx][i][2] + "\t\t" 
                response_tcp = response_tcp + board_list[board_idx][i][1] + "\t\t" + board_list[board_idx][i][3]
            mutex.release()

    #send the response message to the client
    client.send(response_tcp.encode()) 

def handle_read(request_tcp_split, client, connect_db, cursor_db):

    #command incomplete
    if (len(request_tcp_split) < 2):
        response_tcp = "usage: read <post-S/N>"
    #post doesn't exist
    elif (int(request_tcp_split[1]) > SN or post_in_board[int(request_tcp_split[1]) - 1] == "deleted"):
        response_tcp = "Post does not exist."

    #post exists
    else:
        global mutex

        mutex.acquire()
        #[[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]
        board_idx = post_in_board[int(request_tcp_split[1]) - 1]
        board_post = board_list[board_idx]
        for i in range (len(board_post)):
            if (board_post[i][0] == int(request_tcp_split[1])):
                post = board_post[i]
                Author = post[1]
                Title = post[2]
                Date = post[3]
                Content = post[4].split("<br>")
                Comment = post[5]

                response_tcp = "Author: " + Author + "\n" + "Title: " + Title + "\n" + "Date: " + Date + "\n--\n"
                for j in range (len(Content)):
                    response_tcp = response_tcp + Content[j] + "\n"
                response_tcp = response_tcp + "--"
                for j in range (len(Comment)):
                    response_tcp = response_tcp + "\n" + Comment[j][0] + ": " + Comment[j][1]           
                break
        mutex.release()

    client.send(response_tcp.encode()) 

def handle_delete_post(request_tcp_split, client, connect_db, cursor_db):
    global board_list, post_in_board
    #[[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]

    #command incomplete
    if (len(request_tcp_split) < 3):
        response_tcp = "usage: delete-post <post-S/N>"
    #hasn't login yet
    elif request_tcp_split[2] == "aaa":
        response_tcp = "Please login first."
    
    else:
        #global board_list, post_in_board
        

        #post does not exist
        if (int(request_tcp_split[1]) > SN or post_in_board[int(request_tcp_split[1]) - 1] == "deleted"):
            response_tcp = "Post does not exist."
        
        #post exists
        else:          
            #global board_list, post_in_board
            board_idx = post_in_board[int(request_tcp_split[1]) - 1]
            board_post = board_list[board_idx]
            for i in range (len(board_post)):
                if (board_post[i][0] == int(request_tcp_split[1])):
                    post_author = board_post[i][1]
                    break
            
            cursor_db.execute('''SELECT username
                                FROM login_user
                                WHERE random_num = ?''', (request_tcp_split[2], ))
            login_user = cursor_db.fetchone()[0]
            
            # not the post owner
            if (post_author != login_user):
                response_tcp = "Not the post owner."

            # the post owner
            else:
                #global board_list, post_in_board, mutex

                mutex.acquire()
                #delete the post from the board
                board_post.pop(i)
                #change the value in post_in_board into "deleted"
                post_in_board[int(request_tcp_split[1]) - 1] = "deleted"
                mutex.release()

                response_tcp = "Delete successfully."

    client.send(response_tcp.encode()) 


def handle_update_post(request_tcp, client, connect_db, cursor_db):
    global board_list, mutex

    random_num = request_tcp.split("#####")[1]
    request_tcp = request_tcp.split("#####")[0]
    request_tcp_split = request_tcp.split(" ")

    # request_tcp_split[0]: update-post, request_tcp_split[1]: SN, request_tcp_split[2]:--title/content, request_tcp_split[3~end]: new title/content
    # [[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]
    if (len(request_tcp_split) < 5):
        response_tcp = "usage: update-post <post-S/N> --title/content <new>"

    # hasn't login yet
    elif (random_num == "aaa"):
        response_tcp = "Please login first."

    else:       

        # post does not exist
        if(int(request_tcp_split[1]) > SN or post_in_board[int(request_tcp_split[1]) - 1] == "deleted"):
            response_tcp = "Post does not exist."
        
        # post exists
        else:
            
            board_idx = post_in_board[int(request_tcp_split[1]) - 1]
            board_post = board_list[board_idx]
            for i in range (len(board_post)):
                if (board_post[i][0] == int(request_tcp_split[1])):
                    post = board_post[i]
                    post_author = post[1]
                    break
            
            cursor_db.execute('''SELECT username
                                FROM login_user
                                WHERE random_num = ?''', (random_num, ))

            login_user = cursor_db.fetchone()[0]

            # not the post owner
            if (post_author != login_user):
                response_tcp = "Not the post owner."

            # the post owner
            else:
                mutex.acquire()

                #update title
                if (request_tcp_split[2] == "--title"):
                    post[2] = ""
                    for i in range (len(request_tcp_split) - 3):
                        if(i > 0):
                            post[2] = post[2] + " "
                        post[2] = post[2] + request_tcp_split[i + 3]
                    
                elif (request_tcp_split[2] == "--content"):
                    post[4] = ""
                    for i in range (len(request_tcp_split) - 3):
                        if(i > 0):
                            post[4] = post[4] + " "
                        post[4] = post[4] + request_tcp_split[i + 3] + " "
                mutex.release()

                response_tcp = "Update successfully."
    
    client.send(response_tcp.encode())


def handle_comment(request_tcp, client, connect_db, cursor_db):
    global board_list, mutex

    random_num = request_tcp.split("#####")[1]
    request_tcp = request_tcp.split("#####")[0]
    request_tcp_split = request_tcp.split(" ")

    # request_tcp_split[0]: comment, request_tcp_split[1]: SN, request_tcp_split[2~end]: <comment>
    # [[board1[post1[S/N, author, title, date, content, [command]], [post2], [post3], ...], [board2], [board3], ...]

    #command incomplete
    if (len(request_tcp_split) <= 2):
        response_tcp = "usage: comment <post-S/N> <comment>"

    # hasn't login
    elif (random_num == "aaa"):
        response_tcp = "Please login first."

    elif(random_num != "aaa"):
        # post does not exist
        if(int(request_tcp_split[1]) > SN or post_in_board[int(request_tcp_split[1]) - 1] == "deleted"):
            response_tcp = "Post does not exist."

        # post exists
        else:
            mutex.acquire()
            cursor_db.execute('''SELECT username
                                FROM login_user
                                WHERE random_num = ?''', (random_num, ))
            login_user = cursor_db.fetchone()[0]

            comment_content = ""
            for i in range (len(request_tcp_split) - 2):
                if (i > 0):
                    comment_content = comment_content + " "
                comment_content = comment_content + request_tcp_split[i + 2]

            comment = [login_user, comment_content]

            board_idx = post_in_board[int(request_tcp_split[1]) - 1]
            board_post = board_list[board_idx]
            for i in range (len(board_post)):
                if (board_post[i][0] == int(request_tcp_split[1])):
                    post = board_post[i]
                    break
            
            post[5].append(comment)
            mutex.release()

            response_tcp = "Comment successfully."

    elif (random_num == "aaa"):
        response_tcp = "Please login first."

    client.send(response_tcp.encode())

def handle_create_chatroom(request_tcp, client, connect_db, cursor_db):
    global chatroom_dict

    request_tcp_split = request_tcp.split("#####")
    random_num = request_tcp_split[1]
    request_tcp_split = request_tcp_split[0].split(" ")
    PORT_chatroom = request_tcp_split[1]

    # hasn't login yet
    if(random_num == "aaa"):
        response_tcp = "Please login first."
    else:
        # get the username
        cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (random_num, ))
        creator = cursor_db.fetchone()[0]

        # the chatroom doesn't exist
        if(chatroom_dict.get(creator) == None):
            chatroom_dict[creator] = (PORT_chatroom, "open")
            response_tcp = "start to create chatroom..."
        
        # chatroom already exist
        else:
            response_tcp = "User has already created the chatroom."
    
    client.send(response_tcp.encode())

def handle_list_chatroom(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db):
    global chatroom_dict

    random_num = request_udp_split[1]

    # hasn't login yet
    if (random_num == "aaa"):
        response_udp = "Please login first."

    else:
        response_udp = "Chatroom_name\tStatus"
        for key, value in chatroom_dict.items():
            response_udp += "\n" + key + "\t" + value[1]

    socket_udp.sendto(response_udp.encode(), addr_udp)


def handle_join_chatroom(request_tcp, client, connect_db, cursor_db):
    global chatroom_dict

    request_tcp_split = request_tcp.split("#####")
    random_num = request_tcp_split[1]
    request_tcp_split = request_tcp_split[0].split(" ")
    chatroom_name = request_tcp_split[1]

    # hasn't login yet
    if(random_num == "aaa"):
        response_tcp = "Please login first."
    else:
        # the chatroom does not exist
        if(chatroom_dict.get(chatroom_name) == None or chatroom_dict.get(chatroom_name)[1] == "close" ):
            response_tcp = "The chatroom does not exist or the chat room is closed."
        
        # chatroom exists
        else:
            response_tcp = chatroom_dict.get(chatroom_name)[0]
    
    client.send(response_tcp.encode())


def handle_leave_chatroom(request_tcp_split, client, connect_db, cursor_db):
    global chatroom_dict

    random_num = request_tcp_split[1]
    if(random_num != "aaa"):
        # get the username
        cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (random_num, ))
        chatroom_name = cursor_db.fetchone()[0]

        chatroom_port = chatroom_dict.get(chatroom_name)[0]
        chatroom_dict[chatroom_name] = (chatroom_port, "close")

    response_tcp = "Welcome back to BBS."
    
    client.send(response_tcp.encode())

def handle_restart_chatroom(request_tcp_split, client, connect_db, cursor_db):
    global chatroom_dict

    random_num = request_tcp_split[1]
    if(random_num == "aaa"):
        response_tcp = "Please login first."
    
    else:
        # get the username
        cursor_db.execute('''SELECT username
                        FROM login_user
                        WHERE random_num = ?''', (random_num, ))
        chatroom_name = cursor_db.fetchone()[0]


        if(chatroom_dict.get(chatroom_name) == None):
            response_tcp = "Please create chatroom first."
       
        elif(chatroom_dict.get(chatroom_name)[1] == "open"):
            response_tcp = "Your chatroom is still running."

        else:
            chatroom_port = chatroom_dict.get(chatroom_name)[0]
            chatroom_dict[chatroom_name] = (chatroom_port, "open") 
            response_tcp = "start to create chatroom server..."
        
        client.send(response_tcp.encode())










#create udp socket and deal with udp request
def create_udp_socket(connect_db, cursor_db):
    #create udp socket
    socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_udp.bind((HOST,PORT))
    
    while True:
        #get the request from client
        request_udp, addr_udp = socket_udp.recvfrom(1024)
        #decode and split the udp request
        request_udp = request_udp.decode()
        request_udp_split = request_udp.split(' ')        
        
        if (request_udp_split[0] == "register"):
            handle_register(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db)
            
        elif (request_udp_split[0] == "whoami"):
            handle_whoami(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db)

        elif request_udp_split[0] == "list-chatroom":
            handle_list_chatroom(request_udp_split, socket_udp, addr_udp, connect_db, cursor_db)
        
    socket_udp.close()


    
#deal with tcp request
def response_tcp_request(client, addr, connect_db, cursor_db):
    #receive the request from client
    while True:
        request_tcp = client.recv(1024)
        #decode and split the tcp request
        request_tcp = request_tcp.decode()
        request_tcp_split = request_tcp.split(' ')
        
        if request_tcp_split[0] == "login":
            handle_login(request_tcp_split, client, connect_db, cursor_db)                
       
        elif request_tcp_split[0] == "list-user":
            handle_listuser(request_tcp_split, client, connect_db, cursor_db) 

        elif request_tcp_split[0] == "logout":
            handle_logout(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "exit":
            client.close()
            break
        
        elif request_tcp_split[0] == "create-board":
            handle_create_board(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "create-post":
            handle_create_post(request_tcp, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "list-board":
            handle_list_board(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "list-post":
            handle_list_post(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "read":
            handle_read(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "delete-post":
            handle_delete_post(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "update-post":
            handle_update_post(request_tcp, client, connect_db, cursor_db)
        
        elif request_tcp_split[0] == "comment":
            handle_comment(request_tcp, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "create-chatroom":
            handle_create_chatroom(request_tcp, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "join-chatroom":
            handle_join_chatroom(request_tcp, client, connect_db, cursor_db)
        
        elif request_tcp_split[0] == "leave-chatroom":
            handle_leave_chatroom(request_tcp_split, client, connect_db, cursor_db)

        elif request_tcp_split[0] == "restart-chatroom":
            handle_restart_chatroom(request_tcp_split, client, connect_db, cursor_db)



    
def create_tcp_socket(connect_db, cursor_db):
    # create tcp socket
    socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_tcp.bind((HOST,PORT))
    socket_tcp.listen(10)

    while True:
        #get the client information
        client, addr = socket_tcp.accept() #client存串接對象、addr存連線資訊
        print("New Connection.")
        #send welcome message to client
        welcome = "********************************\n**Welecome to the BBS server. **\n********************************"
        client.send(welcome.encode())
        #wait for tcp request
        thread_tcp = threading.Thread(target = response_tcp_request, args = (client, addr, connect_db, cursor_db,))
        thread_tcp.start()
    
#connect to database
connect_db = sqlite3.connect('bbs_board.db', check_same_thread = False)
cursor_db = connect_db.cursor()

#create a table which is named user
cursor_db.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL,
                    password TEXT NOT NULL
                    )''')

#create a table which is named login_user
cursor_db.execute('''CREATE TABLE IF NOT EXISTS login_user(
                    random_num INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL
                    )''')

#create a table which is named board
try:
    cursor_db.execute("DROP TABLE board")
    cursor_db.execute('''CREATE TABLE IF NOT EXISTS board(
                        board_index INTEGER PRIMARY KEY AUTOINCREMENT,
                        board_name TEXT NOT NULL UNIQUE,
                        board_moderator TEXT NOT NULL)
                        ''')
except:
    cursor_db.execute('''CREATE TABLE IF NOT EXISTS board(
                        board_index INTEGER PRIMARY KEY AUTOINCREMENT,
                        board_name TEXT NOT NULL UNIQUE,
                        board_moderator TEXT NOT NULL)
                        ''')

connect_db.commit()    

# create tcp socket
#socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#socket_tcp.bind((HOST,PORT))
#socket_tcp.listen(5)

#create a thread for udp socket
thread_udp = threading.Thread(target = create_udp_socket, args = (connect_db, cursor_db,))
thread_udp.start()

#create a thread for tcp socket
thread_tcp = threading.Thread(target = create_tcp_socket, args = (connect_db, cursor_db,))
thread_tcp.start()