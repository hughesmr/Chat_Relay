#!/usr/bin/python

# ================
# Class inclusions
# ========
import sys
import threading
import time
import select
from socket import *
import socket
import pipes
import os
from stat import *
from multiprocessing import Pipe
# ==================

sem = threading.BoundedSemaphore()     # Semphore for rooms list
rooms=[]     # List of available rooms
pip = []     # List of pipes currently active
users = []   # User list
endServe = []
global passW



# =================
# Function findRoom
# ================
def findRoom(name):
    i = 0
    
    while i < len(rooms): # Determine if room exists
        if name == rooms[i][0]:
            rmNum = i
        i += 1
    return rmNum

# =================
# Function chatRoom
# ======================
def chatRoom(chatFd, p, rmName, userName):
    
    message = ''     # Variable to hold message
    contactList = [] # List of contatcts
    
#   ---------------------
#   ChatRoom control loop
#   ---------------------
    while message != "Q": # While chatRoom active
        
        sem.acquire() # Aquire semephore lock
        
        p = findRoom(rmName) # Check if postion changed
        
        if len(rooms) >= p: # Prevent buffer overrun
            
            p = findRoom(rmName) # Check if postion changed
            
            if len(rooms[p]) != 0 and len(rooms[p]) < 3: # Wait for more people to enter the chat room
                
                p = findRoom(rmName) # Check if postion changed
                sem.release() # Release semephore lock
                
                chatFd.send("Chatroom empty, waiting for more members (type 'ZZ' to get more options).") # Send owner options message
                
                while len(rooms[p]) < 3 and message != "Q":
                    inp,out,exc = select.select([chatFd, 0],[],[], 1) # Wait for socket to read
               
                    for l in inp: # For read from available sockets
                        message = l.recv(1024)  # Get message
                    sem.acquire()
                    p = findRoom(rmName) # Check if postion changed
                    sem.release()
        
            else: # Else enouch people
                sem.release()
        else: # Else p not in rooms
            sem.release()
    
        sem.acquire()
        p = findRoom(rmName) # Check if postion changed
        tempList = rooms[p] # Get the current list of contacts
        sem.release()
    
        i = 1
        contactList = []         # List of contatcts
        while i < len(tempList): # While create list of sockets
            contactList.append(tempList[i])
            i += 1

#       --------------
#       Main chat loop
#       ------------------
        if message != "Q": # If not closing chatRoom
            
            message = '' # Reset message
            inp,out,exc = select.select(contactList,[],[], 1) # Wait for socket to read

            for l in inp: # For read from available sockets
                mm = l.fileno()
                message = ''            # Reset message
          
                if l in pip: # If pipe connection
                    
                    message = l.recv()  # Get message from pipe
                    
                else: # Else socket connection
                    message = l.recv(1024) # Get message from socket
               
                            
                message.strip()# Strip chars
            
                if message == "Q": # If member leaving or closing chatRoom
                    if l == chatFd: # If owner closing room
                        j = 0
                        while j < len(contactList): # While contacts to send to
                            if l != contactList[j]: # If message not being sent to sender
                                contactList[j].send("Q")# Send quit to all members
                            j += 1
                    else: # Else member leaving room
                        sem.acquire()
                        tempList = rooms[p]
                        tempList.remove(l)  # Remove chatRoom from rooms
                        pip.remove(l)
                        rooms[p] = tempList # Add new member list back to rooms
                        sem.release()
                        message = ''        # Reset message
    
            
                else: # No one leaving or closing chatRoom
                    j = 0
                    while j < len(contactList): # While contacts to send to
                        if l != contactList[j]: # If message not being sent to sender
                            contactList[j].send(message)
                        j += 1
#   --------------------------
#   End chatRoom control loop
#   -------------------------
                            
    sem.acquire()
    rooms.pop(p) # Remove chatRoom from rooms
    sem.release()
#   =============
#   End chatRoom
#   ============

# ===============
# Function inRoom
# ===================
def inRoom(fd, a, b, userName):
        
    rc = ''
    a.send(userName.rstrip('\n') + " " + "joined the chat room.")
    while rc != "Q":
        rc = ''
        inp,out,exc = select.select([fd,a],[],[]) # Wait for socket or user
        for i in inp: # For current data to send/read
            if i == fd: # If client sent data
                rc = fd.recv(1024)
                
                if rc == "QQ": # If QQ gets sent instead of Q
                    rc = "Q"
                    a.send(userName.rstrip('\n') + " left chat room.")
                    time.sleep(1)
                    a.send(rc)
                else:
                    a.send(rc)
            else: # If data being sent from room
                rc = a.recv()
                fd.send(rc)

    if rc == "Q": # If no error leaving chatRoom
        time.sleep(1)
        
        a.close()
        b.close()
#   =============
#   End inRoom
#   ==========

# ======================
# Function clientControl
# =====================================
def clientControl(fd, addr):
    
    rc = '' # Variable to hold recieve value
    global passW
    userName = fd.recv(1024) # Get user name
    users.append(userName) # Add to users
    
    while rc != "QUIT": # While user connected to server
    
        rc = fd.recv(1024) # Get user input
        
#       ============== 
        if rc == "LR": # If user selects List Rooms
  
            if len(rooms) == 0:    # If no rooms available
                fd.send("No rooms available")
            else:          # Else rooms available
                i = 0
                string = '' # Variable to temporarily hold rooms
                if len(rooms) != 0:
                    while i < len(rooms): # While rooms to add
                        string = string + " " + rooms[i][0]
                        i += 1
                
                fd.send(string) # Send rooms to client
    
#       ==================
        elif rc == "JOIN": # If user joins room
            
            found = False # Variable to determine if room exists
            
            fd.send("OK") # Send acknowledgment to client
            rm = fd.recv(1024) # Recieve name of chat room

            i = 0
            sem.acquire() 
            while i < len(rooms): # Determine if room exists
                if rm == rooms[i][0]:
                    found = True
                    rmNum = i
                i += 1
            
            if found == True: # If room found
                fd.send("OK") # Send acknowledgment to client
                subList = []  # Sublist to temporary hold new list
                subList = rooms[rmNum]
                
                
                a, b = Pipe() # Create a pip for communication between threads
                pip.append(b) # Add to pip list (SO ROOM KNOWS HOW TO RECV DATA)
                subList.append(b) # Add b to room joined (SO ROOM KNOWS WHO TO CONTACT)
                    
                rooms[rmNum] = subList # Add new member to chat room
                sem.release() # Release semephore
               
                inRoom(fd, a, b, userName) # Enter chat room
                    
            else: # Room not found
                sem.release() # Release semephore
                fd.send("ER") # SEND TO USER
            
                    
#       ================
        elif rc == "CR": # If user creates room
            
            found = False # Variable to determine if room exists
            i = 0
            fd.send("OK") # Send acknowledgement to client
            rc = fd.recv(1024) # Recieve name of chatRoom
            
            sem.acquire()
            while i < len(rooms): # Determine if room exists
                if rc == rooms[i][0]:
                    found = True
                    rmNum = i
                i += 1
            sem.release()
            
            if found == False: # If room found
                
                fd.send("OK")
                sem.acquire()
                rooms.append(rc) # Add new chatRoom
                p = rooms.index(rc)
  
                rmNum = rooms.index(rc)
                subList = []
                m = rooms[rmNum]
                subList.append(m) 
                subList.append(fd)
                rooms[rmNum] = subList # Add owner to chatRoom
                sem.release()
                
                
                
              #  tempName = []
                
              #  p = users.index(userName)
              #  temp = users[p]
                
              #  tempName.append(temp)
              #  tempName.append(rc)
                
                
                
                chatRoom(fd, p, rc, userName) # Create chatRoom

            else: # Room already exists
                fd.send("ER")

#       ================
        elif rc == "USE":
            
            if len(users) == 1 or len(users) == 0:    # If no rooms available
                fd.send("No users available")
            else:          # Else rooms available
                i = 0
                string = '' # Variable to temporarily hold rooms
                    
                while i < len(users): # While rooms to add
                    if users[i] != userName:
                        string = string + " " + users[i]
                    i += 1
                fd.send(string) # Send rooms to client
#
        elif rc == "CMD":
            fd.send("OK")
            rc = fd.recv(1024) # Recieve name of chatRoom
            
            if rc == passW:
                fd.send("OK") # Recieve name of chatRoom
                a, b = Pipe() # Create a pip for communication between threads
                endServe.append(b)
                rc = fd.recv(1024)
                a.send(rc)
                rc = "QUIT"
            else:
                fd.send("ER") # Recieve name of chatRoom
#       ===============
        elif rc == "QUIT": # Else if user quiting
            fd.send("OK")

    users.remove(userName)
    fd.close() # Close socket of client
#   ===================================

# =============
# Function Main
# =================
def main(argv=None):
    
    i = 0             # Varaible to increment
    end = 1
    threads = []      # List of threads
    global passW
    
    print "Enter server password:"
    passW = sys.stdin.readline().strip()
       
    try: # Try to create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create socket
        
    except socket.error, msg: # If error creating socket
        print "Socket creation failed: " + str(msg[0]) + ": " + msg[1]
        sys.exit()
                
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Set socket options
        
    s.bind(('', 30006))      # Bind socket to port 30005
            
    endServe.append(s) # Add s so select knows what to listen to
    endServe.append(0) # Add zero since select requires a list
    print "Server running ..."
    s.listen(5)              # Listen for connection
            
    while end == 1:

        inp,output,exc = select.select(endServe,[],[], 1) # Wait for input
        
        
        for i in inp:
            if i == s:
                client,addr = s.accept() # Accept connection from client
                client.send("OK")        # Aknowledge connection
                x,y = addr               # Get address of client
            
                rc = client.recv(1024) # Determine if server or client connection
            
                if rc == "C": # If client connection
                    t = threading.Thread(target=clientControl, args=(client,x,)) # Create thread
                    threads.append(t) # Add thread to thread list
                    t.start()         # Start thread

                else: # Else unknown connection
                    print "Unknown connection: Disconnecting:"
                    client.close()
        
            elif rc == 0: # 0 only used since a list is needed for select
                 m = 5
            else: # Allow user to end server
                rc = i.recv()
                if rc == "SQUIT":
                    end = 0
                    print "SERVER QUITING"

# ===============

if __name__ == "__main__":
    main()