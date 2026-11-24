import asyncio
import json
import os
import sys
import threading
import time
import ssl

state = "not_chatting"
redirect = None
last_request = -5
last_prompt = ""
lines = asyncio.Queue()

def route(line):
    if redirect is not None:
        redirect.put_nowait(line)
    else:
        lines.put_nowait(line)

def start_reader():
    loop = asyncio.get_running_loop()

    def run():
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            loop.call_soon_threadsafe(route, line)

    threading.Thread(target=run, daemon=True).start()

async def read_input(prompt=""):
    global last_prompt
    last_prompt = prompt
    print(prompt, end="", flush=True)
    return await lines.get()

async def send(writer, **msg):
    writer.write((json.dumps(msg) + "\n").encode())
    await writer.drain()

async def start_server(nickname):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    server = await asyncio.start_server(
        lambda r, w: handle_incoming(r, w, nickname), "0.0.0.0", 0, ssl=ctx)
    return server, server.sockets[0].getsockname()[1]

async def listen(reader, peer):
    while True:
        try:
            line = await reader.readline()
        except OSError:
            break
        if not line:
            break
        try:
            msg = json.loads(line)
            if msg["type"] == "leave":
                break
            if msg["type"] == "msg":
                print(f"{peer}: {msg['text']}")
        except (ValueError, KeyError, TypeError):
            continue
    print(f"\n{peer} left the chat")
    redirect.put_nowait(None)

async def chat(reader, writer, me, peer):
    global redirect
    redirect = asyncio.Queue()
    os.system('clear')
    print(f"Chatting with {peer}, type /quit to leave\n")
    listener = asyncio.create_task(listen(reader, peer))

    while True:
        text = await redirect.get()
        if text is None:
            break
        text = text.strip()
        if text == "/quit":
            try:
                await send(writer, type="leave")
            except OSError:
                pass
            print("You left the chat")
            break
        if not text:
            continue
        print(f"\033[F\033[K{me}: {text}")
        try:
            await send(writer, type="msg", text=text)
        except OSError:
            print(f"\n{peer} left the chat")
            break

    listener.cancel()
    redirect = None
    while not lines.empty():
        lines.get_nowait()

async def handle_incoming(reader, writer, nickname):
    global state, redirect
    if state == "chatting":
        writer.close()
        return

    state = "chatting"
    name = "Someone"
    try:
        msg = json.loads(await asyncio.wait_for(reader.readline(), 5))
        if msg["type"] != "request":
            return
        name = msg["name"]

        redirect = asyncio.Queue()
        while True:
            print(f"\n{name} wants to chat.  1 - Accept   2 - Decline")
            answer = (await asyncio.wait_for(redirect.get(), 25)).strip()
            if answer in ("1", "2"):
                break
            print("Please press 1 or 2.")

        if answer == "1":
            await send(writer, type="accept")
            await chat(reader, writer, nickname, name)
            await asyncio.sleep(2)
            os.system('clear')
            print(last_prompt, end="", flush=True)
        else:
            await send(writer, type="decline")
            print(f"You declined {name}.")
    except TimeoutError:
        print(f"The request from {name} timed out.")
    except (OSError, ValueError, KeyError, TypeError):
        pass
    finally:
        redirect = None
        state = "not_chatting"
        writer.close()

async def select_client(clients, nickname):
    for i, j in enumerate(clients.values(), start = 1):
        print(f"{i} - {j['name']} {j['ip']}")
    print("\nSelect from the above clients")
    choice = await read_input("> ")
    try:
        number = int(choice)
        if number < 1:
            raise IndexError
        peer = list(clients.values())[number - 1]
    except (ValueError, IndexError):
        print("Invalid selection.")
        await asyncio.sleep(2)
        return
    await connect(peer, nickname)

async def connect(peer, nickname):
    global state, last_request
    if state == "chatting":
        print("You're busy right now.")
        await asyncio.sleep(2)
        return
    wait = 5 - (time.monotonic() - last_request)
    if wait > 0:
        print(f"Wait {wait:.0f} more seconds before sending another request.")
        await asyncio.sleep(2)
        return

    last_request = time.monotonic()
    state = "chatting"
    writer = None
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        reader, writer = await asyncio.open_connection(peer["ip"], peer["port"], ssl=ctx)
        await send(writer, type="request", name=nickname)
        print(f"Request sent to {peer['name']}, waiting for a reply...")

        line = await asyncio.wait_for(reader.readline(), 30)
        if not line:
            print(f"{peer['name']} is busy or unavailable.")
            return
        reply = json.loads(line)

        if reply["type"] == "accept":
            await chat(reader, writer, nickname, peer["name"])
        elif reply["type"] == "decline":
            print(f"{peer['name']} declined your request.")
    except TimeoutError:
        print(f"No response from {peer['name']}.")
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"Something went wrong {e}")
    finally:
        state = "not_chatting"
        if writer:
            writer.close()
        await asyncio.sleep(2)
