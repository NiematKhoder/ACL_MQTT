
## 1  What an ACL is and why we need it

In MQTT the broker first **authenticates** a client (username / password, TLS cert, JWT, …).  
An **Access‑Control List (ACL)** then tells the broker *what that client may do* on individual topics (`read`, `write`, `readwrite`, or `deny`). All enforcement happens inside the broker; nothing special is coded in the Python clients.  citeturn6search5

---

##  2  Prerequisites

| Tool | Why | Quick check |
|------|-----|-------------|
| **Docker Desktop** (Windows) | Run the Mosquitto container | `docker version` |
| **Docker Compose** | One‑file stack definition | `docker compose version` |
| **Python ≥ 3.9** | Run publisher/subscriber scripts | `python --version` |
| **(Optional) VS Code** | Editing & terminals | – |

---

##  3  Project structure

```text
mqtt-acl-demo/
├─ docker-compose.yml
├─ broker/
│  └─ conf/
│     ├─ mosquitto.conf
│     ├─ aclfile
│     └─ passwd          ← generated in step 6.2
└─ app/
   ├─ publisher.py
   ├─ subscriber1.py
   └─ subscriber2.py
```

---

##  4  Create the folders (PowerShell)

```powershell
# anywhere you like
mkdir mqtt-acl-demo, mqtt-acl-demo\broker\conf, mqtt-acl-demo\app
cd mqtt-acl-demo
```

---

##  5  `docker-compose.yml`

```yaml
version: "3.9"

services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"           # MQTT TCP
    volumes:
      - ./broker/conf/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - ./broker/conf/aclfile:/mosquitto/config/aclfile:ro
      - ./broker/conf/passwd:/mosquitto/config/passwd:ro
      - mosquitto_data:/mosquitto/data
    command: [ "mosquitto", "-c", "/mosquitto/config/mosquitto.conf" ]

volumes:
  mosquitto_data:
```

---

##  6  Broker configuration files

### 6.1  `broker/conf/mosquitto.conf`

```conf
# --- minimal secure config ---
listener 1883
allow_anonymous false

password_file /mosquitto/config/passwd   # created in 6.2
acl_file      /mosquitto/config/aclfile  # topic permissions
```

*`password_file`* and *`acl_file`* are the two key directives. citeturn6search3

---

### 6.2  Generate the `passwd` file (hashed credentials)

Run once for each user; Docker keeps your host clean:

```powershell
# run from project root
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd pub  pubpass
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub1 sub1pass
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub2 sub2pass
```

The tool appends lines in the format `username:hash`, where the hash is bcrypt‑like and **never reveals the plain password**.  citeturn7search0

---

###  6.3  `broker/conf/aclfile`

```conf
# --- publisher may write both topics ---
user pub
topic write topic1
topic write topic2

# --- subscriber 1 : read-only topic1 ---
user sub1
topic read topic1

# --- subscriber 2 : read-only topic2 ---
user sub2
topic read topic2
```

Lines are evaluated top‑down; anything not explicitly allowed is denied. citeturn6search3

---


## 7  `app/publisher.py`

```python
import time, paho.mqtt.client as mqtt

BROKER, PORT   = "localhost", 1883
TOPICS         = ("topic1", "topic2")   # publish to both
USERNAME, PASS = "pub", "pubpass"

client = mqtt.Client(client_id="publisher")
client.username_pw_set(USERNAME, PASS)
client.connect(BROKER, PORT, keepalive=60)

counter = 0
while True:
    for t in TOPICS:
        payload = f"msg {counter} on {t}"
        client.publish(t, payload, qos=1)
        print(f"→ {payload}")
        time.sleep(0.5)
    counter += 1
```

The code is pure Paho‑MQTT; nothing special for ACLs. citeturn0search0

---

## 8  Subscribers

Both scripts are identical except for `USERNAME/PASS` and the topic variable that we’ll toggle in phase 2.

```python
# app/subscriber1.py  (change to subscriber2.py and edit creds/topic)

import paho.mqtt.client as mqtt, os

BROKER, PORT = "localhost", 1883
USERNAME, PASS = "sub1", "sub1pass"
TOPIC     = "topic1"   # line 8 – switch to "topic2" in phase 2

def on_connect(client, userdata, flags, rc, properties=None):
    print("✔ connected, subscribing to", TOPIC)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    print(f"← {msg.topic}: {msg.payload.decode()}")

client = mqtt.Client(client_id="sub1")
client.username_pw_set(USERNAME, PASS)
client.on_connect  = on_connect
client.on_message  = on_message
client.connect(BROKER, PORT, keepalive=60)
client.loop_forever()
```

---

## 9  Running and testing

### Phase 1 — normal operation

```powershell
# 1. start broker
docker compose up -d        # from project root

# 2. start the subscribers in two terminals
python app\subscriber1.py
python app\subscriber2.py

# 3. start the publisher
python app\publisher.py
```

Expected console output:

* **subscriber1** shows only `topic1` messages  
* **subscriber2** shows only `topic2` messages  
* publisher shows every message it sends.

### Phase 2 — unauthorised subscribe

1. Stop **subscriber1** (`Ctrl+C`)  
2. Edit *line 8* in `subscriber1.py`:

```python
TOPIC = "topic2"   # now trying to spy on topic2
```

 3. Run it again:  

```powershell
python app\subscriber1.py
```

4. Start (or keep running) `publisher.py`.

**Result:** subscriber1 connects successfully but receives **nothing**, proving the ACL denies its subscription to `topic2`.

---

