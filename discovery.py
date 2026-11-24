import json
from socket import *
import os
import asyncio
from connection import read_input

UDP_PORT = 9999

async def beacon(nickname, ID, port):
    MESSAGE = json.dumps({"id": ID, "name": nickname, "port": port})

    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    try:
        while True:
            s.sendto(bytes(MESSAGE, 'utf-8'),('<broadcast>', UDP_PORT)) # As of python3.x message must be turned into bytes instead of sttr
            await asyncio.sleep(3)
    finally:
        s.close()

async def find_clients(my_id, clients):
    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # Just for testing so i can run 2 instances on my machine
    s.bind(("0.0.0.0", UDP_PORT))
    s.setblocking(False)

    loop = asyncio.get_running_loop()

    try:
        while True: # Keep on listening, without it one packet and close
            data, addr = await loop.sock_recvfrom(s, 4096)
            try:
                msg = json.loads(data)
                peer_id, name, port = msg["id"], msg["name"], msg["port"]
            except(ValueError, TypeError, KeyError):
                continue

            if peer_id != my_id and peer_id not in clients:
                clients[peer_id] = {"name": name, "ip": addr[0], "port": port}
                print("New client:", name, addr[0])
    finally:
        s.close()

async def discover(my_id, clients):
    os.system('clear')
    print("Searching for clients, press enter to stop.")

    print("Known clients:")
    for i in clients.values():
        print(i["name"], i["ip"])

    task = asyncio.create_task(find_clients(my_id, clients))
    await read_input()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
