# P2P LAN Chat

A peer-to-peer chat app that runs in the terminal and works over your local network. No central server, no accounts, no port forwarding. Start it on two machines on the same network, find each other, and talk.

Built with Python and `asyncio`.

## How it works

1. **Discovery (UDP).** Every instance broadcasts a small JSON beacon to UDP port `9999` every 3 seconds, containing a random ID, a nickname and the TCP port it is listening on. Every instance also listens for other people's beacons and keeps a list of the peers it has seen.
2. **Request (TCP + TLS).** When you pick a peer, your app connects to that peer's TCP port and sends a chat request. The other person sees a prompt and presses `1` to accept or `2` to decline.
3. **Chat.** On accept, both terminals clear and you can type back and forth. Type `/quit` to leave.

```
mare: hello
djole: hi
mare: how are you doing
djole: good and you?
```

### Rules

- If you are already in a chat or answering a request, incoming connections are dropped and the sender is told you are busy.
- A declined request shows the sender "X declined your request".
- There is a 5 second cooldown between sending requests.
- An unanswered request times out (25 seconds on the receiving side, 30 on the sending side).

## Project layout

| File | What it does |
|---|---|
| `main.py` | Asks for a nickname, starts the TCP server and the beacon, runs the menu |
| `discovery.py` | UDP beacon and listener, and the "Discover hosts" screen |
| `connection.py` | TLS server, request/accept/decline flow, chat loop, keyboard input routing |

## Requirements

- Python 3.11 or newer (uses `loop.sock_recvfrom` and `match`)
- Linux or macOS (uses `clear` and reads stdin in a background thread)
- OpenSSL, to generate a certificate
- No third-party packages

## Setup

Generate a certificate and key and put them in the folder you run the app from:

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 -subj "/CN=p2pchat"
```

Then run:

```bash
python main.py
```

Do this on each machine (or in two terminals on one machine, see below).

## Usage

1. Enter a nickname.
2. Choose **2 - Discover hosts** and wait for other people to show up. Press Enter to stop searching.
3. Choose **1 - Start chatting**, pick a number from the list and wait for a reply.
4. The other person presses `1` to accept or `2` to decline.
5. Chat. Type `/quit` to leave.

### Testing on one machine

Open two terminals, run `python main.py` in each, and use different nicknames. Discovery uses `SO_REUSEADDR` and the TCP port is picked by the OS, so two instances can run side by side.

## Security

The chat connection (TCP) is encrypted with TLS. A few honest limitations:

- **Encryption, not identity.** The client does not verify the server's certificate, so this protects against someone sniffing the Wi-Fi but not against someone impersonating a peer.
- **Beacons are plaintext.** Nicknames, IDs and ports sent over UDP are visible to everyone on the network and can be spoofed.

## Troubleshooting

- **Peers don't show up.** Check that both machines are on the same network and that your firewall allows UDP `9999`. Guest networks and some public Wi-Fi block device-to-device traffic (AP isolation).
- **Connection fails right after sending a request.** Check that both sides have `cert.pem` and `key.pem`, and that your firewall isn't blocking the TCP port (it is random each run).
- **`FileNotFoundError` for `cert.pem`.** The path is relative to where you run the command. Run `python main.py` from the folder that contains the certificate.

### Looking at the traffic with Wireshark

- Beacons: filter `udp.port == 9999`. You will see the JSON payload.
- Chat: filter `tcp.port == <port>`, where the port is in the beacon payload. You should see TLS `Application Data` packets with unreadable contents.
- Two instances on the same machine talk over the loopback interface, so capture on `lo` or `any`, not your Wi-Fi interface.

## Known limitations

- Peers are never removed from the list once seen, so people who left stay listed.
- The peer list only updates while the Discover screen is open.
- Messages that arrive while you are mid-sentence print over your input.
- No message history, no group chats, no file transfer.

## Ideas for later

- Expire peers that stop beaconing
- Keep discovery running in the background
- Per-instance certificates with fingerprint checking
- A nicer terminal UI (for example with `prompt_toolkit`)
- Anonymization: a global relay server with all traffic routed over Tor, so peers can chat across networks without exposing their IP addresses
