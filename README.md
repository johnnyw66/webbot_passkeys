## Webbot – Amazon AtoZ Opportunity Monitor

This project demonstrates how to build a Python-based automation system that reviews and reports job opportunities available to Amazon associates working at logistics centres.

Because Amazon’s authentication flow and page structure change frequently, parts of this project may eventually stop working. However, the codebase is intended primarily as a practical example of writing resilient Playwright automation scripts and adapting to evolving web platforms.

Over the years, these scripts have evolved alongside changes made by the Amazon AtoZ platform:

Initially: simple polling of a REST API

Later: GraphQL polling every 5 minutes

Authentication: username/password every 15 minutes

Currently: passkey-based authentication approximately every 30 days

The system runs fully automatically. If two independent instances are deployed, the monitoring and opportunity capture process remains resilient and fault-tolerant.

Last known successful use: January 2026

Authentication History

Previously, Amazon’s AtoZ system used a layered authentication approach:

+ Username + password

+ SMS-based Two-Factor Authentication (2FA)

+ CAPTCHA challenges

While secure, this approach was complex and depended on external services, increasing friction and potential failure points.

The current system is transitioning to passkeys, which use cryptographic credentials stored directly on a device (a “digital key”). Examples include:

+ Fingerprint readers (phone or PC)

+ YubiKeys

+ WebAuth/FIDO hardware tokens (e.g., **Pico FIDO**)

During login, the browser interacts with the passkey device to confirm identity without requiring passwords or SMS codes.

The **Pico FIDO** device is particularly useful for automation because it can be configured to authenticate without physical interaction. A PIN is still required, but once registered with AtoZ by hand, this can be automated via Python.


https://www.picokeys.com/pico-fido/


## Setup

1. Create configuration file

Copy the example configuration:

example_configure.py → configure.py


Edit:

ATOZ_USERNAME
ATOZ_EMPLOYEE_ID

MQTT_USERNAME
MQTT_SECRET
MQTT_BROKER


If not using passkeys, also set:

ATOZ_PASSWORD
TWO_CAPTCHA_API_KEY


(You can obtain a key at 2captcha.com)

You will also need an MQTT SMS gateway:

https://github.com/johnnyw66/MQTT-SMS-Gateway

2. Install requirements
python3 -m pip install -r requirements.txt

Running
Simple run
python3 webbot.py

Recommended (resilient) run

Use Docker and the watchdog script.

Build the container (one time only)
./docker_build.sh


(Rebuild only if credentials or configuration change)

Start
./webbot_watchdog.sh

Building the Pico FIDO Device

To flash firmware onto a Raspberry Pi Pico:

Unplug the device

Hold BOOTSEL

Plug into USB

A drive appears (RPI-RP2 or RP2350)

Copy the .uf2 file to the drive

Device reboots and appears as Pico Key

LED will blink periodically when ready.

Documentation:

https://www.picokeys.com/getting-started/

https://www.picokeys.com/picokeyapp/


**Amazon A-to-Z Automation WebBot**

A high-performance Python-based automation suite designed to monitor, notify, and "grab" work opportunities (VTO/VET) from the Amazon A-to-Z platform. The system utilises Playwright for browser automation, GraphQL for efficient data fetching, and MQTT for real-time remote control and health monitoring.

## **🚀 Key Features**

* **Automated Opportunity Grabbing:** Monitors and claims Voluntary Time Off (VTO) and Voluntary Extra Time (VET) using direct GraphQL mutations.  
* **Intelligent Requirements Engine:** Uses a **Decorator Pattern** to chain complex logic (e.g., "Only grab VET if it's on a Tuesday, longer than 5 hours, and starts after 08:00").  
* **Anti-Bot & Stealth:** Integrates Playwright stealth scripts, custom User-Agents, and human-like delay logic to minimize detection.  
* **Captcha Solving:** Automated AWS WAF Captcha handling via the **2Captcha** API.  
* **Multi-Channel Notifications:** Supports Email alerts (with IMAP peeking), MQTT status updates, and Voice Monkey (Alexa) announcements.  
* **Containerized Watchdog:** Includes a Bash-based watchdog script that monitors a Docker container via MQTT heartbeats and auto-restarts on failure.  
* **Remote Management:** Dynamically update requirements or trigger "claims" via MQTT topics while the bot is running.

## ---

**🛠️ Tech Stack**

* **Language:** Python 3.10+  
* **Automation:** Playwright (Chromium/Firefox)  
* **Networking:** HTTPX (Async), MQTT (aiomqtt), IMAP  
* **Infrastructure:** Docker, VirtualHere (USB/Hardware Auth Passthrough)  
* **Logic:** Decorator Pattern for requirement matching

## ---

**📋 Prerequisites**

1. **Docker:** For running the containerized environment.  
2. **MQTT Broker:** (e.g., Mosquitto) for status and remote control.  
3. **2Captcha API Key:** Required if your login flow triggers AWS Captchas.  
4. **Python 3.10+:** (If running locally without Docker).

# ---


## ---

**⚙️ Configuration**

1. **Bot Settings:** Copy example\_configure.py to configure.py and update your ATOZ\_USERNAME, ATOZ\_PASSWORD, and MQTT\_SECRET.  
2. **Infrastructure Settings:** Copy example\_watchdog\_configure.sh to watchdog\_configure.sh to set up your Docker environment and MQTT broker addresses.

## ---

**🏃 Installation & Usage**

### **1\. Build and Run via Docker (Recommended)**

The project includes a webbot\_watchdog.sh script to ensure 24/7 uptime.

Bash

\# Give execution permissions  
chmod \+x webbot\_watchdog.sh webbot.sh

\# Start the bot with the watchdog  
./webbot\_watchdog.sh \--join

### **2\. Manual Local Setup**

Bash

pip install \-r requirements.txt  
playwright install chromium  
python webbot.py

## ---

**🧩 Requirement Logic (The Decorator Pattern)**

The system uses decorrequirements.py to filter opportunities. You can chain requirements like this:

Python

\# Example: Grab VET only on weekends if it's at least 5 hours long  
requirement \= DayRequirement('saturday, sunday',   
                TypeRequirement('EXTRA\_TIME',   
                    MinTimeRequirement(300)  
                )  
             )

**Available Requirements:**

* WithinRequirement(mins): Start time is within X minutes.  
* NoticeRequirement(mins): Must have at least X minutes of lead time.  
* DayRequirement(mask): Match specific days of the week.  
* StartTimeRequirement(pattern): Matches HH:MM using regex/wildcards.  
* Min/MaxTimeRequirement: Filters by shift duration.

## ---

**📡 MQTT API**

The bot listens and publishes to several topics for remote orchestration:

| Topic | Purpose |
| :---- | :---- |
| webbot/status/{hostname} | Publishes heartbeat and current bot state. |
| opportunities/{ID}/claim | Send an Opportunity ID to this topic to force-grab it. |
| opportunities/{ID}/stealthdelay | Update the grab delay (seconds) in real-time. |
| setclaimschedule/vetrequirements | Send a JSON payload to update complex VET filters. |

## ---

**⚠️ Disclaimer**

This tool is for educational and personal productivity purposes. Use responsibly and ensure compliance with all applicable Terms of Service.

**Below is a breakdown of the JSON payloads and their corresponding topics:**

### **📥 Inbound Payloads (Control & Configuration)**

**The bot subscribes to these topics to receive external commands.**

#### **1\. Set VET Requirements**

* **Topic: setclaimschedule/vetrequirements**  
* **Purpose: Configures the complex "Decorator" logic for grabbing Extra Time shifts.**  
* **Payload Structure:**  
* **JSON**

**{**

  **"opportunity\_type": "EXTRA\_TIME",**

  **"days": \["Monday", "Tuesday"\],**

  **"min\_duration": 300,**

  **"max\_duration": 360,**

  **"notice": 48.0,**

  **"start\_date": "2025-12-25",**

  **"end\_date": "2025-12-31",**

  **"start\_time\_pattern": "0\[5-6\]:\*\*"**

**}**

*   
  * **Note: notice is expected in hours (converted to minutes by the bot), and start\_time\_pattern supports wildcards (e.g., \*\*:\*\* for any time).**

#### **2\. SMS & Verification Code**

* **Topic: mqttsmsgw/\#**  
* **Purpose: Receives SMS-based One-Time Passwords (OTP) to bypass two-factor authentication.**  
* **Payload Structure:**  
* **JSON**

**{**

  **"text": "Your Amazon verification code is 123456",**

  **"msisdn": "1234567890",**

  **"to": "0987654321"**

**}**

*   
  * **The bot uses regex to extract the digits after "verification code is".**

#### **3\. Claim Specific Opportunity**

* **Topic: opportunities/{ATOZ\_EMPLOYEE\_ID}/claim**  
* **Purpose: Forces the bot to grab a specific shift by its ID.**  
* **Payload: A raw string containing the opportunity\_id.**

---

### **📤 Outbound Payloads (Status & Reporting)**

**The bot publishes these payloads to report its health and found opportunities.**

#### **1\. Bot Health/Ping**

* **Topic: webbot/status/{hostname}**  
* **Purpose: Sent every 5 minutes (or on state change) to indicate the bot is alive.**  
* **Payload Structure:**  
* **JSON**

**{**

  **"version": "1.0",**

  **"utc\_time": 1734840000,**

  **"time\_passed": 3600,**

  **"timestamp": 1734843600,**

  **"hostname": "bot-server-01",**

  **"referrer": "manual-start",**

  **"status": "ok",**

  **"ping\_event": "1734843600.0"**

**}**

*   
* 

#### **2\. Opportunity Updates**

* **Topic: opportunities/api/vto or opportunities/api/vet**  
* **Purpose: Publishes a full list of available shifts found during the last scan.**  
* **Payload Structure: A JSON list containing opportunity objects:**  
* **JSON**

**\[**

  **{**

    **"opportunity\_id": "VTO12345",**

    **"opportunity\_type": "VTO",**

    **"start\_time": "2025-12-23T08:00:00.000Z",**

    **"minutes\_to\_cover\_opportunity": 600,**

    **"active": true,**

    **"inactive\_reason": "None"**

  **}**

**\]**

*   
* 

### **🛠️ Interactive Tooling**

### **1\. Interactive Scheduling (requirements.htm)**

This file serves as a dedicated configuration portal for **VET (Extra Time)** requirements.

* **Day Selection:** It allows you to select specific days of the week (e.g., Monday, Tuesday) via checkboxes to build your "wanted" work week.  
* **Time Patterns:** It provides an input field for start-time-pattern, allowing you to use wildcards like 0\[5-7\]:00 to target specific shift start times.  
* **Persistence:** When you click "Submit," it publishes a **retained MQTT message** to setclaimschedule/vetrequirements, ensuring the Python bot adopts these rules immediately and remembers them even after a reboot.

### **2\. Live Dashboard Monitoring (schedule.htm)**

This file provides a real-time view of the bot's status and **VTO (Time Off)** scheduling.

* **VTO Bitmask Setup:** It includes a fieldset with checkboxes for every day of the week. When changed, it calculates an integer "mask" (e.g., Sunday \= 1, Monday \= 2\) and publishes it to the bot to automate VTO claims.  
* **Stealth Controls:** It allows you to toggle "Stealth Masks" and adjust "Stealth Delay" (0 to 120 seconds) via radio buttons to control how aggressively the bot grabs shifts.  
* **Visual Tables:** It dynamically builds tables to show "Active VTOs," "Accepted VETs," and even the health status of various "Webbots" and "Agents" currently running.

### **3\. Integrated Logic Flow**

The relationship between the files works as follows:

* **Configuration:** You use requirements.htm or the checkboxes in schedule.htm to define your ideal schedule.  
* **Communication:** The JavaScript in these files translates your clicks into MQTT payloads.  
* **Execution:** The Python code (webbot.py) listens for these payloads, updates its RequirementsManager, and uses those new rules to decide which shifts to "grab" during the next scan.

Based on the source code provided, specifically the imports in webbot.py, decorrequirements.py, and the configurations in Dockerfile.freeze, here is a comprehensive list of the Python modules and system dependencies required for this project.

### **🐍 Python Standard Library Modules**

These modules are included with Python and do not require separate installation:

* **asyncio**: Used for the asynchronous core, handling multiple tasks like MQTT listening and browser automation simultaneously.  
* **logging**: For system-wide logging to both console and logfile.log.  
* **json**: For parsing and encoding MQTT payloads.  
* **datetime, time, calendar**: To manage shift timing, stealth delays, and schedule calculations.  
* **hashlib**: Used to generate MD5/SHA256 hashes for tracking change detection in opportunities.  
* **dataclasses**: To define structured data objects like Opportunity and DictData.  
* **imaplib & email**: Used by the "Email Peeker" to check for work notifications via IMAP.  
* **re**: For regex pattern matching in StartTimeRequirement and SMS code extraction.  
* **socket**: To retrieve the local hostname for MQTT status reporting.  
* **pickle**: To save and load the state of processed emails to prevent duplicate alerts.

---

### **📦 Third-Party Python Packages**

These must be installed via pip (as seen in the Dockerfile):

| Package | Purpose |
| :---- | :---- |
| **playwright** | The core browser automation engine used to navigate the A-to-Z portal. |
| **playwright-stealth** | Applies evasion techniques to hide the browser's automated nature. |
| **aiomqtt** (formerly asyncio-mqtt) | Asynchronous client for communicating with the MQTT broker. |
| **httpx** | Handles asynchronous HTTP requests for GraphQL mutations and 2Captcha API calls. |
| **pyautogui** | Used for desktop-level interactions, specifically for entering PINs during authentication. |
| **Pillow (PIL)** | Required for image processing, such as cropping and overlaying grids on Captchas. |
| **python-dateutil** | Provides parser.isoparse for handling complex ISO date strings from the API. |

---

### **🖥️ System & Environment Dependencies**

The project also relies on several external system tools defined in the Dockerfile.freeze and shell scripts:

* **Playwright Browsers**: Specifically Chromium, installed via playwright install chromium.  
* **Mosquitto Clients**: The mosquitto\_sub and mosquitto\_pub commands are used by the watchdog script for health checks.  
* **X11 Server / Xvfb**: Required for the GUI-based browser to run in a containerized environment.  
* **VirtualHere Client**: (vhclient) Used for USB/Hardware passthrough, likely for security keys or authentication devices.  
* **Docker**: The project is designed to run in a containerized environment using the Dockerfile.freeze.

### **How to Install**

If you are setting this up manually without Docker, you would typically run:

Bash

pip install playwright playwright-stealth aiomqtt httpx pyautogui Pillow python-dateutil

playwright install chromium

**Here is the complete requirements.txt content for your project. This includes all necessary libraries identified from the source code imports and the Docker build instructions.**

### **requirements.txt**

**Plaintext**

**\# Browser Automation & Evasion**

**playwright\>=1.40.0**

**playwright-stealth\>=1.0.6**

**\# Asynchronous Networking**

**aiomqtt\>=2.0.0**

**httpx\>=0.25.0**

**\# GUI & Desktop Interaction**

**pyautogui\>=0.9.54**

**\# Image Processing (Captcha Handling)**

**Pillow\>=10.0.0**

**\# Date & Time Utilities**

**python-dateutil\>=2.8.2**

**\# Email & Data Handling**

**\# (Standard libraries like imaplib/pickle are included in Python)**

---

### **Project Dependency Architecture**

**The following diagram illustrates how these modules interact within your system to handle the automation lifecycle:**

### **Module Breakdown & Justification**

* **playwright & playwright-stealth: Essential for navigating the Amazon A-to-Z portal while mimicking a real browser to avoid detection.**  
* **aiomqtt: The asynchronous backbone that allows the bot to listen for schedule updates from requirements.htm and schedule.htm without blocking the browser logic.**  
* **httpx: Used for high-speed GraphQL mutations (the "Smash and Grab" logic) and communicating with the 2Captcha API for AWS WAF challenges.**  
* **pyautogui: A fallback for desktop-level input, specifically used in the code to handle PIN entry for WebAuthn/Passkey prompts.**  
* **Pillow: Used to process screenshots of Captchas, allowing the bot to draw grids and identify click coordinates for the solver.**  
* **python-dateutil: Critical for parsing the ISO 8601 timestamps returned by the Amazon GraphQL API into Python datetime objects.**

### **Final Installation Steps**

1. **Place the text above into a file named requirements.txt.**  
2. **Install the packages:**  
3. **Bash**

**pip install \-r requirements.txt**

4.   
5.   
6. **Install the Chromium binaries (required for Playwright):**  
7. **Bash**

**playwright install chromium**

8.   
9. 

