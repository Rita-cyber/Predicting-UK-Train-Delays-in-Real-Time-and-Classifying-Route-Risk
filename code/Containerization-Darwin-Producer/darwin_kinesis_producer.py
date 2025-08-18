import stomp
import zlib
import time
import socket
import logging
import boto3
import json
import os
import signal
import sys
import uuid

try:
    import PPv16
except ModuleNotFoundError:
    raise ImportError("Class files not found - please configure the client following steps in README.md!")

# 🛠 CONFIGURATION
USERNAME = os.getenv('DARWIN_USERNAME')
PASSWORD = os.getenv('DARWIN_PASSWORD')
HOSTNAME = 'darwin-dist-44ae45.nationalrail.co.uk'
HOSTPORT = 61613
TOPIC = '/topic/darwin.pushport-v16'
CLIENT_ID = CLIENT_ID = f"{socket.getfqdn()}-{uuid.uuid4().hex[:8]}"
HEARTBEAT_INTERVAL_MS = 15000
RECONNECT_DELAY_SECS = 15
KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME')

if not USERNAME or not PASSWORD or not KINESIS_STREAM_NAME:
    raise EnvironmentError("❌ Missing required env vars: DARWIN_USERNAME, DARWIN_PASSWORD, KINESIS_STREAM_NAME")

# 🔌 Kinesis Client
kinesis_client = kinesis_client = boto3.client(
    'kinesis',
    region_name=os.getenv('AWS_REGION', 'eu-north-1')
)

# 🧠 Logging
logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO)

# Handle shutdown cleanly
running = True
def handle_sigterm(signum, frame):
    global running
    logging.info("🛑 Received SIGTERM, shutting down gracefully...")
    running = False
signal.signal(signal.SIGTERM, handle_sigterm)

# 🔄 Connect and Subscribe
def connect_and_subscribe(connection):
    if stomp.__version__[0] < '5':
        connection.start()

    connect_header = {'client-id': USERNAME + '-' + CLIENT_ID}
    subscribe_header = {'activemq.subscriptionName': CLIENT_ID}

    connection.connect(username=USERNAME,
                       passcode=PASSWORD,
                       wait=True,
                       headers=connect_header)

    connection.subscribe(destination=TOPIC,
                         id='1',
                         ack='auto',
                         headers=subscribe_header)

# 📡 STOMP Listener
class DarwinKinesisListener(stomp.ConnectionListener):

    def on_heartbeat(self):
        logging.debug('Received heartbeat')

    def on_heartbeat_timeout(self):
        logging.error('⚠️ Heartbeat timeout')

    def on_error(self, message):
        logging.error('❌ STOMP error: %s', message)

    def on_disconnected(self):
        logging.warning(f'⚠️ Disconnected - will retry in {RECONNECT_DELAY_SECS}s')
        time.sleep(RECONNECT_DELAY_SECS)

    def on_connecting(self, host_and_port):
        logging.info(f'🔌 Connecting to {host_and_port[0]}')

    def on_message(self, frame):
        try:
            logging.info('📩 Message seq=%s, type=%s',
                         frame.headers.get('SequenceNumber'),
                         frame.headers.get('MessageType'))

            msg = zlib.decompress(frame.body, zlib.MAX_WBITS | 32)
            obj = PPv16.CreateFromDocument(msg)

            payload = {
                'ts': str(obj.ts),
                'msg_type': frame.headers.get('MessageType'),
                'raw_xml': msg.decode("utf-8", errors="ignore")
            }

            kinesis_client.put_record(
                StreamName=KINESIS_STREAM_NAME,
                Data=json.dumps(payload),
                PartitionKey=str(obj.ts)
            )
            logging.info("✅ Sent record to Kinesis for ts %s", obj.ts)

        except Exception as e:
            logging.exception("❌ Error handling message")

# 🚀 Start the Stream Listener
def start_darwin_stream():
    global running
    while running:
        try:
            conn = stomp.Connection12(
                [(HOSTNAME, HOSTPORT)],
                auto_decode=False,
                heartbeats=(HEARTBEAT_INTERVAL_MS, HEARTBEAT_INTERVAL_MS)
            )
            conn.set_listener('', DarwinKinesisListener())
            connect_and_subscribe(conn)
            logging.info("📡 Subscribed to Darwin Push Port... streaming to Kinesis")

            while running and conn.is_connected():
                time.sleep(1)

            conn.disconnect()
        except Exception as e:
            logging.exception("❌ Stream loop crashed, retrying...")
            time.sleep(RECONNECT_DELAY_SECS)

    logging.info("👋 Producer stopped")

if __name__ == "__main__":
    start_darwin_stream()
