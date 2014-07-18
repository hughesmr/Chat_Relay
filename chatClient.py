#!/usr/bin/python

# ================
# Class Inclusions
# ========
import sys
import threading
import time
import select
import socket

# =================
# Function chatRoom
# ===========================
def chatRoom(sock, userName):
    
    print "Enter 'ZZ' to get chatRoom options" # Instructions

    #message = userName.rstrip('\n') + " " + "joined the chat room."
    time.sleep(1)
    #sock.send(message)
    
    message = '' # Variable to hold message
    while message != "Q":

        inp,out,exc = select.select([0,sock],[],[]) # Wait for socket or user data

        for i in inp: # For current data to send/read
            if i == 0: # If user sending message
                message = sys.stdin.readline().strip() # Get message to send
                if message == "ZZ": # If user wants menu
                    print "Enter 'Q' to leave chat room"
                    message = sys.stdin.readline().strip()
                    if message == "Q":
                        sock.send(message)

                else:
                    if message != "Q":
                        message = userName.rstrip('\n') + ": " + message
                    else:
                        message = "Q'"
                    sock.send(message)

            else: # Else from socket
                message = sock.recv(1024)
                if message != "Q": # Message sent
                    print message
                else: # Room being closed
                    print "Room being closed by owner"

# ==================
# Function roomOwner
# ==============================
def roomOwner(chatFd, userName):
    
    print "Enter 'ZZ' to get chatRoom options"

    message = ''
    while message != "Q":
    
        inp,output,exc = select.select([0,chatFd],[],[]) # Wait for input
    
        for i in inp:
            if i == 0: # If user input
                message = sys.stdin.readline().strip()
                if message == "ZZ":
                    print "Enter 'Q' to leave chat room"
                    message = sys.stdin.readline().strip()
                    if message == "Q":
                        chatFd.send("Q")
            
                else: # Else input from server
                    if message != "Q":
                        message = userName.rstrip('\n') + ": " + message
                    chatFd.send(message)
        
            else:
                message = chatFd.recv(1024) 
                print message
    

# =============
# End roomOwner
# =============

# =============
# Function chat
# =============
def chat(sock):
    
    print "Please enter your user name:"
    userName = sys.stdin.readline()
    sock.send(userName) # Send server user name
    
    ch = ''
    
    while ch != 'q': # While user connected to server
        
        print "Please make a selection:"
        print "List Rooms   (lr)"
        print "List Peers   (lp)"
        print "Join Room    (jr)"
        print "Create Room  (cr)"
        print "Command mode (cm) (password required)" 
        print "Quit         (q)"

        ch = sys.stdin.readline().strip() # Get selection
        
#       =============
        if ch == "lr":
            sock.send("LR")
            rc = sock.recv(1024)
            print "Rooms currently available: \n"
            print rc + "\n"
    
#       ================
        elif ch == "lp":
            sock.send("USE")
            rc = sock.recv(1024)
            print "Users currently online: \n"
            print rc + "\n"
    
#       ====================================
        elif ch == "jr": # If join chat room
            sock.send("JOIN")
            rc = sock.recv(1024) # Throw exception if not OK !!
        
            print "Please enter the name of the chatroom to join:"
            rmName = sys.stdin.readline().strip()
            sock.send(rmName)
            rc = sock.recv(1024)# Throw exception if not OK
            ans,space,portNum = rc.partition(" ")
            if ans == "OK":
            
                chatRoom(sock, userName) #
                sock.send("Q")
                
            else:
                print "Room '"+ rmName +"' not found"
                
#       ===================================
        elif ch == "cr": # Create chat room
            
            sock.send("CR")
            rc = sock.recv(1024)
            print "Please enter a name for your chat room:"
            rmName = sys.stdin.readline().strip()
            sock.send(rmName)
            rc = sock.recv(1024) # Throw exception if not OK

            if rc == "OK":
                
                roomOwner(sock, userName)
                
            else:
                print "Error room '"+rmName+"' already exists"


#       ===================================
        elif ch == "cm": # Command mode

            sock.send("CMD")
            rc = sock.recv(1024)
            print "Please enter server password:"
            passW = sys.stdin.readline().strip()
            sock.send(passW)
            rc = sock.recv(1024)
            if rc == "OK":
                sock.send("SQUIT")
                print "Server closing, logging off..."
                ch = 'q'
            else:
                print "Incorrect password!"


#       ================================
        elif ch == "q": # Quit server
            sock.send("QUIT")
            rc = sock.recv(1024)
            if rc == "OK":
                print "Disconnecting from server " + rc
            else:
                print "Error disconnecting from server"

#       =============================================
        else: # Input not recognized
            print "input not recognized, re-enter"

#  ========
#  End chat
#  ========

# =============
# Function Main
# =================
def main(argv=None):

    print "Please enter ip address or host name to connect to."
    ip = sys.stdin.readline().strip() # Get ip/host to connect to
    
    try: # Try to create connection
        chatFd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as msg: # If error occurs
        print "Error creating socket: " + msg[0] + ": " + msg[1]
        sys.exit()
            

    chatFd.connect((ip, 30006)) # Connect to server
    time = chatFd.gettimeout()
    chatFd.settimeout(3.0) # Set time out to prevent long connection times with server
    m = ''
    try: # Get server response
        m = chatFd.recv(1024) # Recieve OK make exception
    except socket.error as msg: # If timeout occurs
        print "Connection error, server response " + str(msg) + "."
        sys.exit()

    if m == "OK": # If connection successful
        chatFd.settimeout(time)
        chatFd.send("C")
        print "Connection Successful"
        chat(chatFd)
    else: # If connection fails
        print "Close Chat Service"
        sys.exit(0)
    
    chatFd.close()

if __name__ == "__main__":
    main()
