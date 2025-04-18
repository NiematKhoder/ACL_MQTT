
## 1  What an ACL is and why we need it

In MQTT the broker first **authenticates** a client (username / password, TLS cert, JWT, …).  
An **Access‑Control List (ACL)** then tells the broker *what that client may do* on individual topics (`read`, `write`, `readwrite`, or `deny`). All enforcement happens inside the broker; nothing special is coded in the Python clients. 

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
├─ mosquitto/
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

### 4  Get the project

```powershell
git clone https://github.com/NiematKhoder/ACL_MQTT.git
cd ACL_MQTT
```
---

### 5  Start the broker

```powershell
docker compose up -d
```

This launches the Mosquitto container in the background.

--- 

##  6  Broker configuration files: Explanation

### 6.1  `broker/conf/mosquitto.conf`

```conf
# --- minimal secure config ---
listener 1884
allow_anonymous false

password_file /mosquitto/config/passwd   # created in 6.2
acl_file      /mosquitto/config/aclfile  # topic permissions
```

*`password_file`* and *`acl_file`* are the two key directives.

> [!IMPORTANT]
> **Why `allow_anonymous false`?**  
> Setting it to **false** forces every client to present valid credentials.  
> If you leave it **true**, Mosquitto lets anonymous clients connect, and those
> connections **skip both the password check *and* the ACL file**, so the
> authentication / authorisation rules we’re building in this tutorial would be ignored.
---

### 6.2  Generate the `passwd` file (hashed credentials)

Run once for each user; Docker keeps your host clean:

```powershell
# run from project root
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd pub  pub1
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub1 sub1
docker run --rm -it -v ${PWD}\broker\conf:/mosquitto/config eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub2 sub2
```

The tool appends lines in the format `username:hash`, where the hash is bcrypt‑like and **never reveals the plain password**. 

Here’s what each line does, step by step:

```powershell
# 1) Create or update the passwd file inside broker/conf, adding the “pub” user
docker run --rm -it \
  -v ${PWD}\broker\conf:/mosquitto/config \
  eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd pub pub1
```
- **`docker run`**  
  Launches a new container from the given image.
- **`--rm`**  
  Automatically removes the container when it exits (keeps your system clean).
- **`-it`**  
  Allocates an interactive pseudo‑TTY so you can see prompts (though `-b` “batch” mode suppresses them here).
- **`-v ${PWD}\broker\conf:/mosquitto/config`**  
  Mounts your local `broker\conf` folder into the container at `/mosquitto/config`.  
  - On Windows PowerShell `${PWD}` expands to your current directory path.
- **`eclipse-mosquitto:2.0`**  
  The official Mosquitto image (version 2.0) that includes the `mosquitto_passwd` tool.
- **`` ` mosquitto_passwd -b /mosquitto/config/passwd pub pub1``**  
  Runs the Mosquitto utility to add (or update) a line in the file `/mosquitto/config/passwd`:
  - `-b` = batch mode: takes the password from the command line instead of prompting.
  - `/mosquitto/config/passwd` = the target password file (inside the container, which is your mounted folder).
  - `pub` = the username to create/update.
  - `pub1` = the plaintext password; the tool writes a bcrypt‑style hash to the file.

---

```powershell
# 2) Add subscriber1’s credentials
docker run --rm -it \
  -v ${PWD}\broker\conf:/mosquitto/config \
  eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub1 sub1
```
Exactly the same as above, but now:
- **`sub1`** is the username.
- **`sub1`** (second argument) is its password.

This appends (or replaces) the `sub1:<hash>` line in your `broker/conf/passwd`.

---

```powershell
# 3) Add subscriber2’s credentials
docker run --rm -it \
  -v ${PWD}\broker\conf:/mosquitto/config \
  eclipse-mosquitto:2.0 `
  mosquitto_passwd -b /mosquitto/config/passwd sub2 sub2
```
Again identical, but for:
- **`sub2`** as the user,
- **`sub2`** as its password.

---

### What you end up with

After running these three commands, your `broker/conf/passwd` file will contain three lines, each in the form:

```
username:hashed-password
```

- **`pub:<hash>`**  
- **`sub1:<hash>`**  
- **`sub2:<hash>`**

Mosquitto uses this file at startup (via `password_file` in `mosquitto.conf`) to authenticate any connecting client. Any change you make here takes effect the next time you restart or reload the broker.

---

###  6.3  `broker/conf/aclfile`

```conf
# --- publisher may write both topics ---
user pub
topic readwrite topic1
topic readwrite topic2

# --- subscriber 1 : read-only topic1 ---
user sub1
topic read topic1

# --- subscriber 2 : read-only topic2 ---
user sub2
topic read topic2
```

> [!NOTE]
> **Note – roles reflected in credentials**  
> - The **`pub`** username/password acts as the *broker administrator* account: it has full **read + write** rights on all topics.  
> - Each topic also has its own dedicated consumer credential:  
>   - **`sub1`** ⇒ access **only** to `topic1`  
>   - **`sub2`** ⇒ access **only** to `topic2`  
>  
> You can think of it as **each topic having its own specific username/password**—clients holding a topic’s credentials can only access that topic—while the admin account (`pub`) retains full control for management or debugging across every topic.

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

