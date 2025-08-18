import stomp
import zlib
import io
import time
import socket
import logging
import boto3
import json
import os
import socket
#from dotenv import load_dotenv
#load_dotenv() 
try:
    import PPv16
except ModuleNotFoundError:
    raise ImportError("Class files not found - please configure the client following steps in README.md!")


# 🛠 CONFIGURATION (fetched from environment variables)
# 🔐 Secure Configuration via Environment Variables
USERNAME = 'Darwin Username'
PASSWORD = 'Darwin Password'
HOSTNAME = 'darwin-dist-44ae45.nationalrail.co.uk'
HOSTPORT = 61613
TOPIC = '/topic/darwin.pushport-v16'
CLIENT_ID = socket.getfqdn()  # Generates a unique client ID from machine hostname
HEARTBEAT_INTERVAL_MS = 15000
RECONNECT_DELAY_SECS = 15
KINESIS_STREAM_NAME ='kinesis-datanationalrail-events'



# 🔌 Kinesis Client
kinesis_client = boto3.client('kinesis')

# 🧠 Logging
logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO)


# 🔄 Connect and Subscribe to STOMP
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
        logging.info('Received a heartbeat')

    def on_heartbeat_timeout(self):
        logging.error('Heartbeat timeout')

    def on_error(self, message):
        logging.error('STOMP error: %s', message)

    def on_disconnected(self):
        logging.warning(f'Disconnected - waiting {RECONNECT_DELAY_SECS}s before exiting')
        time.sleep(RECONNECT_DELAY_SECS)
        exit(-1)

    def on_connecting(self, host_and_port):
        logging.info(f'Connecting to {host_and_port[0]}')

    def on_message(self, frame):
        try:
            logging.info('Message seq=%s, type=%s received', frame.headers.get('SequenceNumber'), frame.headers.get('MessageType'))
            msg = zlib.decompress(frame.body, zlib.MAX_WBITS | 32)
            obj = PPv16.CreateFromDocument(msg)

            payload = {
                'ts': str(obj.ts),
                'msg_type': frame.headers.get('MessageType'),
                'raw_xml': msg.decode("utf-8", errors="ignore")
            }

            # Send to Kinesis
            kinesis_client.put_record(
                StreamName=KINESIS_STREAM_NAME,
                Data=json.dumps(payload),
                PartitionKey=str(obj.ts)
            )
            logging.info("✅ Sent record to Kinesis for ts %s", obj.ts)

        except Exception as e:
            logging.error("❌ Error handling message: %s", str(e))


# 🚀 Start the Stream Listener
def start_darwin_stream():
    conn = stomp.Connection12([(HOSTNAME, HOSTPORT)],
                              auto_decode=False,
                              heartbeats=(HEARTBEAT_INTERVAL_MS, HEARTBEAT_INTERVAL_MS))

    conn.set_listener('', DarwinKinesisListener())
    connect_and_subscribe(conn)

    logging.info("📡 Subscribed to Darwin Push Port... streaming to Kinesis")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        conn.disconnect()
        logging.info("🛑 Gracefully disconnected")


if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        logging.error("⚠️ Username or password not set. Please configure before running.")
    else:
        start_darwin_stream()
