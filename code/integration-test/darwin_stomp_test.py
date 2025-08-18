import stomp
import socket
import logging
import os
import time
import uuid, socket

# ---------- CONFIG ----------
USERNAME = 'DARWIN76ee3c8b-16bb-44c3-be6b-8b09b073f0bd'
PASSWORD = 'c9c047f6-b26f-4149-bde6-8daa0793e437'
HOSTNAME = 'darwin-dist-44ae45.nationalrail.co.uk'
HOSTPORT = 61613
TOPIC = '/topic/darwin.pushport-v16'
CLIENT_ID = f"{socket.getfqdn()}-{uuid.uuid4().hex[:8]}"


HEARTBEAT_INTERVAL_MS = 15000
RECONNECT_DELAY_SECS = 15

# ---------- LOGGING ----------
logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO)

# ---------- STOMP Listener ----------
class TestListener(stomp.ConnectionListener):
    def on_error(self, message):
        logging.error("STOMP error: %s", message)

    def on_heartbeat(self):
        logging.info("Heartbeat received")

    def on_heartbeat_timeout(self):
        logging.warning("Heartbeat timeout")

    def on_disconnected(self):
        logging.warning(f"Disconnected - retrying in {RECONNECT_DELAY_SECS}s")
        time.sleep(RECONNECT_DELAY_SECS)

    def on_connecting(self, host_and_port):
        logging.info(f"Connecting to {host_and_port[0]}:{host_and_port[1]}")

    def on_message(self, frame):
        logging.info(f"Message received: seq={frame.headers.get('SequenceNumber')} type={frame.headers.get('MessageType')}")

# ---------- CONNECT ----------
def start_test_connection():
    conn = stomp.Connection12([(HOSTNAME, HOSTPORT)],
                              auto_decode=False,
                              heartbeats=(HEARTBEAT_INTERVAL_MS, HEARTBEAT_INTERVAL_MS))

    listener = TestListener()
    conn.set_listener('', listener)

    try:
        connect_header = {'client-id': USERNAME + '-' + CLIENT_ID}
        subscribe_header = {'activemq.subscriptionName': CLIENT_ID}

        conn.connect(username=USERNAME, passcode=PASSWORD, wait=True, headers=connect_header)
        conn.subscribe(destination=TOPIC, id='1', ack='auto', headers=subscribe_header)

        logging.info("Subscribed to Darwin topic. Listening for messages...")

        while True:
            time.sleep(1)

    except Exception as e:
        logging.error(f"Exception during connection: {e}")
    finally:
        conn.disconnect()
        logging.info("Disconnected")

# ---------- MAIN ----------
if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        logging.error("Username or password not set.")
    else:
        start_test_connection()
