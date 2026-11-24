import asyncio
import os
import secrets
from discovery import beacon, discover
from connection import select_client, start_server, read_input, start_reader

async def main():
    clients = {}
    my_id = secrets.token_hex(8)
    os.system('clear')
    print("Hello and welcome to my p2p chat app, please enter you nickname below:\n")
    nickname = input().strip()
    while not nickname:
        nickname = input("Nickname can't be empty, try again:\n").strip()
    start_reader()
    server, port = await start_server(nickname)
    beacon_task = asyncio.create_task(beacon(nickname, my_id, port))

    while True:
        os.system('clear')
        choice = await read_input("1 - Start chatting\n2 - Discover hosts\n3 - Exit\n")
        match choice.strip():
            case "1":
                if not clients:
                    print("No clients available, find some by using the 'Discover hosts' option")
                    await asyncio.sleep(2)
                else:
                    os.system('clear')
                    await select_client(clients, nickname)
            case "2":
                await discover(my_id, clients)
            case "3":
                print("Exiting")
                beacon_task.cancel()
                server.close()
                break
            case _:
                print("Invalid input. Please select either 1, 2 or 3.")
                await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting")
        os._exit(0)
