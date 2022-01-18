#!/usr/bin/python3
import socket
import sys
import threading
import select
import datetime

#server information
HOST = sys.argv[1]
PORT = int(sys.argv[2])

#create tcp socket
socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_tcp.connect((HOST, PORT))

#create udp socket
socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_udp.connect((HOST, PORT))

 # create tcp socket for chat room
socket_tcp_chatroom = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



#receive welcome message from server
welcome = socket_tcp.recv(1024)
print (welcome.decode())



login_user = "idk"
random_num = "aaa"
inputs = [sys.stdin,]
chatroom_status = 0 # is not created yet, 1 is open, 2 is close 
attach_chatroom = 0
chatroom_special_thread_on = 0
leave_chatroom = 0
exit_status = 0
client_leave_chatroom = 1
the_last_three_message = []
PORT_chatroom = 0

def chatroom_accept_client():
    global inputs, chatroom_status, exit_status, the_last_three_message, socket_tcp_chatroom
    #print(chatroom_status)
    #print(exit_status)

    while (chatroom_status == 1 and exit_status == 0):
        #print("chatroom_accept_client1")
        readable, _, _ = select.select([socket_tcp_chatroom,], [], [], 0.1)

        for new_connection in readable:

            #get the chatroom client information
            new_chatroom_client, new_chatroom_addr = socket_tcp_chatroom.accept()
            inputs.append(new_chatroom_client)

            new_client_name = new_chatroom_client.recv(1024).decode()


            welcome = "****************************\n**Welecome to the chatroom**\n****************************"
            for i in range(len(the_last_three_message)):
                welcome += '\n' + the_last_three_message[i]
                
            new_chatroom_client.send(welcome.encode())

            time = datetime.datetime.now()
            current_time = "[" + str(time.hour) + ":" + str(time.minute) + "]: "
            join_message = "sys" + current_time + new_client_name + " join us."

            print(join_message)
            for chatroom_client in inputs:                
                if(chatroom_client != sys.stdin and chatroom_client != new_chatroom_client):
                    chatroom_client.send(join_message.encode())


def chatroom_owner_detach():
    global login_user, inputs, chatroom_special_thread_on, the_last_three_message
   
    while (chatroom_special_thread_on and exit_status == 0):
        readable, _, _ = select.select(inputs, [], [], 0.1)

        time = datetime.datetime.now()
        current_time = "[" + str(time.hour) + ":" + str(time.minute) + "]: "

        for message_sender in readable:
            if(message_sender != sys.stdin):

                message_recieved = message_sender.recv(1024).decode()
                message_recieved_splited = message_recieved.split("#####")

                # the client closed the socket(leave-chatroom)
                if(message_recieved_splited[0] == "leave-chatroom"):
                    message = "sys" + current_time + message_recieved_splited[1] + " leave us"
                    # print(message)
                    for chatroom_client in inputs:
                        
                        if (chatroom_client != sys.stdin and chatroom_client != message_sender) :
                                chatroom_client.send(message.encode())

                elif(message_recieved == ""):
                    inputs.remove(message_sender)
                
                # the client sent message
                else:                    
                    #message_recieved = message_recieved.split("#####")
                    message = message_recieved_splited[1] + current_time + message_recieved_splited[0]

                    if(len(the_last_three_message) == 3):
                        del the_last_three_message[0]
                    the_last_three_message.append(message)

                    #print(message)

                    # send the message to other chatroom clients
                    for chatroom_client in inputs:
                        if (chatroom_client != sys.stdin and chatroom_client != message_sender) :
                                chatroom_client.send(message.encode())

def chatroom_gogo(thread_chatroom_connect):
    global chatroom_status, attach_chatroom, login_user, inputs, socket_tcp_chatroom, chatroom_special_thread_on, socket_tcp_chatroom, the_last_three_message
    # print welcome message
    print("****************************\n**Welecome to the chatroom**\n****************************")

    for i in range(len(the_last_three_message)):
        message = the_last_three_message[i]
        print(message)

    attach_chatroom = 1
    if(chatroom_special_thread_on == 1):
        chatroom_special_thread_on = 0


    while (attach_chatroom and chatroom_status == 1):

        readable, _, _ = select.select(inputs, [], [], 0.1)

        time = datetime.datetime.now()
        current_time = "[" + str(time.hour) + ":" + str(time.minute) + "]: "

        for message_sender in readable:
            
            # message from the server itself
            if message_sender == sys.stdin:
                message = sys.stdin.readline().rstrip('\n')
                # the chatroom owner wants to detach

                if (message == "detach"):
                    attach_chatroom = 0
                    chatroom_special_thread_on = 1
                    #create a new thread for chatroom when the owner detach
                    thread_chatroom_owner_detach = threading.Thread(target = chatroom_owner_detach, args = ())
                    thread_chatroom_owner_detach.start()


                    print("Welcome back to BBS.")
                    break

                elif (message == "leave-chatroom"):
                    message = "the chatroom is close."
                    for chatroom_client in inputs:
                        if chatroom_client != sys.stdin:
                            chatroom_client.send(message.encode())
                    # change chatroom status to 2
                    chatroom_status = 2
                    break          

                else:
                    message = login_user + current_time + message

                    if(len(the_last_three_message) == 3):
                        del the_last_three_message[0]
                    the_last_three_message.append(message)

                    # send the message to other chatroom clients
                    for chatroom_client in inputs:
                        if chatroom_client != sys.stdin:
                            chatroom_client.send(message.encode())   

            # message is from other chatroom client
            else:
                message_recieved = message_sender.recv(1024).decode()
                message_recieved_splited = message_recieved.split("#####")

                # the client closed the socket(leave-chatroom)
                if(message_recieved_splited[0] == "leave-chatroom"):
                    message = "sys" + current_time + message_recieved_splited[1] + " leave us"
                    print(message)
                    for chatroom_client in inputs:
                        #message = "sys" + current_time + message_recieved_splited[1] + " leave us"
                        if (chatroom_client != sys.stdin and chatroom_client != message_sender) :
                                chatroom_client.send(message.encode())

                elif(message_recieved == ""):
                    inputs.remove(message_sender)
                
                # the client sent message
                else:                    
                    #message_recieved = message_recieved.split("#####")
                    message = message_recieved_splited[1] + current_time + message_recieved_splited[0]

                    if(len(the_last_three_message) == 3):
                        del the_last_three_message[0]
                    the_last_three_message.append(message)

                    print(message)

                    # send the message to other chatroom clients
                    for chatroom_client in inputs:
                        if (chatroom_client != sys.stdin and chatroom_client != message_sender) :
                                chatroom_client.send(message.encode())

        # leave-chatroom
        if(chatroom_status == 2):
            socket_tcp_chatroom.close()

            request = "leave-chatroom " + random_num
            #send message to server by tcp
            socket_tcp.send(request.encode())
            #receive data from server by tcp and print it out
            response_tcp = socket_tcp.recv(1024).decode()
            print(response_tcp)


#thread_chatroom_connect = threading.Thread(target = chatroom_accept_client, args = ())
socket_tcp_chatroom = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
def create_chatroom():
    global PORT_chatroom,exit_status, chatroom_status, socket_tcp_chatroom, thread_chatroom_connect, the_last_three_message, inputs,socket_tcp_chatroom
    
    # create tcp socket for chat room
    socket_tcp_chatroom = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_tcp_chatroom.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_tcp_chatroom.bind((HOST, int(PORT_chatroom)))
    socket_tcp_chatroom.listen(10)

    # change chatroom_status to 1
    chatroom_status = 1
    exit_status = 0
    inputs = [sys.stdin,]

    thread_chatroom_connect = threading.Thread(target = chatroom_accept_client, args = ())
    thread_chatroom_connect.start() 

    # # print welcome message
    # print("****************************\n**Welecome to the chatroom**\n****************************")

    # for i in range(len(the_last_three_message)):
    #     message = the_last_three_message[i]
    #     print(message)


    # handle messages from all the chatroom clients
    chatroom_gogo(thread_chatroom_connect)



while True:

    #get command from user
    request = input("% ")
    #split the request
    request_split = request.split(' ')

    
    #using udp
    if (request_split[0] == "register"):
        #send message to server by udp
        socket_udp.sendto(request.encode(), (HOST, int(PORT)))
        #receive message from server by udp and print it out
        response_udp, addr_server = socket_udp.recvfrom(1024)
        print (response_udp.decode())


    elif (request_split[0] == "whoami") :
        #add the random_num to the end of request
        request = request + " " + random_num
        #send message to server by udp
        socket_udp.sendto(request.encode(), (HOST, int(PORT)))
        #receive message from server by udp and print it out
        response_udp, addr_server = socket_udp.recvfrom(1024)
        print (response_udp.decode())


    #using tcp    
    elif(request_split[0] == "login"): 
        #add the random_num to the end of request
        request = request + " " +random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp
        response_tcp = socket_tcp.recv(1024)
        #split the response from tcp to distinguish the ramdom_num from the respinse message
        response_tcp_split = response_tcp.decode().split('#')
        print(response_tcp_split[0])
        #change the random_num
        if(len(request.split(' ')) == 4 and random_num == "aaa"):
            random_num = response_tcp_split[1]
        #store the login user name
        if (response_tcp_split[0] != "Please logout first." and response_tcp_split[0] != "Login failed." and response_tcp_split[0] != "Usage: login <username> <password>"):
            login_user = response_tcp_split[2]


            
    elif (request_split[0] == "logout") :        
        request = request + " " + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp
        response_tcp = socket_tcp.recv(1024)
        #split the response from tcp to distinguish the ramdom_num from the respinse message
        response_tcp_split = response_tcp.decode().split('#')
        #print out the response message
        print (response_tcp_split[0])
        #change the random_num
        random_num = response_tcp_split[1]  

   
    elif (request_split[0] == "list-user"):
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())

        
    elif (request_split[0] == "exit"):
        exit_status = 1
        chatroom_status = 2
        leave_chatroom = 1
        try:
            thread_chatroom_connect.join()
            thread_chatroom_owner_detach.join()
            break
        except:
            break


    elif (request_split[0] == "create-board"):
        request = request + " " + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())

    
    elif (request_split[0] == "create-post"):
        request = request + "#####" + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "list-board"):
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "list-post"):
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "read"):
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "delete-post"):
        request = request + " " + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "update-post"):
        request = request + "#####" + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "comment"):
        request = request + "#####" + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024)
        print (response_tcp.decode())


    elif (request_split[0] == "create-chatroom"):
        PORT_chatroom = request.split(' ')[1]
        request = request + "#####" + random_num
        # send message to server by tcp
        socket_tcp.send(request.encode())
        # receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024).decode()
        print (response_tcp)

        if(response_tcp == "start to create chatroom..."):
            

            create_chatroom()

            
            

    elif(request_split[0] == "join-chatroom"):
        client_leave_chatroom = 0
        chatroom_name = request_split[1]
        request = request + "#####" + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024).decode()

        # hasn't login or the chatroom is not available
        if(response_tcp == "Please login first." or response_tcp == "The chatroom does not exist or the chat room is closed."):
            print (response_tcp)

        #chatroom exist, connect to the chat room server
        else:

            socket_tcp_chatroom_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_tcp_chatroom_server.connect((HOST, int(response_tcp))) # response_tcp is the port of the chat room



            socket_tcp_chatroom_server.send(login_user.encode())



            welcome = socket_tcp_chatroom_server.recv(1024)
            print (welcome.decode())

            client_inputs = [sys.stdin, socket_tcp_chatroom_server, ]

            while (client_leave_chatroom == 0):
                readable, _, _ = select.select(client_inputs, [], [], 0.1)

                for message_sender in readable: 
                    # messeage from the client itself
                    if(message_sender == sys.stdin):
                        send_message = sys.stdin.readline().rstrip('\n')

                        # client leave-chatroom
                        if(send_message == "leave-chatroom"):
                            client_leave_chatroom = 1
                            send_message += "#####" + login_user                            
                            socket_tcp_chatroom_server.send(send_message.encode())
                            socket_tcp_chatroom_server.close()

                            request = "leave-chatroom aaa"
                            #send message to server by tcp
                            socket_tcp.send(request.encode())
                            #receive data from server by tcp and print it out
                            response_tcp = socket_tcp.recv(1024).decode()
                            print(response_tcp)
                            break

                        else:
                            send_message += "#####" + login_user
                            socket_tcp_chatroom_server.send(send_message.encode())

                    # message from other message 
                    else:
                        message_recieved = socket_tcp_chatroom_server.recv(1024).decode()
                        if(message_recieved == "the chatroom is closed"):
                            time = datetime.datetime.now()
                            current_time = "[" + str(time.hour) + ":" + str(time.minute) + "]: "
                            message_recieved = "sys" + current_time + message_recieved
                            print(message_recieved)
                            client_leave_chatroom = 1
                            request = "leave-chatroom " + "aaa"
                            #send message to server by tcp
                            socket_tcp.send(request.encode())
                            #receive data from server by tcp and print it out
                            response_tcp = socket_tcp.recv(1024).decode()
                            print(response_tcp)
                            break
                        else:
                            print (message_recieved)


    elif (request_split[0] == "attach"):
        # hasn't login
        if (random_num == "aaa"):
            print("Please login first.")
        
        # the chatroom hasn't been created
        elif (chatroom_status == 0):
            print("Please create-chatroom first.")

        # the chatroom is closed
        elif (chatroom_status == 2):
            print("Please restart-chatroom first.")

        else:
            chatroom_gogo(thread_chatroom_connect)

    elif (request_split[0] == "restart-chatroom"):
        request = request + " " + random_num
        #send message to server by tcp
        socket_tcp.send(request.encode())
        #receive data from server by tcp and print it out
        response_tcp = socket_tcp.recv(1024).decode()
        print(response_tcp)

        if(response_tcp == "start to create chatroom server..."):
            chatroom_status = 1
            create_chatroom()




    # udp
    elif (request_split[0] == "list-chatroom"):
        request = request + " " + random_num
        #send message to server by udp
        socket_udp.sendto(request.encode(), (HOST, int(PORT)))
        #receive message from server by udp and print it out
        response_udp, addr_server = socket_udp.recvfrom(1024)
        print (response_udp.decode())