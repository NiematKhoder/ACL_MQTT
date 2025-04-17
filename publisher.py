
import time
import paho.mqtt.client as mqtt

def connect_mqtt(client_id, username, password, on_message=None):
    client = mqtt.Client(client_id=client_id)
    client.username_pw_set(username, password)
    if on_message:
        client.on_message = on_message
    client.connect("localhost", 1883, keepalive=60)
    return client

client = connect_mqtt("pub-client", "pub", "pub1")

while True:
    client.publish("topic1", "hello topic1")
    client.publish("topic2", "hello topic2")
    print("Sent one message to each topic")
    time.sleep(3)
