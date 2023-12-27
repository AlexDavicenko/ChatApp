import socket
import logging
import json
import sys
import time
from datetime import datetime
from threading import Thread, Event
from controller_protocol import Controller

import sys
sys.path.append('../')
from communication_protocol.communicationProtocol import send_bytes, listen_for_bytes
from communication_protocol.TCPMessages import *
sys.path.append('client/')
import pickle

class Client():
    def __init__(self, controller: Controller, offline_mode = False) -> None:
        self.controller = controller
        self.close_event = Event()
        
        self.PORT = 8080
        #172.20.4.155
        #192.168.0.73
        #192.168.0.83
        #172.20.4.155
        self.HOST = "192.168.0.73"
        
        if offline_mode: return
        self.server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.server_conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 102400)
        self.server_conn.connect((self.HOST, self.PORT))

        logging.info(f"Connected to server {self.HOST, self.PORT}")

    def user_input(self):
        while not self.close_event.is_set():
            try:
                msgs =  self.controller.get_outgoing_msgs()
                if msgs:
                    for msg in msgs:
                        logging.info(f"[MESSAGE SENT] {msg}")
                    self.send_msg(msgs)
                    time.sleep(0.05)
                else:
                    time.sleep(0.05)

            except Exception as e:
                logging.error(str(e))
                self.close_event.set()


    def server_messages(self):
        while not self.close_event.is_set():
            try:

                msgs = self.receive_msg()
                for msg in msgs:                  
                    logging.info(f"[MESSAGE RECEIVED] {msg}")

                    if isinstance(msg, NewMessageNotif):
                        self.controller.recieve_incoming_msg(msg)

                    elif isinstance(msg, LoginResponse):
                        if msg.success:
                            self.controller.login_approved()
                        else:
                            self.controller.login_failed()
                    
                    elif isinstance(msg, ChannelCreateResponse):
                        if msg.success:
                            self.controller.create_channel(
                                msg.channel_id,
                                msg.channel_name
                            )
                    elif isinstance(msg, ChannelJoinResponse):
                        if msg.success:
                            self.controller.join_channel(
                                msg.channel_id,
                                msg.channel_name
                            )
                    elif isinstance(msg, ChannelLeaveNotif):
                        self.controller.user_left_channel_update(msg.channel_id, msg.username)

                    elif isinstance(msg, UserJoinNotif):
                        self.controller.user_join_channel_update(msg.channel_id, msg.username, msg.firstname, msg.lastname)
                    
                    elif isinstance(msg, SearchReponse):
                        self.controller.search_response(msg.response_data)
                    elif isinstance(msg, SignUpResponse):
                        if msg.success:
                            #Same procedure as login
                            self.controller.login_approved()
                    elif isinstance(msg, FriendRequestNotif):
                        self.controller.friend_request_recieved(msg.username, msg.firstname, msg.lastname)

                    elif isinstance(msg, FriendRemoval):
                        self.controller.remove_friend_notif(msg.username)

                    elif isinstance(msg, FriendRequestDecision):
                        self.controller.friend_request_decision(msg.username, msg.success)

                    elif isinstance(msg, FriendStatusNotif):
                        self.controller.friend_status_notif(msg.username, msg.firstname, msg.lastname, msg.decision)

            except (ConnectionResetError, ConnectionAbortedError) as e:
                logging.error(e)
                self.close_event.set()

    def receive_msg(self):
        msg = pickle.loads(listen_for_bytes(self.server_conn))
        return msg


    def send_msg(self, msg: TCPMessage):
        send_bytes(self.server_conn, pickle.dumps(msg))


    
    def close(self):
        self.server_conn.close()


    def start(self):

        #TODO: 
        #   split into different files and classes
        Thread(target=self.user_input, args=()).start()
        Thread(target=self.server_messages, args=()).start()
    
