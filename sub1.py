# sub1_debug.py  (same for sub2, just change user/topic)

import paho.mqtt.client as mqtt
import logging

logging.basicConfig(level=logging.DEBUG)      # full wire‑level log
USER, PW  = "sub1", "sub1"
TOPIC     = "topic1"
# TOPIC     = "topic2"
def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNECT rc =", rc)                  # 0 = success
    if rc == 0:
        client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

cli = mqtt.Client(client_id="sub1-client")
cli.enable_logger()                           # paho helper :contentReference[oaicite:0]{index=0}
cli.username_pw_set(USER, PW)
cli.on_connect, cli.on_message = on_connect, on_message
cli.connect("localhost", 1883, 60)
cli.loop_forever()
