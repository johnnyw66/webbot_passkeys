import logging
import time
import configure
import javascripts
import pyautogui
import asyncio
from asyncio.exceptions import InvalidStateError


# Playwright
from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async
from playwright._impl._errors import TargetClosedError


import httpx
from httpx import HTTPStatusError, RequestError, TimeoutException


from datetime import datetime, timedelta, timezone, date
from dateutil import parser

import json

import random
import string

from dataclasses import dataclass
import unicodedata

from aiomqtt import Client as AsyncMQTTClient, MqttError

import os
import pickle

# Email Peeker
from pathlib import Path
import imaplib
import email
from email.header import decode_header

import hashlib

import socket

import io
from PIL import Image, ImageDraw, ImageFont
import base64
import sys

from decorrequirements import *

CAPTURE_DEBUG = True

AWS_CAPTURE_TIMEOUT = 180
FARM_URL = "https://httpbin.org/post"
FARM_ID = "YOUR AWS CAPTCHA FARM ID"
FARM_SECRET="YOUR AWS CAPTCHA FARM SECRET"

TOP_MARGIN = 70
BOTTOM_MARGIN = 80

file_logger = logging.getLogger('file_logger')
file_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('logfile.log', mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(name)s %(levelname)s: %(asctime)s: %(message)s')
file_handler.setFormatter(file_formatter)
file_logger.addHandler(file_handler)
file_logger.info(f"File Logging Started: {datetime.now()}")

class LogoutException(Exception):
    pass

@dataclass
class HashObject:
    hash:str

    #def __post_init__(self):
    #    hash = ''

@dataclass
class ValueWrapper:
    value: object

    def __eq__(self, other):
        if not isinstance(other, ValueWrapper):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def as_str(self) -> str:
        """Return the value as a string."""
        return str(self.value)

    def is_primitive(self) -> bool:
        """Check if the value is a primitive type."""
        return isinstance(self.value, (int, str, bool))

    def describe(self) -> str:
        """Return a description of the type and value."""
        return f"Type: {type(self.value).__name__}, Value: {self.value}"

class StealthDelayer:
    __slots__ = ('delay_wrapper', 'cancel_event', 'chunk_size')

    def __init__(self, delay_wrapper, cancel_event=None, chunk_size=0.25):
        """
        delay_wrapper: an object with a .value attribute (float, in seconds)
        cancel_event: asyncio.Event, shared externally for cancellation
        chunk_size: sleep interval granularity (default: 0.25s)
        """
        self.delay_wrapper = delay_wrapper
        self.cancel_event = cancel_event or EventWrapper()
        self.chunk_size = chunk_size

    async def wait(self):
        """
        Waits until either:
        - the delay elapses (can be shortened externally via delay_wrapper)
        - the cancel_event is set
        """
        logging.info(f"StealthDelayer wait(): START. MAX DELAY={self.delay_wrapper.value}s, CHUNK SIZE={self.chunk_size}s  CANCEL_EVENT {self.cancel_event}")
        elapsed_time = 0

        while True:
            if self.cancel_event.is_set():
                logging.info("StealthDelayer: CANCELLED early.")
                break

            current_delay = self.delay_wrapper.value
            if elapsed_time >= current_delay:
                break

            remaining_time = max(0, current_delay - elapsed_time)
            sleep_time = min(self.chunk_size, remaining_time)
            await asyncio.sleep(sleep_time)
            elapsed_time += sleep_time

        logging.info("StealthDelayer: DONE.")

    def set_delay(self, value):
        if value < 0:
            raise ValueError("Delay must be non-negative")
        logging.info(f"StealthDelayer: delay set to {value:.2f}s")
        self.delay_wrapper.value = value

    def cancel(self):
        """Externally trigger a cancel event."""
        try:
            self.cancel_event.set("Stealth Delay Cancel")
        except TypeError:
            self.cancel_event.set()

    def reset_if_set(self):
        logging.info("StealthDelayer: reset_if_set() - Check.")
        if self.cancel_event.is_set():
            logging.info("Reset Cancel Event after being set")
            """Manually clear the cancel event (e.g. before reuse)."""
            self.cancel_event.clear()
            logging.info(f"{self}")
        
    def __str__(self):
        return f"StealthDelayer: MAX DELAY: {self.delay_wrapper} CANCEL_EVENT: {self.cancel_event} CHUNK: {self.chunk_size}"

class EventWrapper():

    def __init__(self, val=None):
        self._event = asyncio.Event()
        self._shared = val

    def set(self, shared):
        logging.debug(f"EventWrapper: Set event. Shared data: {self._shared}")
        self._shared = shared
        self._event.set()

    def get(self):
        logging.debug(f"EventWrapper: Get event. Shared data: {self._shared}")
        return self._shared

    def is_set(self):
        return self._event.is_set()

    async def wait(self, timeout=None):
        logging.debug("Waiting for event...")
        if timeout:
            try:
                await asyncio.wait_for(self._event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logging.debug("EventWrapper: Timeout occurred while waiting for event.")
                raise asyncio.TimeoutError("Timeout occurred while waiting for the event.")
        else:
            await self._event.wait()


    def clear(self):
        logging.debug(f"EventWrapper: Clearing event. Shared data was: {self._shared}")
        self._shared=None
        self._event.clear()

    def __str__(self):
        return f"{self._event}: shared:{self._shared}"


@dataclass
class Opportunity:
    data: dict

    def __post_init__(self):
        #for key, value in self.data.items():
        #    setattr(self, key, value)
        for key,value in sorted(self.data.items()):
            normvalue = unicodedata.normalize('NFC', value) if isinstance(value,str) else value 
            setattr(self, key, normvalue if not isinstance(value,list) else tuple(sorted(value)))
            #setattr(self, key, value)



    def __str__(self):
        items = [f"{key}: {value}" for key, value in self.data.items()]
        return f"Opportunity: {{ {', '.join(items)} }}"



class ProcessedEmailsManager:
    def __init__(self, file_path):
        self.file_path = file_path
        #self.processed_emails = {}
        self.last_saved_hash = None
        self.load_emails()

    def _hash_dict(self, data):
        """Generate a hash for the dictionary."""
        dict_bytes = pickle.dumps(data)  # Serialize the dictionary
        return hashlib.sha256(dict_bytes).hexdigest()  # Return the hash

    def _generate_email_hash(self, from_, subject, date, body):
        """Generate a unique hash for an email using its from_, subject, date, and body content."""
        hash_input = f"{from_}-{subject}-{date}-{body}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()

    def dump(self):
        """Load and print the processed emails dictionary."""
        for email_hash, metadata in self.processed_emails.items():
            print(f"Hash: {email_hash}")
            print(f"  Subject: {metadata['subject']}")
            print(f"  Date: {metadata['date']}")
            print(f"  Processed: {metadata['processedtime']}")
            print()

    def email_exists(self, from_, subject, date, body):
        return self._generate_email_hash(from_, subject, date, body) in self.processed_emails

    def load_emails(self):
        """Load processed emails from a file."""
        if Path(self.file_path).is_file():
            with open(self.file_path, "rb") as f:
                self.processed_emails = pickle.load(f)
            self.last_saved_hash = self._hash_dict(self.processed_emails)  # Update the saved hash
            logging.info(f"Loaded {len(self.processed_emails)} processed emails.")
        else:
            logging.info("No previous processed emails found. Starting fresh.")
            self.processed_emails = {}

    def save_emails(self):
        """Save processed emails to a file if there are changes."""
        current_hash = self._hash_dict(self.processed_emails)
        if current_hash != self.last_saved_hash:
            with open(self.file_path, "wb") as f:
                pickle.dump(self.processed_emails, f)
            self.last_saved_hash = current_hash  # Update the saved hash
            logging.info(f"Saved {len(self.processed_emails)} processed emails.")
        else:
            #logging.info("No changes detected. Skipping save.")
            pass

    def add_email(self, from_, subject, date, body):
        email_hash = self._generate_email_hash(from_, subject, date, body)
        """Add a new email to the processed emails."""
        current_datetime = datetime.now()
        self.processed_emails[email_hash] = {"from": from_, "subject": subject, "date": date , "body": body, "processedtime":current_datetime}


# Replacement function to deal with older versions of datetime library.
def fromisoformat(iso_string):
    return datetime.fromisoformat(iso_string) if not iso_string.endswith('Z') else datetime.fromisoformat(iso_string[:-1]+'+00:00')

def dbg_exception(o:str, e:Exception):
    if (configure.DEBUG_EXCEPTION):
        logging.info(f"dbg_exception: {o}, {type(e)}")


async def email_peeker(email_event):
    pause = 3.0
    PROCESSED_EMAILS_FILE = "email_processed.pkl"
    processed_emails=ProcessedEmailsManager(PROCESSED_EMAILS_FILE)  # Load processed emails at the start

    # Returns True - if our email is the one we are looking for
    # Looking for VETs or VTOs from 'amazon'
    def wanted_email(from_, subject):
        return ("amazon" in from_.lower() or configure.TEST_EMAIL_ALERTS) and \
                any(sub in subject for sub in configure.EMAIL_ALERT_SUBJECTS) and \
                "available" in subject

    logging.info("email_peeker- starting....")
    try:
        # Call the function periodically
        #await voice_monkey()
        counter = 0 
        while True:
            await check_inbox(processed_emails, wanted_email, email_event)
            print(f"Email Peeker: Waiting for {pause} seconds before checking again... {counter} {email_event}\r", end="")

            processed_emails.save_emails()  # Save processed emails after each cycle

            counter = counter + 1
            #if (counter % 10 == 0):
            #    await update_status(counter)
            await asyncio.sleep(pause)  # Sleep for a few seconds.

    except (asyncio.exceptions.CancelledError, KeyboardInterrupt):
        logging.info("\nStopping the email peeker. Saving state...")
        processed_emails.save_emails()  # Save processed emails before exiting
        logging.info("State saved. Goodbye!")
    except Exception as e:
        logging.info("-------------->", e, type(e), "<====================")


async def check_inbox(processed_emails, wanted_email, email_event):
    try:
        # Connect to the server
        mail = imaplib.IMAP4_SSL(configure.IMAP_SERVER)
        mail.login(configure.EMAIL, configure.EMAIL_APP_PASSWORD)
        mail.select("inbox", readonly=True)  # Open mailbox in read-only mode

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        if status == "OK":
            email_ids = messages[0].split()
            for email_id in email_ids:
                # Fetch the email using BODY.PEEK
                res, msg = mail.fetch(email_id, "(BODY.PEEK[])")
                for response in msg:
                    if isinstance(response, tuple):
                        # Parse the email content
                        msg = email.message_from_bytes(response[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        from_ = msg.get("From")
                        date = msg.get("Date")

                        # Extract the body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()

                        # Check if the email has been processed
                        if processed_emails.email_exists(from_, subject, date, body):
                            logging.debug(f"Email already processed. Skipping...{from_} {subject} {date}")
                            continue

                        # Process the email
                        logging.info(f"New Email:\nSubject: {subject}\nFrom: {from_}\nDate: {date}\nBody: {body[:50]}...\n")
                        email_msg = {
                            "body": body,
                            "from": from_,
                            "subject": subject,
                        }
                        lsub = subject.lower()
                        if (wanted_email(from_, lsub)):
                            logging.info(f"***Email Match*** {subject}")
                            email_event.set(email_msg)
                        else:
                            pass

                        # Mark the email as processed
                        processed_emails.add_email(from_, subject, date, body)
        else:
            logging.info("No new emails.")
        mail.logout()
    except Exception as e:
        logging.info(f"Error: {e}")



async def subscribe_and_process(topic: str, message_handler: callable):
    while True:
        try:
            async with AsyncMQTTClient(hostname=configure.MQTT_BROKER, port=configure.MQTT_PORT,
                                       username=configure.MQTT_USERNAME, password=configure.MQTT_SECRET) as client:
                await client.subscribe(topic, qos=1)
                async for message in client.messages:
                    await message_handler(message)
        except asyncio.CancelledError:
            logging.info(f"Subscription to {topic} was canceled.")
            break
        except Exception as e:
            logging.error(f"An error occurred in subscription to {topic}: {e}")
            await asyncio.sleep(3)  # Retry after a delay

async def voice_monkey(message="INSERT YOUR MESSAGE HERE", device=configure.VOICEMONKEY_DEVICE):
    logging.info(f"Initiating Voice Monkey message to device {device}")
    async with httpx.AsyncClient() as client:
        url = "https://api-v2.voicemonkey.io/announcement"
        vm_payload = {      "token": configure.VOICEMONKEY_TOKEN,
                            "text": message,
                            "device": device}
        response = await client.get(url, params = vm_payload) #headers = headers)
        logging.info(f"{response} from voice monkey")

def bomb_out(reason:str=None):
    logging.info(f"***BOMB OUT*** REASON: '{reason if reason is not None else 'None given'}'")
    time.sleep(5)
    os._exit(-1)
 
async def monitor_url(page):
    current_url = page.url
    while True:
        if page.url != current_url:
            logging.info(f"monitor_url: URL changed: {current_url} -> {page.url}")
            current_url = page.url
            if "federate_callback" in current_url:
                logging.warning(f"***************************************** Reached federate_callback URL — possible stale or invalid SAML token: {current_url}")
            if "logout" in current_url:
                # Somewhere - we have failed - perhaps too late to click are you still there.
                bomb_out('Logged out by system.')
            if "myhr" in current_url:
                bomb_out('My HR')
                pass

        await asyncio.sleep(1)  # Check every second


async def passkey_entry(page):
    pin = "0000"    #configure.PASSKEYPIN
    logging.info("Passkey entry: Simulate touch and PIN **** @TODO")
    await asyncio.sleep(5)
    pyautogui.typewrite(pin)
    pyautogui.press("enter")
    await asyncio.sleep(10)
    if (not "voluntary_time_off" in page.url):
        logging.info("WE HAVE NOT ARRIVED!!!!!!!!!!! WE MIGHT HAVE TO DO SOMETHING.... (one last chance)")
        await asyncio.sleep(10)
        if (not "voluntary_time_off" in page.url):
            logging.info("WE HAVE NOT ARRIVED!!!!!!!!!!! DO SOMETHING")
            bomb_out("WE FAILED TO AUTHENTICATE")    
    logging.info("Looks like we got through authentication...")


async def handle_webauthn(webauth_event):
    while True:
        try:
            logging.info(f"⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰ Waiting for WebAuthn ⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰⏰")
            await webauth_event.wait(timeout=None) 
            webauth = webauth_event.get()
            logging.info(f"passkey_entry: We got something from our webauth event {webauth}")
            webauth_event.clear()
            await asyncio.sleep(5)
            pyautogui.typewrite("0000")
            pyautogui.press("enter")
        except Exception:
            bomb_out("PROBLEM WITH WEBAUTH")    
        


async def wait_for_movement(page):
    await asyncio.sleep(20)
    if (not "atoz.amazon.work" in page.url):
        logging.info("WE HAVE NOT ARRIVED!!!!!!!!!!! WE MIGHT HAVE TO DO SOMETHING.... (one last chance)")
        await asyncio.sleep(20)
        if (not "atoz.amazon.work" in page.url):
            logging.info("WE HAVE NOT ARRIVED!!!!!!!!!!! DO SOMETHING")
            bomb_out("WE FAILED TO AUTHENTICATE")    
    logging.info("✅✅✅✅✅✅✅✅ Looks like we got through authentication...✅✅✅✅✅✅✅✅")



# Handle pass key setup prompts (prior to agreeing to setting this up and then the subsequent 'webauthn' login)
async def handle_passkey_pin(page, webauth_event):
    while True:
        try:
            # Post registration
            signin_btn =  page.locator('button[data-testid="webauthn-signin-button"]')
            if await signin_btn.count() > 0 and await signin_btn.is_visible():
                await signin_btn.click()
                await wait_for_movement(page)
                #await passkey_entry(page)
            else:
                # Pre registration - use SMS OTPs
                # Step 1: Click main page 'Remind me later'
                main_btn = page.locator("div.passkey-container button:has-text('Remind me later')")
                if await main_btn.count() > 0 and await main_btn.is_visible():
                    logging.info("Clicked main page 'Remind me later' button")
                    await main_btn.click()
                    await asyncio.sleep(2)  # we know the modal pop up will take some time to come up.

                    
                # Step 2: Click modal 'Remind me later' if modal appeared
                modal_btn = page.locator("#passkeyConfirmModal button:has-text('Remind me later')")
                if await modal_btn.count() > 0 and await modal_btn.is_visible():
                    logging.info("Clicked modal 'Remind me later' button")
                    await modal_btn.click()
            
        except PlaywrightTimeoutError:
            # Ignore timeout if button not yet visible
            dbg_exception("handle_passkey_pin TimeOutError",toe)
            pass
        except Exception as e:
            # Log any unexpected exception
            print(f"Exception in handle_passkey_pin: {e}")

        # Small delay to prevent tight loop
        await asyncio.sleep(2)


# Click on 'Stay In' modal button - if it appears
async def handle_session_modal(page):

    button_stay_in_id = "#session-expires-modal-btn-stay-in"
    button_stay_logged_in_text = 'Stay logged in'

    while True:
        try:
            # Wait for the button to appear
            await page.locator("button:has-text('Stay logged in')").click(timeout=4000)
            logging.info("'Stay logged in' button - Clicked Complete. Wait a while for it to go off")
            await asyncio.sleep(2)
            logging.info("**handle_session_modal: Completed. Waiting for next modal session timeout**")
        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_session_modal TimeOutError",toe)
            #print("STAY LOGGED IN TIMEOUT..")
            pass
        except Exception as e:
            dbg_exception("handle_session_modal Exception",e)
            print(f"*********************************************FAILED TO CLICK {e}")
            pass

        await asyncio.sleep(0.5)  # Sleep for a few seconds.


async def handle_opt_device_select(page,otp_index):
    logging.info(f"handle_opt_device_select: OTP INDEX: {otp_index}")
    while True:
        try:
            await page.wait_for_selector("form#selectPhone_form", timeout = 3000)
            await page.check(f'input[type="radio"][value=\"{otp_index}\"]')
            await page.click('button[type="submit"]')

        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_opt_device_select TimeoutError",toe)
            pass
        except Exception as e:
            dbg_exception("handle_opt_device_select Exception",e)
            pass
        await asyncio.sleep(3)  # Sleep for a few seconds.
              
    
async def handle_otp_pin(page,otp_event):
    while True:
        try:
            await page.wait_for_selector('form#otp-form',timeout = 5000)
            await page.check('input[type="checkbox"][id="trustedDevice"]')

            while True:
                try:
                    logging.info("handle_otp_pin: Waiting for OTP SMS")
                    await otp_event.wait(timeout=60.0) # Wait for the event with a timeout of 60 seconds
                    verification_code = otp_event.get()
                    logging.info(f"handle_otp_pin: We got something from our event {verification_code}")
                    otp_event.clear()
                    await page.fill('input[name="code"]',verification_code)        
                    await page.click('button[type="submit"]')
                    logging.info(f"filled form with verification code {verification_code}")
                    await asyncio.sleep(3)  # Sleep for a few seconds - making sure this form closes
                    break 
                except asyncio.TimeoutError:
                    logging.info("handle_otp_pin: Timeout occurred while waiting for the event.")
                    break

        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_otp_pin TimeoutError", toe)
            pass
        except Exception as e:
            dbg_exception("handle_otp_pin", e)
            pass
        await asyncio.sleep(0.1)  # Sleep for a few seconds.

async def handle_aa_login(page):
    
    while True:
        input_selector = 'input#associate-login-input'

        try:
            # Wait for the credential inputs to be present on the page

            await page.wait_for_selector(input_selector, timeout=3000)
            logging.info("FOUND AA LOGIN")
            await page.fill('input[name="login"]', configure.ATOZ_USERNAME)
            #await page.fill('input[name="password"]', configure.ATOZ_PASSWORD)
            # Submit the credentials
            await page.click('button[type="submit"]')

        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_aa_login TimeoutError", toe)
            pass     
        except Exception as e:
            dbg_exception(f"handle_aa_login: Input with ID {input_selector} is not present on the page within the timeout. '{e}'", e)
            pass

        await asyncio.sleep(3)  # Sleep for a few seconds.


async def handle_login(page):
    while True:
        try:
            await page.wait_for_selector('input[name="password"]', timeout=5000)

            # Only fill login if not readonly
            login_input = await page.query_selector('input[name="login"]')

            if (await login_input.get_attribute("readonly")) is None:
                await page.fill('input[name="login"]', configure.ATOZ_USERNAME)
            else:
                logging.info("handle_login: Username is readonly — skipping")

            # Fill password
            await page.focus('input[name="password"]')
            await page.fill('input[name="password"]', configure.ATOZ_PASSWORD)

            # Press Enter instead of clicking
            await page.press('input[name="password"]', "Enter")

            # --- Fallback: if still on same page after delay, click button ---
            try:
                await page.wait_for_selector('form#loginForm', timeout=3000, state="detached")
                logging.info("Form submitted successfully via Enter.")
            except PlaywrightTimeoutError:
                logging.info("handle_login: Form still visible — retrying via button click.")
                try:
                    await page.click('button[type="submit"]', timeout=3000)
                except Exception as e:
                    logging.info(f"handle_login: Button click failed: {e}")


        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_login TimeoutError", toe)

        except Exception as e:
            dbg_exception(f"handle_login exception: {e}",e)

        await asyncio.sleep(3)


async def handle_404_page(page, wanted_url):
    while True:
        #print(f"Checking for 404 - {wanted_url} current {page.url}")
        if ('404' in page.url):
            logging.info(f"404! Going back to {wanted_url}")
            await page.goto(wanted_url)

        await asyncio.sleep(5)  # Sleep for a few seconds.

async def handle_vto_page(page):
    # Note: VTO by clicking buttons will only really work autonomously if configure.REACT_REFRESH is True.
    while True:
        try:
            vto_page = ('voluntary_time_off' in page.url)

            # Click the 'Accept' button (if viewing VTO page)
            if (vto_page):
                #logging.info("Clicking VTO Accept button...")
                await page.locator("button:has-text('Accept')").click(timeout=2000)
                logging.info("'Accept' VTO button - Clicked Complete. Wait a while for it to go off")

                await asyncio.sleep(0.5)
                
        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_vto_page TimeOutError",toe)
            pass
        except Exception as e:
            dbg_exception("handle_vto_page Exception",e)
            pass

        await asyncio.sleep(0.5)  # Sleep for a few seconds.

async def handle_vto_accept_page(page):
    # Note: VTO by clicking buttons will only really work autonomously if configure.REACT_REFRESH is True.
    while True:
        try:
            vto_page = ('voluntary_time_off' in page.url)

            # Click the 'Accept VTO' button (if viewing VTO page)
            if (vto_page):
                #await page.wait_for_selector("button:has-text('Accept VTO')", timeout=2500)
                await page.locator("button:has-text('Accept VTO')").click(timeout=2500)
                logging.info("'Accept VTO' button - Clicked Complete. Wait a while for it to go off")
                await asyncio.sleep(0.5)
                
        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_vto_accept_page TimeOutError",toe)
            pass
        except Exception as e:
            dbg_exception("handle_vto_accept_page Exception",e)
            pass

        await asyncio.sleep(0.5)  # Sleep for a few seconds.

async def handle_vto_view_page(page):
    # Note: VTO by clicking buttons will only really work autonomously if configure.REACT_REFRESH is True.
    while True:
        try:
            vto_page = ('voluntary_time_off' in page.url)

            # Click the 'Accept VTO' button (if viewing VTO page)
            if (vto_page):
                #await page.wait_for_selector("button:has-text('View VTO')", timeout=2500)
                await page.locator("button:has-text('View VTO')").click(timeout=2500)
                logging.info("'View VTO opportunities' button - Clicked Complete. Wait a while for it to go off")
                await asyncio.sleep(0.5)
                
        except PlaywrightTimeoutError as toe:
            dbg_exception("handle_vto_view_page TimeOutError",toe)
            pass
        except Exception as e:
            dbg_exception("handle_vto_view_page Exception",e)
            pass

        await asyncio.sleep(0.5)  # Sleep for a few seconds.



# +++++++++++++++++++++++++++++++++++ START of AWS Captcha handling +++++++++++++++++++++++++++++++++++

from typing import Optional

CREATE_TASK_URL = "https://api.2captcha.com/createTask"
GET_TASK_URL = "https://api.2captcha.com/getTaskResult"
GETBALANCE_URL = "https://api.2captcha.com/getBalance"
REPORT_INCORRECT_URL = "https://api.2captcha.com/reportIncorrect"

HEADERS = {"Content-Type": "application/json"}

MAX_RETRIES = 5
RETRY_BACKOFF = 3  # seconds (base for exponential backoff)


async def resilient_post(url: str, payload: dict, timeout: float = 30.0) -> Optional[dict]:
    """Make a POST request with retries and exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=HEADERS, timeout=timeout)
                response.raise_for_status()
                return response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
            logging.warning(f"HTTP request failed (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES:
                raise
            backoff = RETRY_BACKOFF * attempt
            logging.debug(f"Retrying after {backoff:.1f} seconds...")
            await asyncio.sleep(backoff)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise

async def report_incorrect(taskId:int) -> str:
    payload = {
        "clientKey": configure.TWO_CAPTCHA_API_KEY,
        "taskId":taskId
    }
    logging.info(f"Report Incorrect Task {taskId}")
    data = await resilient_post(REPORT_INCORRECT_URL, payload)
    logging.info(f"report_incorrect: {data}")

    if data.get("errorId") != 0:
        raise Exception(f"2Captcha reportIncorrect failed: {data.get('errorDescription')}")
    return data["status"]

async def get_captcha_balance() -> float:
    payload = {
        "clientKey": configure.TWO_CAPTCHA_API_KEY,
    }

    data = await resilient_post(GETBALANCE_URL, payload)
    logging.info(f"get_captcha_balance: {data}")

    if data.get("errorId") != 0:
        raise Exception(f"2Captcha getBalance failed: {data.get('errorDescription')}")
    return data["balance"]


async def create_grid_task(question_b64: str, grid_b64: str, rows=3, columns=3) -> int:
    payload = {
        "clientKey": configure.TWO_CAPTCHA_API_KEY,
        "task": {
            "type": "GridTask",
            "body": grid_b64,
            "imgInstructions": question_b64,
            "rows": rows,
            "columns": columns
        }
    }

    data = await resilient_post(CREATE_TASK_URL, payload)
    logging.info(f"create_grid_task: {data}")
    if data.get("errorId") != 0:
        raise Exception(f"2Captcha createTask failed: {data.get('errorDescription')}")
    return data["taskId"]


async def poll_grid_task(task_id: int, poll_interval=10, timeout=180) -> str:
    payload = {
        "clientKey": configure.TWO_CAPTCHA_API_KEY,
        "taskId": task_id
    }
    logging.info(f"poll_grid_task: payload: {payload}")
    deadline = asyncio.get_event_loop().time() + timeout

    while True:
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError(f"Polling timed out after {timeout} seconds")

        try:
            data = await resilient_post(GET_TASK_URL, payload, timeout=20.0)
            logging.info(f"poll_grid_task: returned from  getTaskResult post {data}")
        except Exception as e:
            logging.warning(f"Polling error: {e}")
            await asyncio.sleep(poll_interval)
            continue

        if data.get("status") == "processing":
            logging.info("2Captcha still processing… waiting")
            await asyncio.sleep(poll_interval)
            continue

        if data.get("status") == "ready":
            solution = data.get("solution", {})
            if "click" in solution:
                return ",".join(str(i) for i in solution["click"])
            else:
                raise Exception("2Captcha returned 'ready' but no answers found")

        if data.get("errorCode") == "ERROR_CAPTCHA_UNSOLVABLE":
            raise Exception("2Captcha: CAPTCHA was unsolvable")

        raise Exception(f"2Captcha getTaskResult returned unexpected result: {data}")


# Send AWS Capture Challenge over HTTP question and challenge are base64 PNG images
# from the AWS Captcha form

async def farm_capture_challenge_over_http(question:str, challenge: str, answer_event: EventWrapper):
    taskId = await create_grid_task(question, challenge)
    logging.info(f"farm_capture_challenge_over_http taskId: {taskId}")
    answer_message = await poll_grid_task(taskId)
    answer_event.set((answer_message, taskId))


# Send AWS Capture Challenge over MQTT
async def farm_capture_challenge_over_mqtt(question,challenge):
    retry_delay = 1  # Initial retry delay
    while True:
        try:
            async with AsyncMQTTClient(
                hostname=configure.MQTT_BROKER,
                port=configure.MQTT_PORT,
                username=configure.MQTT_USERNAME,
                password=configure.MQTT_SECRET
            ) as client:
                logging.info(f"publish challenge - {question[0:5]}, {challenge[0:5]}")
                payload = json.dumps({"question": question, "challenge": challenge})
                await client.publish(f'captcha', payload, retain=True, qos=1)
            break  # Exit retry loop on success
        except MqttError as e:
            logging.warning(f"MQTT connection failed: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s

async def handle_capture_answer(message, answer_event):
    logging.info("HANDLE CAPTURE ANSWER OVER MQTT")
    try:
        msg_payload = message.payload.decode('utf-8')
        data = json.loads(msg_payload)                 # Parse JSON string to dict
        logging.info(f"payload: {data}")
        answer = data['answer']
        challengeID = data['challengeID']
        answer_event.set((answer, challengeID))
    except Exception as e:
        logging.warning(f"Topic: {message.topic}. Problem handling Captcha Answer Message.{e}")

async def receive_captcha_answer(answer_event):
    capture_answer_topic = f"captcha_answer/#"
    logging.info(f"MQTT receive_captcha_answer() topic {capture_answer_topic}")
    await subscribe_and_process(capture_answer_topic, lambda message: handle_capture_answer(message, answer_event))

async def handle_captcha_form(page, answer_event):
    captcha_form_id = "#captchaForm"

    while True:
        try:

            await page.wait_for_function("document.querySelector('#captchaForm') !== null", timeout=5000)
            logging.info("CAPTCHA FORM IDENTIFIED!!!!!! FARM OFF. FARM OFF FARM OFF")
            await farm_capture(page, answer_event)

            #balance = await get_captcha_balance()
            #logging.info(f"----------->2Captcha Balance {balance}<-----------------")

        except PlaywrightTimeoutError as toe:
            dbg_exception(f"handle_captcha_form TimeOutError", toe)
            pass
        except Exception as e:
            dbg_exception("handle_captcha_form Exception",e)
            pass

async def scale_css_box(page, box, *args):
    device_pixel_ratio = await page.evaluate("window.devicePixelRatio")
    scaled_box = {k: v * device_pixel_ratio for k, v in box.items()}
    scaled_args = tuple(a * device_pixel_ratio for a in args)
    return scaled_box, scaled_args if args else None


async def capture_captcha_quiz_as_base64(page, selector="#captcha-container", top_margin=TOP_MARGIN, bottom_margin=BOTTOM_MARGIN, x_scale=0.5, y_scale=0.5):
    container = page.locator(selector)
    await container.wait_for(state="visible", timeout=10000)

    box = await container.bounding_box()
    if not box:
        logging.error("❌ CAPTCHA container not found")
        return None, None

    # Scale bounding box and margins
    box, scaled_margins = await scale_css_box(page, box, top_margin, bottom_margin)
    if scaled_margins:
        scaled_top_margin, scaled_bottom_margin = scaled_margins
    else:
        scaled_top_margin = top_margin
        scaled_bottom_margin = bottom_margin

    screenshot_bytes = await page.screenshot(full_page=True)
    image = Image.open(io.BytesIO(screenshot_bytes))

    left = int(box['x'])
    top = int(box['y'])
    width = int(box['width'])
    height = int(box['height'])
    right = left + width
    bottom = top + height

    # Crop full captcha container from screenshot
    captcha_image = image.crop((left, top, right, bottom))

    # Crop question section (top margin height)
    question_height = int(scaled_top_margin)
    question_image = captcha_image.crop((0, 0, width, question_height))

    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:
        resample_filter = Image.ANTIALIAS  # Pillow < 10 fallback

    # Scale down question_image by x_scale and y_scale
    new_width = int(width * x_scale)
    new_height = int(question_height * y_scale)
    if new_width > 0 and question_height > 0:
        question_image = question_image.resize((new_width, new_height), resample_filter)

    # Crop cells section (middle area, excluding top and bottom margins)
    cells_height = height - int(scaled_top_margin) - int(scaled_bottom_margin)
    cells_image = captcha_image.crop((0, int(scaled_top_margin), width, int(scaled_top_margin) + cells_height))

    # Scale down cells_image by x_scale and y_scale
    new_width = int(width * x_scale)
    new_height = int(cells_height * y_scale)
    if new_width > 0 and new_height > 0:
        cells_image = cells_image.resize((new_width, new_height), resample_filter)

    def to_base64(img):
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    question_b64 = to_base64(question_image)
    cells_b64 = to_base64(cells_image)

    return question_b64, cells_b64

async def capture_captcha_quiz_as_base64_deprecated(page, selector="#captcha-container"):
    logging.info("building base64 captcha image...")
    # Wait for CAPTCHA container to be visible
    container = page.locator(selector)
    await container.wait_for(state="visible", timeout=10000)

    # Get bounding box of the captcha container
    box = await container.bounding_box()
    if not box:
        print("❌ CAPTCHA container not found")
        return

    box, _ = await scale_css_box(page, box)

    # Take full page screenshot as bytes
    screenshot_bytes = await page.screenshot(full_page=True)

    # Load into Pillow Image
    image = Image.open(io.BytesIO(screenshot_bytes))

    # Crop the CAPTCHA region
    left = int(box['x'])
    top = int(box['y'])
    right = left + int(box['width'])
    bottom = top + int(box['height'])
    captcha_image = image.crop((left, top, right, bottom))

    # Save cropped image to bytes buffer as PNG
    buffer = io.BytesIO()
    captcha_image.save(buffer, format="PNG")
    png_data = buffer.getvalue()

    # Encode PNG bytes to base64 string
    b64_str = base64.b64encode(png_data).decode('utf-8')
    return b64_str

async def save_captcha_grid_overlay(
    page,
    selector="#captcha-container",
    rows=3,
    cols=3,
    top_margin=0,
    bottom_margin=0,
    filename="captcha_overlay.png"
):
    locator = page.locator(selector)
    box = await locator.bounding_box()
    if not box:
        print("❌ CAPTCHA container not visible")
        return

    box, (top_margin, bottom_margin) = await scale_css_box( page, box, top_margin, bottom_margin)

    #
    logging.info(f"BOX {box} top_margin: {top_margin} bottom_margin: {bottom_margin}")
    # Capture full page screenshot
    screenshot_bytes = await page.screenshot(full_page=True)
    image = Image.open(io.BytesIO(screenshot_bytes))

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    # Adjust usable grid area
    usable_height = box['height'] - top_margin - bottom_margin
    cell_width = box['width'] / cols
    cell_height = usable_height / rows
    logging.info(f"CELL DIMENSION wxh: {cell_width}x{cell_height}")

    for i in range(rows * cols):
        row = i // cols
        col = i % cols

        x = box['x'] + col * cell_width
        y = box['y'] + top_margin + row * cell_height
        rect = [x, y, x + cell_width, y + cell_height]

        draw.rectangle(rect, outline="red", width=3)
        draw.text((x + 5, y + 5), str(i + 1), fill="yellow", font=font)

    image.save(filename)
    logging.info(f"✅ CAPTCHA overlay saved to {filename}")

async def click_aws_captcha_boxes_adjusted(page, box_string: str, selector="#captcha-container", rows=3, cols=3, top_margin=70, bottom_margin=80):
    box_nums = [int(b.strip()) - 1 for b in box_string.split(",") if b.strip().isdigit()]

    container = page.locator(selector)
    box = await container.bounding_box()
    if not box:
        logging.info("❌ CAPTCHA container not visible")
        return

    #box, (top_margin, bottom_margin) = await scale_css_box( page, box, top_margin, bottom_margin)


    # Adjust height to ignore top & bottom margin text
    usable_height = box['height'] - top_margin - bottom_margin
    cell_width = box['width'] / cols
    cell_height = usable_height / rows

    for index in box_nums:
        row = index // cols
        col = index % cols

        x = box['x'] + col * cell_width + cell_width / 2
        y = box['y'] + top_margin + row * cell_height + cell_height / 2

        logging.info(f"🖱️ Clicking box {index + 1} at ({x:.1f}, {y:.1f})")
        await page.mouse.click(x, y)


async def draw_confirm_click_overlay(
    page,
    selector="#captcha-container",
    rows=3,
    cols=3,
    top_margin=60,
    bottom_margin=40,
    confirm_offset_y=20,
    filename="captcha_bullseye.png"
):
    locator = page.locator(selector)
    box = await locator.bounding_box()
    if not box:
        logging.info("❌ CAPTCHA container not visible")
        return

    box, (top_margin, bottom_margin, confirm_offset_y) = await scale_css_box( page, box, top_margin, bottom_margin, confirm_offset_y)


    screenshot_bytes = await page.screenshot(full_page=True)
    image = Image.open(io.BytesIO(screenshot_bytes))
    draw = ImageDraw.Draw(image)

    # Calculate cell size
    usable_height = box['height'] - top_margin - bottom_margin
    cell_width = box['width'] / cols
    cell_height = usable_height / rows

    # Coordinates: directly below box 9 (bottom-right cell)
    x = box['x'] + (cols - 0.5) * cell_width
    y = box['y'] + top_margin + cell_height * rows + confirm_offset_y

    # Draw crosshair (bullseye)
    radius = 10
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline="red",
        width=3
    )
    draw.line((x - radius, y, x + radius, y), fill="red", width=2)
    draw.line((x, y - radius, x, y + radius), fill="red", width=2)

    image.save(filename)
    logging.info(f"🎯 Click (Confirm button) overlay saved to {filename}")


async def click_captcha_confirm_under_box_9(
    page,
    selector="#captcha-container",
    rows=3,
    cols=3,
    top_margin=70,
    bottom_margin=80,
    confirm_offset_y=30
):
    container = page.locator(selector)
    box = await container.bounding_box()
    if not box:
        logging.info("❌ CAPTCHA container not found")
        return

    # 🔧 Scale to device pixel space
    #box, (top_margin, bottom_margin, confirm_offset_y) = await scale_css_box( page, box, top_margin, bottom_margin, confirm_offset_y)


    # Calculate cell size
    cell_width = box['width'] / cols
    usable_height = box['height'] - top_margin - bottom_margin
    cell_height = usable_height / rows

    # X aligned with box 9 (last column), Y just below last row
    x = box['x'] + (cols - 0.5) * cell_width
    y = box['y'] + top_margin + (cell_height * rows) + confirm_offset_y

    logging.info(f"Clicking Capture Confirm button at ({x:.1f}, {y:.1f})")
    await page.mouse.click(x, y)


async def verify_captcha(page):
    await click_captcha_confirm_under_box_9(page, top_margin = TOP_MARGIN, bottom_margin= BOTTOM_MARGIN)


async def farm_capture(page, answer_event):
    await page.wait_for_function("document.querySelector('#captchaForm') !== null", timeout=50000)
    attempt = 0

    logging.info("🚨 CAPTCHA detected! Farming out question")
    await asyncio.sleep(5)

    if (CAPTURE_DEBUG):
        # Debug - Form an Image with grids to make sure that our mouse clicks
        # are over the correct area
        await save_captcha_grid_overlay(page, top_margin=TOP_MARGIN, bottom_margin=BOTTOM_MARGIN)

        # Debug - Draw a Bulls Eye Cross Hair to make sure that we
        # clicking over the confirm area
        await draw_confirm_click_overlay(
            page,
            top_margin=TOP_MARGIN,
            bottom_margin=BOTTOM_MARGIN,
            confirm_offset_y=30  # adjust this until bullseye lands on "Confirm"
        )

    question_b64, cells_b64, = await capture_captcha_quiz_as_base64(page)

    #await farm_capture_challenge_over_mqtt(question_b64, cells_b64)
    await farm_capture_challenge_over_http(question_b64, cells_b64, answer_event)

    #box_string = "" input("Enter comma-separated box numbers to select (e.g. 2,5,9): ")
    answer_string="1,2,3"
    while True:
        try:
            logging.info("farm_capture: Waiting for ANSWER")
            await answer_event.wait(timeout=180.0) # Wait for the event with a timeout of 180 seconds
            answer_string, taskId = answer_event.get()
            logging.info(f"farm_capture: We got something from our event {answer_string} taskId: {taskId}")
            answer_event.clear()
            await click_aws_captcha_boxes_adjusted(page, answer_string)


            await page.screenshot(path=f"captcha_{attempt}.png", full_page=True)
            await verify_captcha(page)
            await asyncio.sleep(3)
            await page.screenshot(path=f"attempt_{attempt}.png", full_page=True)
            # Look at this page - Are we still on Captcha?
            # - if so we have probably failed - raise an Exception
            element = await page.query_selector('#captchaForm')
            if element:
                logging.info(f"We still have the captchaForm on this page - so report it and then raise an exception - forcing a rerun - taskId {taskId}")

                await report_incorrect(taskId)      # Only supported for http.

                raise Exception(f"Failed in our captcha challenge TaskId {taskId}- our helper failed! Complain!")
            break 
        except asyncio.TimeoutError:
            logging.info("farm_capture: Timeout occurred while waiting for the answer event.")
            raise Exception("Failed in our captcha challenge - no one helped us! Complain!")
            break

# ----------------------------------- End of AWS Captcha handling -----------------------------------


def ping_factory(referrer, hostname, ping_event_wrapper):
    logging.info(f"Ping Factory referrer: {referrer} host:{hostname} {ping_event_wrapper}")
    start_time = int(time.time())
    async def update_ping():
        while True:
            try:
                await ping_event_wrapper.wait(timeout=60*5)
                logging.info(f"update_ping: Something changed. Publishing ping with value : {ping_event_wrapper.get()}")
                current_epoch = int(time.time())
                retry_delay = 1  # Initial retry delay
                while True:
                    try:
                        async with AsyncMQTTClient(
                            hostname=configure.MQTT_BROKER,
                            port=configure.MQTT_PORT,
                            username=configure.MQTT_USERNAME,
                            password=configure.MQTT_SECRET
                        ) as client:
                            logging.info(f"publish ping - referrer: {referrer}, host: {hostname}, {ping_event_wrapper}")
                            message = {
                                "version": configure.VERSION,
                                "utc_time": start_time,
                                "time_passed": current_epoch - start_time,
                                "timestamp": current_epoch,  # current epoch time
                                "hostname": hostname,
                                "referrer": referrer,
                                "status": "ok",
                                "ping_event": str(ping_event_wrapper.get())
                            }

                            # Convert to JSON string
                            json_message = json.dumps(message)
                            
                            await client.publish(f'webbot/status/{hostname}', json_message, retain=False, qos=1)
                        break  # Exit retry loop on success
                    except MqttError as e:
                        logging.warning(f"MQTT connection failed: {e}. Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s

                ping_event_wrapper.clear()

            except asyncio.TimeoutError:
                logging.info("update_ping: ping_event_wrapper wait timeout expired!")
            except Exception as e:
                logging.error(f"update_ping: {e}", exc_info=True)  # Log full traceback

    return update_ping


def generate_random_uid(length=21):
    characters = string.ascii_letters + string.digits
    result = ''.join(random.choice(characters) for _ in range(length))
    return result


def generate_uid():
    result = generate_random_uid(11) + "-" + generate_random_uid(9)
    return result

async def postjson(page, url, json, headers, retries = 3):

    """
    Makes a POST request with JSON data, using cookies from the Playwright context.

    Args:
        page: Playwright page instance.
        url: The URL to post to.
        json: The JSON payload to send.
        headers: The headers to include in the request.
        retries: Number of retries for transient errors (default is 3).

    Returns:
        The HTTPX response object.

    Raises:
        ValueError: If inputs are invalid.
        HTTPStatusError: If the response status indicates an error.
    """

    # Validate inputs
    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        raise ValueError("Invalid URL provided.")
    if not isinstance(json, dict):
        raise ValueError("The JSON payload must be a dictionary.")
    if not isinstance(headers, dict):
        raise ValueError("Headers must be a dictionary.")

    # Retrieve cookies from Playwright
    cookies = await page.context.cookies()
    httpx_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

    # Configure the HTTPX client and handle errors
    for attempt in range(retries):
        try:
            logging.info(f"HTTPX Attempt {attempt}")
            async with httpx.AsyncClient(cookies=httpx_cookies, timeout=httpx.Timeout(configure.HTTPX_TIMEOUT)) as client:
                response = await client.post(url, json=json, headers=headers)

                # Raise an exception for HTTP errors (e.g., 4xx, 5xx)
                response.raise_for_status()
                return response

        except (HTTPStatusError, RequestError, TimeoutException) as e:
            # Log and retry for transient issues
            logging.info(f"Attempt {attempt + 1} failed: {type(e).__name__}")
            if attempt == retries - 1:
                raise  # Reraise the exception after max retries


async def grab_opportunity_using_graphql(page, opportunity_id, opp_type):
    #print(f"grab_opportunity {opportunity_id} : {opp_type}")
    url = f"https://atoz-api-us-east-1.amazon.work/graphql?employeeId={configure.ATOZ_EMPLOYEE_ID}"
    #url = f"https://httpbin.org/delay/5"
    #url = f"https://httpbin.org/post"

    query_grab_vet = """mutation ClaimOpportunity($shiftOpportunityId: AddShiftInput!)
                { addShift(input: $shiftOpportunityId)
            }"""

    query_grab_vto = """mutation ClaimOpportunity($shiftOpportunityId: DropShiftInput!)
                { dropShift(input: $shiftOpportunityId)
            }"""

    query = query_grab_vto if 'TIME_OFF' in opp_type  else query_grab_vet

    json = {
        "operationName": 'ClaimOpportunity',
        "variables": {
                "shiftOpportunityId": { "shiftOpportunityId": f"{opportunity_id}" }
                },
        "query" : query
        }

    headers={
        'X-Atoz-Client-Id': 'SCHEDULE_MANAGEMENT_SERVICE',
        'X-Atoz-Client-Request-Id': generate_uid(),
        'Content-Type': 'application/json',
        'User-Agent':configure.USER_AGENT,
    }

    response = await postjson(page, url, json = json, headers = headers)

    return (opportunity_id, response.status_code, response.json())

async def get_opportunities_using_graphql_combined(page, include_ineligible=True):
#async def get_opportunities_combined(page, include_ineligible=True):
    """
    Fetch both:
      1) shift opportunities (VTO/VET offers, including ineligible and certain unavailable reasons)
      2) scheduled shifts (including accepted VTO time ranges)
    """
    graphql_url = f"https://atoz-api-us-east-1.amazon.work/graphql?employeeId={configure.ATOZ_EMPLOYEE_ID}"

    query = """
    query CombinedShiftData(
      $timeRange: DateTimeRangeInput!
      $opportunityTypes: TypeFilter!
      $filter: ShiftOpportunitiesFilter
    ) {
      # 1) Opportunities
      shiftOpportunities(timeRange: $timeRange, filter: $filter) {
        opportunities(opportunityTypes: $opportunityTypes) {
          id
          type
          skill
          addDeadline
          eligibility { isEligible unclaimableReasonCodes }
          unavailability { reasons }
          shift {
            timeRange { start end }
            site { name region }
          }
        }
      }

      # 2) Schedule (requires timeRange)
      schedule(timeRange: $timeRange) {
        scheduleShifts {
          shift {
            timeRange { start end }
            site { name }
          }
          acceptedVtoTimeRanges { start end }
        }
      }
    }
    """

    today = date.today() - timedelta(days=max(0, configure.START_DATE_OFFSET))
    future = date.today() + timedelta(days=configure.END_DATE_OFFSET)
    start_str = today.strftime("%Y-%m-%d")
    end_str = future.strftime("%Y-%m-%d")

    headers = {
        "X-Atoz-Client-Id": "SCHEDULE_MANAGEMENT_SERVICE",
        "X-Atoz-Client-Request-Id": generate_uid(),
        "User-Agent": configure.USER_AGENT,
    }

    json_body = {
        "operationName": "CombinedShiftData",
        "variables": {
            "timeRange": {
                "start": f"{start_str}T10:00:00.000Z",
                "end": f"{end_str}T10:00:00.000Z",
            },
            "filter": {
                "includeIneligible": include_ineligible,
                "unavailableReasonsToInclude": [
                    "AssociateAccepted",
                    "ShiftOpportunityCapacityMet"
                ]
            },
            "opportunityTypes": {
                "types": ["VOLUNTARY_TIME_OFF", "VOLUNTARY_EXTRA_TIME"]
            },
        },
        "query": query,
    }

    try:
        resp = await postjson(page, graphql_url, json=json_body, headers=headers)
        data = resp.json()
        if "errors" in data:
            logging.error("❌ GraphQL errors: %s", data["errors"])
        else:
            logging.info("✅ Combined schedule + opportunities query succeeded")
        return data
    except Exception as e:
        logging.exception("❌ GraphQL combined query failed: %s", e)
        return None


async def get_opportunities_using_graphql_LATEST(page, include_ineligible=True):
    """
    Fetch both:
      1) shift opportunities (VTO/VET offers)
      2) scheduled shifts (including accepted VTO time ranges)
    """
    graphql_url = f"https://atoz-api-us-east-1.amazon.work/graphql?employeeId={configure.ATOZ_EMPLOYEE_ID}"

    query = """
    query CombinedShiftData(
      $timeRange: DateTimeRangeInput!
      $opportunityTypes: TypeFilter!
      $filter: ShiftOpportunitiesFilter
    ) {
      # 1) Opportunities
      shiftOpportunities(timeRange: $timeRange, filter: $filter) {
        opportunities(opportunityTypes: $opportunityTypes) {
          id
          type
          addDeadline
          eligibility { isEligible unclaimableReasonCodes }
          unavailability { reasons }
          shift {
            timeRange { start end }
            site { name region }
          }
        }
      }

      # 2) Schedule (requires timeRange)
      schedule(timeRange: $timeRange) {
        scheduleShifts {
          shift {
            timeRange { start end }
            site { name }
          }
          acceptedVtoTimeRanges { start end }
        }
      }
    }
    """

    # date window
    today = date.today() - timedelta(days=configure.START_DATE_OFFSET)
    future = date.today() + timedelta(days=configure.END_DATE_OFFSET)
    start_str = today.strftime("%Y-%m-%d")
    end_str = future.strftime("%Y-%m-%d")
    logging.info(f"📡 Fetching schedule+opportunities between {start_str} and {end_str}")

    headers = {
        "X-Atoz-Client-Id": "SCHEDULE_MANAGEMENT_SERVICE",
        "X-Atoz-Client-Request-Id": generate_uid(),
        "User-Agent": configure.USER_AGENT,
    }

    json_body = {
        "operationName": "CombinedShiftData",
        "variables": {
            "timeRange": {
                "start": f"{start_str}T10:00:00.000Z",
                "end": f"{end_str}T10:00:00.000Z",
            },
            "filter": {
                "includeIneligible": include_ineligible
            },
            "opportunityTypes": {
                "types": ["VOLUNTARY_TIME_OFF", "VOLUNTARY_EXTRA_TIME"]
            },
        },
        "query": query,
    }

    try:
        resp = await postjson(page, graphql_url, json=json_body, headers=headers)
        data = resp.json()
        if "errors" in data:
            logging.error("❌ GraphQL errors: %s", data["errors"])
        else:
            logging.info("✅ Combined schedule + opportunities query succeeded")
        return data
    except Exception as e:
        logging.exception("❌ GraphQL combined query failed: %s", e)
        return None
    
async def get_opportunities_using_graphql_DEP(page, include_ineligible=True):

    logging.info(f"get_opportunities_using_graphql INCLUDE_INELIGIBLE {include_ineligible}")

    graphql_url = f"https://atoz-api-us-east-1.amazon.work/graphql?employeeId={configure.ATOZ_EMPLOYEE_ID}"
    #graphql_url = f"https://httpbin.org/delay/5"

    query = """query OppsPage($timeRange: DateTimeRangeInput!, $opportunityTypes: TypeFilter!, $filter: ShiftOpportunitiesFilter) {
  shiftOpportunities(timeRange: $timeRange, filter: $filter) {
    opportunities(opportunityTypes: $opportunityTypes) {
      ...OppCard_shiftOpportunity
      __typename
    }
    __typename
  }
}
fragment OppCard_shiftOpportunity on ShiftOpportunity {
  id
  type
  skill
  eligibility {
    isEligible
    unclaimableReasonCodes
    __typename
  }
  unavailability {
    reasons
    __typename
  }
  shift {
    timeRange {
      start
      end
      __typename
    }
    __typename
  }
  __typename
}
    """

    today = date.today() - timedelta(days=max(0,configure.START_DATE_OFFSET))
    todays_date = today.strftime("%Y-%m-%d")
    future_date = date.today() + timedelta(days=configure.END_DATE_OFFSET)
    next_month = future_date.strftime("%Y-%m-%d")
    logging.info(f"Retrieving opportunities between {todays_date} and {next_month} include_ineligible: {include_ineligible}")


    headers={
                'X-Atoz-Client-Id': 'SCHEDULE_MANAGEMENT_SERVICE',
                'X-Atoz-Client-Request-Id': generate_uid(),
                'User-Agent':configure.USER_AGENT,
    }

    json_body = {
        "operationName":"OppsPage",
        'variables': {
            'timeRange': {
                'start':f'{todays_date}T10:00:00.000Z',
                'end':f'{next_month}T10:00:00.000Z'
            },
            'filter': {
                    'includeIneligible': include_ineligible,
                        "unavailableReasonsToInclude": [
                                                    "AssociateAccepted",
                                                    "ShiftOpportunityCapacityMet"
                        ]
                    
            },
            "opportunityTypes": {
                    # VOLUNTARY_TIME_OFF, VOLUNTARY_EXTRA_TIME
                    "types": [
                                "VOLUNTARY_TIME_OFF",
                                "VOLUNTARY_EXTRA_TIME",

                                ]
            }
        },
        'query':query

        }

    response = await postjson(page, graphql_url, json=json_body, headers=headers)

    
    return response.json()





async def get_opportunities_using_api(page):
    # Call the web service and fetch the JSON response
    json_response = await page.evaluate("""
        async () => {
            const response = await fetch('https://atoz.amazon.work/api/v1/opportunities/get_opportunities?employee_id=111283278', {
                method: 'GET',
                headers: {
                    'Dnt': '1', // Add headers if needed
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return await response.json(); // Return the JSON response
        }
    """)

    #print("JSON Response:", json_response)
    return json_response



async def preflight_check(page, url):
        response = await page.evaluate(f'''async () => {{
            const res = await fetch('{url}', {{
                method: 'OPTIONS',
                headers: {{
                    'Content-Type': 'application/json',
                }}
            }});
            return {{
                status: res.status,
                headers: Object.fromEntries(res.headers.entries())
            }};
        }}''')
        return response

async def test_preflght(url="https://atoz-api-us-east-1.amazon.work/graphql"):

    # Simulate the preflight request

    headers = {
        "Origin": "https://atoz.amazon.work",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type, x-atoz-client-id",
    }

    async with httpx.AsyncClient() as client:
        response = await client.options(url, headers=headers)

    logging.info(f"test_preflght: url: {url} headers:{headers}")
    logging.info(f"test_preflght: Response Status Code: {response.status_code}")
    logging.info(f"test_preflght: Response Headers: {response.headers}")

async def preflight_checks(page):
    await test_preflght()
    # Preflight check
    flight_check = await preflight_check(page,'https://atoz-api-us-east-1.amazon.work/graphql?employeeId=111283278')
    logging.info(f"preflight_checks: {flight_check}")


async def stealth_delay(stealth_delay_wrapper, chunk_size=0.25):
    logging.info(f"stealth_delay: START. MAX DELAY={stealth_delay_wrapper}s, CHUNK SIZE={chunk_size}s")
    elapsed_time = 0
    
    while elapsed_time < stealth_delay_wrapper.value:
        remaining_time = max(0, stealth_delay_wrapper.value - elapsed_time)
        sleep_time = min(chunk_size, remaining_time)
        #logging.info(f"stealth_delay: Sleeping for {sleep_time:.2f}s (elapsed {elapsed_time:.2f}s)")
        await asyncio.sleep(sleep_time)
        
        elapsed_time += sleep_time

    logging.info("stealth_delay: DONE.")


async def smash_and_grab_using_graphql(page, requirements_manager, stealth_delayer):
    logging.info(f"smash_and_grab_using_graphql : STEALTH_DELAYER = {stealth_delayer}")


    #opportunities_response=await get_opportunities_using_graphql_DEP(page)
    opportunities_response=await get_opportunities_using_graphql_combined(page)
    #opportunities_response=await get_opportunities_using_graphql_LATEST(page)
    opportunities = opportunities_response['data']['shiftOpportunities']['opportunities']
    all_ops=sorted([
        Opportunity({
        'date': str(fromisoformat(_['shift']['timeRange']['start']).date()),
        'id':_['id'],
        'utc':int(fromisoformat(_['shift']['timeRange']['start']).timestamp()),
        'start': str(fromisoformat(_['shift']['timeRange']['start']).time()),
        'end': str(fromisoformat(_['shift']['timeRange']['end']).time()),
        'duration':int((fromisoformat(_['shift']['timeRange']['end']) - fromisoformat(_['shift']['timeRange']['start'])).total_seconds()//60),
        'due_to_start':int((fromisoformat(_['shift']['timeRange']['start']) - datetime.now(timezone.utc)).total_seconds()//60),
        'type':_['type'],
        'skill':_['skill'] if 'skill' in _ else '',
        'eligibility': _['eligibility']['isEligible'],
        'eligibility_reasons': ','.join(sorted(_['eligibility']['unclaimableReasonCodes'])),
        'availability_reasons':','.join(sorted(_['unavailability']['reasons'])) if _['unavailability'] and 'reasons'in _['unavailability'] else 'None'
        })
        for _ in opportunities
    ], key=lambda _: (-_.duration))

    vtos = list(filter(lambda _ :  'TIME_OFF' in _.type, all_ops))
    vets = list(filter(lambda _ :  'VOLUNTARY_EXTRA_TIME' in _.type, all_ops))

    sorted_vto = sorted(vtos, key = lambda i: i.utc)
    sorted_vet = sorted(vets, key = lambda i: i.utc)

    active_vet = list(filter(lambda _ :  _.eligibility, sorted_vet))
    active_vto = list(filter(lambda _ :  _.eligibility, sorted_vto))
    active_opps = list(filter(lambda _ :  _.eligibility, all_ops))
    inactive_vto = list(filter(lambda _ :  not _.eligibility, sorted_vto))

    logging.info(f"Active VTOs {len(active_vto)}, Total {len(vtos)}. Active VETs {len(active_vet)}, Total {len(vets)}")
    logging.info(f"Active OPS {len(active_opps)}")
    
    matched_opportunities = requirements_manager.extract_matched_opportunties(active_opps)
    #matched_opportunities = [(opportunity.id, opportunity.type) for opportunity in inactive_vto] 

    logging.info(f"Matched opportunities (VTOs and VETs) {matched_opportunities} size: {len(matched_opportunities)}")



    logging.info(f"Grabbing. Mock:{configure.Mock} Limited: {configure.Limited}")

    if (len(matched_opportunities)>0):
        await stealth_delayer.wait()
        
        if configure.Limited:
            matched_opportunities  = [matched_opportunities[0]] # ONE AT A TIME!

        if not configure.Mock:
            tasks = [ asyncio.create_task(grab_opportunity_using_graphql(page, *opportunity_pair )) for opportunity_pair in matched_opportunities]
            task_results = await asyncio.gather(*tasks)
            logging.info(f"grab_opportunity_using_graphql: Task Results  {task_results}")
            file_logger.info(f"grab_opportunity_using_graphql: results = {task_results}")
        else:
            logging.info(f"Mock grab_opportunity_using_graphql: Opportunities Matched  {matched_opportunities}")
            file_logger.info(f"Mock grab_opportunity_using_graphql: Opportunties Matched = {matched_opportunities}")
                        
    stealth_delayer.reset_if_set()
    return matched_opportunities

async def handle_sleep_with_interrupt(opportunity_event, sleep_time):
    logging.info(f"handle_sleep_with_interrupt: Sleeping... {sleep_time} seconds")
    try:
        await opportunity_event.wait(timeout=sleep_time)
        logging.info(f"Wake-up message received! {opportunity_event.get()}")
        opportunity_event.clear()
        # Handle wake-up logic here
    except asyncio.TimeoutError:
        logging.info("Sleep timeout expired!")


async def pause_for_thought(opportunity_event, n_minute = 5):
    #current_time_gmt = datetime.now(timezone.utc)
    now = datetime.now()
    # Calculate the next time aligned to the 'n'-minute interval
    next_minute = (now + timedelta(minutes=n_minute))
    next_execution = next_minute.replace(
        minute=(next_minute.minute // n_minute) * n_minute, second=0, microsecond=0
    )
        
    if next_execution <= now:
        # If the calculated time is in the past, move to the next interval
        next_execution += timedelta(minutes=n_minute)
        
    # Calculate how long to sleep until the next execution
    sleep_time = (next_execution - now).total_seconds()

    logging.info(f"Wait for {sleep_time} seconds or if we get an opportunity text/email message")        

    # Sleep until the next minute or we get an opportunity_event
    await handle_sleep_with_interrupt(opportunity_event, sleep_time)


from playwright.async_api import expect
#import asyncio
from playwright.async_api import Page


async def mimic_human_fill_form(page, form_el, str_input):
    await asyncio.sleep(random.uniform(0.3, 0.6))  # Let React attach listeners
    # Wait until readonly attribute disappears (React removes it dynamically)
    element_handle = await form_el.element_handle()
    if element_handle:
        await element_handle.wait_for_element_state("editable", timeout=5000)

    # Re-focus after editable (some React components re-render the input)
    await form_el.click(force=True)

    # Type the username like a user, key by key
    await page.keyboard.type(str_input, delay=random.uniform(50, 100))


async def form_input(page, form_el, str_input):

    await form_el.wait_for(state="visible", timeout=30000)
    await form_el.click(force=True)
    #await mimic_human_fill_form(page, form_el, str_input)
    await form_el.fill(str_input)



async def handle_idprism_form(page):
    logging.info(f"handle_idprism_form() - username: {configure.ATOZ_USERNAME}")

    while True:
        try:
            url = page.url
            logging.debug(f"[idprism] Current URL: {url}")

            if "idprism-auth.amazon.com" in url:
                logging.info(f"Detected IdPrism page: {url}") 

                # → Step 1
                logging.info("→ Step 1: Waiting for DOMContentLoaded...")
                await page.wait_for_load_state("domcontentloaded")
                logging.info("✓ Step 1 complete: DOMContentLoaded reached.")

                # → Step 2
                logging.info("→ Step 2: Checking for 'Sorry' message...")
                try:
                    error_locator = page.locator("text=/sorry, something went wrong/i")
                    if await error_locator.count() > 0:
                        logging.warning("⚠️ 'Sorry' message detected — reloading IdPrism page...")
                        await page.reload()
                        await page.wait_for_load_state("domcontentloaded")
                        logging.info("✓ Reloaded after 'Sorry' message.")
                        continue
                    else:
                        logging.info("✓ Step 2 complete: No 'Sorry' message detected.")

                except Exception:
                    logging.info("✓ Step 2 complete: No 'Sorry' message detected.")

                # → Step 3
                logging.info("→ Step 3: Checking for username input...")
                username_input = page.locator("[data-testid='username-input']")
                username_count = await username_input.count()
                logging.info(f"✓ Step 3 complete: Found {username_count} username input(s).")

                if username_count == 0:
                    logging.info("IdPrism page without username input — probably redirect. Waiting…")
                    await asyncio.sleep(2)
                    continue

                # → Step 4
                logging.info("→ Step 4: Waiting for username input to become visible...")
                try:
                    logging.info("✓ Step 4 complete: Username input visible.")
                    logging.info("→ Step 5: Clicking username input...")
                    await form_input(page, username_input, configure.ATOZ_USERNAME)
                    logging.info("✓ Filled username input.")
                except Exception as e:
                    logging.exception("❌ Step 4 error: username input interaction failed. Reloading page.")
                    await page.reload()
                    await page.wait_for_load_state("domcontentloaded")
                    continue

                # → Step 6
                logging.info("→ Step 6: Waiting for submit button...")
                submit_btn = page.locator("[data-testid='submit-username-button']")
                try:
                    await submit_btn.wait_for(state="visible", timeout=10000)
                    await expect(submit_btn).to_be_enabled(timeout=10000)
                    logging.info("✓ Step 6 complete: Submit button visible and enabled.")
                    logging.info("→ Step 7: Clicking submit button...")
                    # Hover (to simulate cursor over button)

                    await submit_btn.click()
                    logging.info("✓ Step 7 complete: Submit clicked.")
                    await asyncio.sleep(random.uniform(0.2, 0.5))

                except Exception as e:
                    logging.exception("❌ Step 6 error: submit button interaction failed. Reloading page.")
                    await page.reload()
                    await page.wait_for_load_state("domcontentloaded")
                    continue

                # → Step 8
                logging.info("→ Step 8: Waiting for redirect away from IdPrism page...")
                for i in range(60):  # up to 60 seconds
                    current_url = page.url
                    if "idprism-auth.amazon.com" not in current_url:
                        logging.info(f"✓ Step 8 complete: Redirected away from IdPrism to {current_url}")
                        break
                    logging.debug(f"⏳ Waiting for redirect ({i + 1}/60): still on {current_url}")
                    await asyncio.sleep(1)
                else:
                    logging.warning("⚠️ Step 8: Still on IdPrism page after 60s.")
                    await page.reload()

            else:
                # Not on IdPrism domain — idle and recheck soon
                logging.debug(f"[idprism] Not on IdPrism page ({url}) — waiting 2s.")
                await asyncio.sleep(2)

        except Exception as e:
            if "NS_BINDING_ABORTED" in str(e):
                logging.warning("⚠️ Navigation aborted (NS_BINDING_ABORTED) — continuing.")
            else:
                logging.exception("❌ handle_idprism_form: Unhandled exception.")
            await asyncio.sleep(2)


async def wait_for_employee_id_in_content(page, timeout=180000):
    deadline = asyncio.get_event_loop().time() + timeout / 1000
    while True:
        try:
            html = await page.content()
            if '"employeeId"' in html:
                return True
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError("employeeId not found in page")
            await asyncio.sleep(0.5)
        except PlaywrightTimeoutError as toe:
            pass
        except Exception as e:
            print(f"wait_for_employee_id_in_content: Other Error {e}")


def map_opportunities_to_schedule(data):
    opportunities = data["data"]["shiftOpportunities"]["opportunities"]
    schedule = data["data"]["schedule"]["scheduleShifts"]

    results = []

    for opp in opportunities:
        opp_start = parser.isoparse(opp["shift"]["timeRange"]["start"])
        opp_end = parser.isoparse(opp["shift"]["timeRange"]["end"])
        matched_shift = None

        for shift in schedule:
            sched_start = parser.isoparse(shift["shift"]["timeRange"]["start"])
            sched_end = parser.isoparse(shift["shift"]["timeRange"]["end"])

            # ✅ Basic overlap check
            if opp_start < sched_end and opp_end > sched_start:
                matched_shift = shift
                break

        results.append({
            "opportunity_id": opp["id"],
            "opportunity_start": opp_start,
            "opportunity_end": opp_end,
            "matched_schedule": matched_shift is not None,
            "schedule_time_range": (
                (sched_start, sched_end) if matched_shift else None
            ),
            "unclaimable_reasons": opp["eligibility"]["unclaimableReasonCodes"]
        })

    return results



def report_opportunity_status(data):
    """
    Analyse the GraphQL response from get_schedule_and_opportunities()
    and print a human-readable report of each opportunity.
    """

    opps = data["data"]["shiftOpportunities"]["opportunities"]
    shifts = data["data"]["schedule"]["scheduleShifts"]

    if not opps:
        print("⚠️ No opportunities found.")
        return

    print("📊 Opportunity Analysis Report")
    print("=" * 60)

    for opp in opps:
        opp_id = opp["id"]
        opp_type = opp.get("type", "UNKNOWN")
        add_deadline = parser.isoparse(opp["addDeadline"]) if opp.get("addDeadline") else None
        opp_start = parser.isoparse(opp["shift"]["timeRange"]["start"])
        opp_end = parser.isoparse(opp["shift"]["timeRange"]["end"])
        site_name = opp["shift"]["site"].get("name", "?")
        eligibility = opp["eligibility"]["isEligible"]
        reason_codes = opp["eligibility"].get("unclaimableReasonCodes", [])
        unavailability = (opp.get("unavailability") or {}).get("reasons", [])

        # Check if this opportunity overlaps a scheduled shift
        matched_shift = None
        for shift in shifts:
            sched_start = parser.isoparse(shift["shift"]["timeRange"]["start"])
            sched_end = parser.isoparse(shift["shift"]["timeRange"]["end"])

            if opp_start < sched_end and opp_end > sched_start:
                matched_shift = shift
                break

        # Build human-readable status
        if eligibility:
            status = "✅ Still claimable"
        else:
            if "ShiftOpportunityExpired" in unavailability:
                status = "⏱️ Expired before you could claim"
            else:
                status = "❌ Not eligible"

        if matched_shift:
            shift_start = parser.isoparse(matched_shift["shift"]["timeRange"]["start"])
            shift_end = parser.isoparse(matched_shift["shift"]["timeRange"]["end"])
            overlap_msg = f"🕐 Overlaps scheduled shift on {shift_start.date()} ({shift_start.time()}–{shift_end.time()})"
        else:
            overlap_msg = "📅 No scheduled shift overlap"

        # Print the report block
        print(f"ID: {opp_id}")
        print(f"Type: {opp_type}")
        print(f"Site: {site_name}")
        print(f"Shift Time: {opp_start} → {opp_end}")
        if add_deadline:
            print(f"Add Deadline: {add_deadline}")
        print(f"Eligibility: {eligibility}")
        print(f"Reason Codes: {reason_codes}")
        print(f"Unavailability: {unavailability}")
        print(f"Status: {status}")
        print(f"{overlap_msg}")
        print("-" * 60)


async def get_opportunities_with_api(page):
    opps_url = f'https://atoz.amazon.work/api/v1/opportunities/get_opportunities?employee_id={configure.ATOZ_EMPLOYEE_ID}'
    
    response = await page.request.get(
        opps_url,
        headers={
            'Dnt': '1',
            'User-Agent': configure.USER_AGENT,
            'Referer': 'https://atoz.amazon.work/time/extra'
        }
    )
    
    # Optionally, get JSON data directly
    data = await response.json()
    return data


def update_opportunities_factory(page, last_hash, use_graphql =  False):


    logging.info(f"update_opportunities_factory: USE_GRAPHQL: {use_graphql}")

    async def publishResponse(sorted_vto, sorted_vet):
        #print(sorted_vto)
        num_VETs = len(sorted_vet)
        num_VTOs = len(sorted_vto)

        if ((num_VETs + num_VTOs) == 0 and not use_graphql):
            logging.info('Zero Sized Opportunities on Restful API - (usually associated with server error) - so skipping Checks')
            #logging.info(jResp)
            return
        logging.info(f"numVETS {num_VETs}, numVTOs {num_VTOs}")
        all_ops = {'vtoOpportunities':sorted_vto, 'vetOpportunities': sorted_vet}

        active_vet = list(filter(lambda _ :  _['active'], sorted_vet))
        active_vto = list(filter(lambda _ :  _['active'], sorted_vto))

        num_active_VETs = len(active_vet) 
        num_active_VTOs = len(active_vto) 

        accepted_vto = list(filter(lambda _ : _['inactive_reason'] == 'ALREADY_ACCEPTED', sorted_vto))
        accepted_vet = list(filter(lambda _ : _['inactive_reason'] == 'ALREADY_ACCEPTED', sorted_vet))
        barred_vtos = list(filter(lambda _ : _['inactive_reason'] == 'Removed associate due to specified override.', sorted_vto))

        opportunities_hash = hashlib.md5(str(all_ops).encode()).hexdigest()
        if (opportunities_hash != last_hash.hash):
            logging.info("Updating Opportunities over MQTT")
            last_hash.hash = opportunities_hash
            #employee_id = configure.ATOZ_EMPLOYEE_ID
            async with AsyncMQTTClient(hostname=configure.MQTT_BROKER, port=configure.MQTT_PORT,
                                    username=configure.MQTT_USERNAME, password=configure.MQTT_SECRET) as client:
                await client.publish(f"opportunities/api/vto", json.dumps(sorted_vto), retain=True, qos=1)
                await client.publish(f"opportunities/api/vet", json.dumps(sorted_vet), retain=True, qos=1)


        return {
                        "accepted_vtos":len(accepted_vto),
                        "vtos": num_VTOs,
                        "active_vtos":num_active_VTOs,
                        "accepted_vets":len(accepted_vet),
                        "vets":num_VETs,
                        "active_vets":num_active_VETs,
                        "barred_vtos":len(barred_vtos)
        }
    
    # Replacement function to deal with older versions of datetime library.
    def fromisoformat(iso_string):
        return datetime.fromisoformat(iso_string) if not iso_string.endswith('Z') else datetime.fromisoformat(iso_string[:-1]+'+00:00')

    async def update_opportunities_graphql_api(page):

        def buildWrapper(opps):

            sorted_vto = []
            sorted_vet = []

            if (configure.REPORT_OPPORTUNTIES):
                logging.info(f"REPORT_OPPORTUNTIES: opps: {opps}")

                report_opportunity_status(opps)

                logging.info("Scheduled Shifts")
                for shift in opps["data"]["schedule"]["scheduleShifts"]:
                    logging.info(f'Scheduled shift:, {shift["shift"]["timeRange"]}')
                    for vto in shift.get("acceptedVtoTimeRanges", []):
                        print(f'  Accepted VTO: {vto["start"]} → {vto["end"]}')


            for _ in opps['data']['shiftOpportunities']['opportunities']:
                opp_id = _['id']
                start_date_str = _['shift']['timeRange']['start']
                end_date_str =  _['shift']['timeRange']['end']
                addDeadline = _['addDeadline']

                start_date = str(fromisoformat(_['shift']['timeRange']['start']).date())
                utc=int(fromisoformat(_['shift']['timeRange']['start']).timestamp())
                opp_start = str(fromisoformat(_['shift']['timeRange']['start']).time())
                opp_end = str(fromisoformat(_['shift']['timeRange']['end']).time())
                duration=int((fromisoformat(_['shift']['timeRange']['end']) - fromisoformat(_['shift']['timeRange']['start'])).total_seconds()//60)
                due_to_start = int((fromisoformat(_['shift']['timeRange']['start']) - datetime.now(timezone.utc)).total_seconds()//60)
                opp_type= 'VET' if 'VOLUNTARY_EXTRA_TIME' in _['type'] else 'VTO'
                skill = _['skill'] if 'skill' in _ else ''
                eligibility = _['eligibility']['isEligible']
                eligibility_reasons = ','.join(sorted(_['eligibility']['unclaimableReasonCodes']))
                availability_reasons =','.join(sorted(_['unavailability']['reasons'])) if _['unavailability'] and 'reasons'in _['unavailability'] else 'None'
                availability_reasons = 'ALREADY_ACCEPTED' if 'AssociateAccepted' in  availability_reasons else availability_reasons

                #print(opp_id , opp_type, skill, eligibility, eligibility_reasons, opp_start, opp_end)
                #print(opp_type, start_date_str, opp_start, "-", opp_end, duration, eligibility, availability_reasons)
                
                jopp = {
                    "start_time":start_date_str,
                    "start_time_local":start_date_str,
                    "end_time":end_date_str,
                    "end_time_local":end_date_str,
                    "signup_start_time": addDeadline,
                    "signup_start_time_local":addDeadline,
                    "signup_end_time":"1970-01-01T00:00:00.000Z",
                    "signup_end_time_local":"1970-01-01T00:00:00.000Z",
                    "site_time_zone":None,
                    "opportunity_id":opp_id,
                    "workgroup":skill,"active":eligibility,
                    "opportunity_type":opp_type,
                    "inactive_reason":availability_reasons,
                    "minutes_to_cover_opportunity":duration,
                    "minimum_time_denomination_in_minutes":30,
                    "accrual_balances":[],
                    "accrual_supported":False,
                    "is_opportunity_incentivized":False,
                    "incentives":None,
                    "droppable":False,
                    "drop_start_time":None,
                    "drop_start_time_local":None,
                    "drop_end_time":None,
                    "drop_end_time_local":None
                }
                if ('VET' in opp_type):
                    sorted_vet.append(jopp)
                else:
                    sorted_vto.append(jopp)

            return sorted_vto, sorted_vet


        logging.info(f"update_opportunities_graphql_api: {page}")

        opps = await get_opportunities_using_graphql_combined(page)
        sorted_vto, sorted_vet = buildWrapper(opps)
        ping_response = await publishResponse(sorted_vto,sorted_vet)
        return ping_response


    async def update_opportunities_restful_api(page):
        logging.info(f"update_opportunities_restful_api: {page}")

        jResp = await get_opportunities_with_api(page)

        sorted_vto = sorted(jResp['vtoOpportunities'], key = lambda i: i['opportunity_id'])
        sorted_vet = sorted(jResp['vetOpportunities'], key = lambda i: i['opportunity_id'])
        ping_response = await publishResponse(sorted_vto,sorted_vet)
        return ping_response
        


    return update_opportunities_graphql_api if use_graphql else update_opportunities_restful_api


def ping_status_factory(time_started, hostname, ipaddress, poll_timer_wrapper):

    async def ping_status(results):

        #logging.info(f"ping status {hostname}, {ipaddress} - {results} utc {int(time_started.timestamp())}")

        running_time = (datetime.now() - time_started)

        ping_message = {
                            "hostname": f'{hostname}_restful',
                            "ipaddress": ipaddress,
                            "utc_start":int(time_started.timestamp()),
                            "employee_id":configure.ATOZ_EMPLOYEE_ID,
                            "otp_device_index" : configure.OTP_INDEX,
                            "time_passed": int(running_time.total_seconds()),
                            "device_name": configure.DEVICE_NAME,
                            "poll_time": poll_timer_wrapper.value,
                            "announcements": True,
                            "live": True,
                            "gsm_running":"mqtt"

                    }

        ping_message.update(results) #build completed message
        #logging.info(f"Pinging ... {ping_message}")

        async with AsyncMQTTClient(hostname=configure.MQTT_BROKER, port=configure.MQTT_PORT,
                                username=configure.MQTT_USERNAME, password=configure.MQTT_SECRET) as client:

              await client.publish(f'opportunities/api/status/restful_{hostname}',
              json.dumps(ping_message), retain=True, qos=1)

        #logging.info(f"PING COMPLETED----> {ping_message}")

    return ping_status

async def handle_content(main_url, context, page, opportunity_event):
    opportunities_hash = HashObject('')

    stealth_delay_wrapper = ValueWrapper(configure.STEALTH_GRAB_DELAY)    
    stealth_delayer=StealthDelayer(stealth_delay_wrapper)
    zero_delayer = StealthDelayer(ValueWrapper(0), cancel_event = stealth_delayer.cancel_event)


    time_started = datetime.now()

    #main_page_retrieve = False
    email_peeker_initiated = False

    logging.info(f"SMASH and GRAB is {'ON' if configure.ATTEMPT_GRABBING else 'OFF'}.")
    logging.info(f"REPORTING IS {'ON' if configure.UPDATE_OPPORTUNITIES else 'OFF'}.")

    logging.info(f"STEALTH GRAB DELAY  = {stealth_delayer}")

    pause_mins_wrapper = ValueWrapper(5)
    main_page_retrieve  = ValueWrapper(False)
   

    ping_event_wrapper  = EventWrapper(0) # utc
    vet_allowed_wrapper = ValueWrapper(False)
    #ping_event_wrapper.set(0)

    hostname = socket.gethostname()
    referrer = os.environ.get('referrer', 'unknown')
    update_opportunities_flag = os.environ.get("update_opportunities", "False").lower() == "true" or configure.UPDATE_OPPORTUNITIES
    logging.info(f"HOSTNAME {hostname} {ping_event_wrapper} REFERRER {referrer},  Update Opportunities {update_opportunities_flag}")
    ping_update = ping_factory(referrer, hostname, ping_event_wrapper)
    asyncio.create_task(ping_update())

    requirements_manager = RequirementsManager()
    #work_requirements = [DayRequirement('saturday, sunday, monday, tuesday, wednesday, thursday, friday', TypeRequirement('TIME_OFF'))] # One which can not be changeable
    #requirements_manager.setRequirements(work_requirements)

    logging.info(f"Starting with Requirements: {requirements_manager}")
    asyncio.create_task(watch_for_new_requirements(requirements_manager, opportunity_event))
    asyncio.create_task(watch_for_new_vet_requirements(requirements_manager, vet_allowed_wrapper, opportunity_event))
    logging.info("Look for any changes in VET flag")
    asyncio.create_task(watch_for_new_vet_flag(vet_allowed_wrapper, opportunity_event))

    logging.info("Look for any changes in stealth delay")
    asyncio.create_task(watch_for_new_stealth_delay(stealth_delayer))

    logging.info("Look for any new claims or clean claims")
    asyncio.create_task(watch_for_new_claim(requirements_manager, opportunity_event, stealth_delayer))
    asyncio.create_task(watch_for_clean_claims(requirements_manager, opportunity_event, stealth_delayer))

    asyncio.create_task(handle_idprism_form(page))
    ip_addr = '0.0.0.0'
    ping_status = ping_status_factory(time_started,hostname, ip_addr, stealth_delay_wrapper)


    while True:
        
        try:

            if (not main_page_retrieve.value):
                logging.info(f"Goto main_url {main_url}")
                await page.goto(main_url)
                #element = await page.wait_for_function("""
                #    () => document.documentElement.innerHTML.includes('"employeeId"')
                #""", timeout=180000)  # Waits up to 60 seconds

                #await page.wait_for_load_state("networkidle", timeout=60000)  # wait until idle

                await wait_for_employee_id_in_content(page)
                main_page_retrieve.value = True
                #await voice_monkey("Refreshed Page")

            #await preflight_checks(page)
            #origin = await page.evaluate('window.origin')

            if (update_opportunities_flag):
                logging.info("++++ REPORTING (over MQTT) is ON! ++++")
                update_opportunties = update_opportunities_factory(page, opportunities_hash, use_graphql = not configure.USE_RESTFUL_API)
                opportunities = await update_opportunties(page)   # Build opportunities using resetful API or GraphQL
                if (opportunities):
                    await ping_status(opportunities)

            if (configure.ATTEMPT_GRABBING):
                used_delayer = zero_delayer if requirements_manager.hasClaims() else stealth_delayer
                logging.info(f"++++ SMASH and GRAB is ON! (delay {used_delayer.delay_wrapper.value} secs)++++")
                logging.info(f"{'***WARNING WARNING WARNING *** ALLOWING VET GRABBING!' if (vet_allowed_wrapper.value != 0) else 'VET GRABBING OFF (through requirements)'} VET ALLOWED WRAPPER (Boolean int) {vet_allowed_wrapper} - ")
                matched = await smash_and_grab_using_graphql(page, requirements_manager, used_delayer)
                num_opps = len(matched)

                logging.info(f"clean up requirements_manager by removing ONE OFF CLAIMS (of type IDRequirement) that matched our last grab attempt. One off claims exist = {requirements_manager.hasClaims()}")
                logging.info(f"Before: {requirements_manager}")
                requirements_manager.removeOneOffIDClaimsThatMatch(matched)

            ping_event_wrapper.set(datetime.now(timezone.utc).timestamp())

            if (not email_peeker_initiated and configure.EMAIL_PEEKER):
                asyncio.create_task(email_peeker(opportunity_event))
                email_peeker_initiated = True

            if (num_opps == 0):
                await pause_for_thought(opportunity_event, pause_mins_wrapper.value)

        except TargetClosedError:
            print("Session Finished Due to TargetClose or InvalidState Error")
            raise TargetClosedError("JOHNNY!")
        except Exception as e:
            line_number = e.__traceback__.tb_lineno
            print(f"handle_atoz_content Exception {line_number}-------------->", e, type(e), "<---------------------------------")

        await asyncio.sleep(0.01)



def route_matcher(str):
    #print("********************************************Matching", str)
    return True

async def intercept(route, request):
    headers = request.headers.copy()

    watch_url='atoz-api-us-east-1.amazon.work'
    if (watch_url in request.url):
        logging.info(f"intercept: {request.url}")
        logging.info(f"intercept: {str(headers)}")
    #wanted=['x-amz-date', 'authorization', 'x-api-key', 'x-amz-security-token', 'cookie', 'origin', 'x-atoz-client-id', 'x-atoz-employee-id', 'x-atoz-client-request-id']


    response = await route.continue_(headers=headers)


async def handle_sms_message(message, verification_event, opportunity_event):
    import re
    try:
        msg_payload = eval(message.payload.decode('utf-8'))
        logging.info(f"payload: {msg_payload}")
        txt_message = str(msg_payload['text']).lower()
        mo_from = msg_payload['msisdn']
        to = msg_payload['to']
        verification_code = None
        vcode = re.search(r"\b"+".*fication code is ([0-9]+)", txt_message)
        if (vcode is not None):
            logging.info("SMS OTP message")
            verification_code = vcode.group(1)
            verification_event.set(verification_code)

        # Look for opportunity text message 'You have a VTO opportunity available'
        opportunity = re.search(r"\b"+".*opportunity", txt_message)
        if (opportunity is not None):
            logging.info("SMS Opportunity message")
            opportunity_event.set(txt_message)
        
        logging.info(f"SMS message received {txt_message}")

    except Exception as e:
        logging.warning(f"Topic: {message.topic}. Not a valid JSON message.{e}")


async def handle_wakeup_message(message, opportunity_event):
    try:
        decoded_message = message.payload.decode('utf-8')
        msg_payload = eval(decoded_message)
        logging.info(f"handle_wakeup_message: payload: {msg_payload}")
        opportunity_event.set(msg_payload)
    except Exception as e:
        logging.warning(f"handle_wakeup_message: Topic: {message.topic} {e}")
        opportunity_event.set(f"{message.topic} {str(decoded_message)}")

 
async def receive_sms(verification_event, opportunity_event):
    sms_topic = f"mqttsmsgw/#"
    logging.info(f"MQTT receive_sms() topic {sms_topic}")
    await subscribe_and_process(sms_topic, lambda message: handle_sms_message(message, verification_event, opportunity_event))

async def handle_wakeup_event(opportunity_event):
    wakeup_topic = f"wakeup"
    logging.info(f"MQTT handle_wakeup_event() topic {wakeup_topic}")
    await subscribe_and_process(wakeup_topic, lambda message: handle_wakeup_message(message, opportunity_event))


async def handle_clean_claims_message(message, requirements_manager, opportunity_event, stealth_delayer):
    logging.info(f"handle_clean_claims_message {stealth_delayer}")
    requirements_manager.removeOneOffClaims()
    opportunity_event.set("Requirement Changed. Clean up Claims") # This will stop any long 5 minute pauses.
    logging.info("Cancel Any Stealth Delays")
    stealth_delayer.cancel()


async def watch_for_clean_claims(requirements_manager, opportunity_event, stealth_delayer):
    clean_claims_topic = f"opportunities/{configure.ATOZ_EMPLOYEE_ID}/cleanclaims"
    await subscribe_and_process(clean_claims_topic,
        lambda message: handle_clean_claims_message(message, requirements_manager, opportunity_event, stealth_delayer))


async def handle_claim_message(message, requirements_manager, opportunity_event, stealth_delayer):
    logging.info(f"handle_claim_message {stealth_delayer}")
    opportunity_id = message.payload.decode('utf-8')
    id_requirement = IDRequirement(opportunity_id)
    logging.info(f"Add New Requirements Claim ID {id_requirement}")
    requirements_manager.addClaim(id_requirement)
    opportunity_event.set("Requirement Changed with new IDRequirement") # This will stop any long 5 minute pauses.
    logging.info("Cancel Any Stealth Delays")
    stealth_delayer.cancel()


async def watch_for_new_claim(requirements_manager, opportunity_event, stealth_delayer):
    claim_topic = f"opportunities/{configure.ATOZ_EMPLOYEE_ID}/claim"
    await subscribe_and_process(claim_topic,
        lambda message: handle_claim_message(message, requirements_manager, opportunity_event, stealth_delayer))

def parse_days(days_list):
    return ', '.join(day.lower() for day in days_list)

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


def parse_vet_requirements(msg, vet_wrapper, requirement_manager):

    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        logging.info(f"parse_requirements: PAYLOAD {payload}")
        opportunity_type = payload.get("opportunity_type", "EXTRA_TIME")
        days = parse_days(payload.get("days", []))
        min_duration = int(payload.get("min_duration", 300))
        max_duration = int(payload.get("max_duration", 360))
        notice_hours = float(payload.get("notice", 48))
        start_date = str(parse_date(payload["start_date"]))
        end_date = str(parse_date(payload["end_date"]))
        start_time_pattern = payload.get("start_time_pattern","**:**")


        requirement = BooleanRequirement(vet_wrapper,
                PeriodRequirement(start_date, end_date,
                NoticeRequirement(int(notice_hours*60),
                DayRequirement(days,
                TypeRequirement(opportunity_type,
                StartTimeRequirement(start_time_pattern,
                MinTimeRequirement(min_duration,
                MaxTimeRequirement(max_duration))))))))
        logging.info(f"parse_vet_requirements: VET WRAPPER {vet_wrapper} boolean equiv of {vet_wrapper.value != 0}")
        logging.info(f"parse_vet_requirements: Built Requirement from message: {requirement}")

        logging.info("Clear any other VET requirements - only allowing one.")
        requirement_manager.clearVETrequirements()      # Only Allow ONE VET Requirement for now

        requirement_manager.addRequirements(requirement)
        logging.info(f"VET Requirement added to requirement_manager successfully. current state: {requirement_manager}")
        
    except Exception as e:
        print(f"Failed to process VET requirement message: {e}")

async def handle_vet_requirements_message(message, vet_allowed_wrapper, requirements_manager, opportunity_event):
    logging.info(f"Handle vet requirements message {message}")
    parse_vet_requirements(message, vet_allowed_wrapper, requirements_manager)
    opportunity_event.set("VET Requirement Changed - Wake up!")


async def watch_for_new_vet_requirements(requirements_manager, vet_allowed_wrapper, opportunity_event):
    requirements_topic = "setclaimschedule/vetrequirements"
    await subscribe_and_process(requirements_topic,
        lambda message: handle_vet_requirements_message(message, vet_allowed_wrapper, requirements_manager, opportunity_event))

async def handle_vet_allowed_message(message, vet_allowed_wrapper, opportunity_event):
    try:
        vet_allowed = int(message.payload.decode('utf-8'))
        logging.info(f"handle_vet_allowed_message: Changing VET ALLOWED FLAG to {vet_allowed}")
        vet_allowed_wrapper.value = vet_allowed
        opportunity_event.set("VET ALLOWED WRAPPER CHANGED")

    except Exception as e:
        logging.info(f"handle_vet_allowed_message: Invalid delay integer - ignoring {e}")
        

async def watch_for_new_vet_flag(vet_allowed_wrapper, opportunity_event):
    vet_allowed_topic = f"opportunities/{configure.ATOZ_EMPLOYEE_ID}/grabvetsflag"
    await subscribe_and_process(vet_allowed_topic,
        lambda message: handle_vet_allowed_message(message, vet_allowed_wrapper, opportunity_event))

async def handle_vto_schedule_message(message, requirements_manager, opportunity_event):
    mask = int(message.payload.decode('utf-8'))
    vto_requirement = TypeRequirement('TIME_OFF', DayRequirement(mask))
    #vto_requirement = DayRequirement(mask, TypeRequirement('TIME_OFF'),MinTimeRequirement(360)))
    requirements_manager.setConstantVTORequirement(vto_requirement)
    logging.info(f"Changing VTO Mask to {vto_requirement} New Requirements {requirements_manager}")
    logging.info("Requirement Mask Changed - Wake up!")
    opportunity_event.set("Requirement Mask Changed")

async def watch_for_new_requirements(requirements_manager, opportunity_event):
    vto_schedule_topic = f"opportunities/{configure.ATOZ_EMPLOYEE_ID}/setclaimschedule/vto"
    await subscribe_and_process(vto_schedule_topic,
        lambda message: handle_vto_schedule_message(message, requirements_manager, opportunity_event))

async def handle_stealth_delay_message(message, stealth_delayer):
    try:
        new_delay = int(message.payload.decode('utf-8'))
        logging.info(f"handle_stealth_delay_message: Changing STEALTH DELAY to {new_delay}")
        stealth_delayer.set_delay(new_delay)
    except Exception as e:
        logging.info(f"handle_stealth_delay_message: Invalid delay integer - ignoring {e}")
        

async def watch_for_new_stealth_delay(stealth_delayer):
    stealth_delay_topic = f"opportunities/{configure.ATOZ_EMPLOYEE_ID}/stealthdelay"
    await subscribe_and_process(stealth_delay_topic,
        lambda message: handle_stealth_delay_message(message, stealth_delayer))


def handle_webauthn_request_factory(webauthevent):
    logging.info("handle_webauthn_request_factory: Set up WebAuth Handler")
    async def handle_webauthn_request(options):
        #PROXY_URL = "http://127.0.0.1:5000/webauthn"
        PROXY_URL = "http://127.0.0.1:5000/webauthn_proxy"
        logging.info(f"Intercepted WebAuthn request (raise ValueError): {options}")

        webauthevent.set("Event from handle_webauthn_request")

        async with httpx.AsyncClient() as client:
            # Forward the options to your Flask proxy
            try:
                resp = await client.post(PROXY_URL, json=options)
                resp.raise_for_status()
                # Optionally get any response back from your proxy
                result = resp.json()
                logging.info(f"Proxy response: {result}")
                return result
            except Exception as e:
                logging.info(f"Error sending to proxy: {e}")
                return None
                
    return handle_webauthn_request

def handle_console(msg):
    text = msg.text

    if text.startswith("[PW-DEBUG]"):
        json_str = text.replace("[PW-DEBUG] ", "")
        logging.info(f"🟡 Javascript console : {json_str}")
    elif text.startswith("[PW-WEBAUTHN-REQUEST]"):
        json_str = text.replace("[PW-WEBAUTHN-REQUEST] ", "")
        logging.info(f"🔵 WebAuthn Request: {json_str}")

    elif text.startswith("[PW-WEBAUTHN-RESPONSE]"):
        json_str = text.replace("[PW-WEBAUTHN-RESPONSE] ", "")
        logging.info(f"🟢 WebAuthn Response: {json_str}")


async def authenticate_with_playwright(main_url, headless=True, javascript_enabled=True):


    logging.info(f'authenticate_with_playwright headless: {headless} javascript:{javascript_enabled}')


    async with async_playwright() as playwright:
        SESSION_STORAGE_PATH = "user_data"


        # webkit, firefox or chromium
        # Warning CHROMIUM is BUGGY in HEADLESS mode.
        # Warning FIREFOX is BUGGY in NON Javascript mode
        if (configure.USE_PLAYWRIGHT_BROWSER):
            raise ValueError("Playwright browsers no longer supported - set configure.USE_PLAYWRIGHT_BROWSER to False.")
            browser = await playwright.firefox.launch(headless=headless, args=["--disable-infobars"])
            context = await browser.new_context()
            page = await context.new_page()  # Fallback if no page exists

        else:
            # Create a persistent context (like a real user profile)
            # Apple
            if ('darwin' in sys.platform):
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            else:
                if 'linux' in sys.platform:
                    chrome_path = "/usr/bin/chromium"
                else:
                    raise ValueError(f"Unsupported platform. {sys.platform}")

            context = await playwright.chromium.launch_persistent_context(
                user_data_dir="/tmp/playwright-profile",  # keep cookies, logins
                executable_path=chrome_path,
                headless=False,  # important: run in headed mode
                args=[
                    "--disable-blink-features=AutomationControlled",  # reduce bot signals
                ]
            )
            page = await context.new_page()

        # Hook into javascript log.console (only used for debugging).
        page.on("console", handle_console)

        # Intercept
        if (configure.LOG_INTERCEPTS):
            await page.route(url=route_matcher, handler=intercept)

        async def log_response_headers(response):
            url = response.url
            headers = response.headers
            allow_origin = headers.get("access-control-allow-origin", "Origin Not Present")
            allow_methods = headers.get("access-control-allow-methods", "Methods Not Present")
            allow_headers = headers.get("access-control-allow-headers", "Headers Not Present")
            allow_credentials = headers.get("access-control-allow-credentials", "Credentials Not Present")
            watch_url='atoz-api-us-east-1.amazon.work'
            if (watch_url in url):
                logging.info(f"log_response_headers: url: {url}")
                logging.info(f"log_response_headers: Access-Control-Allow-*: {url} origin: {allow_origin} methods: {allow_methods} headers:{allow_headers} credentials:{allow_credentials}")


        # Handle webauthn requests.  (see also javascripts.py)      
        webauthn_event = EventWrapper()
        await page.expose_function("py_webauthn_hook", handle_webauthn_request_factory(webauthn_event))

        # Add response event listener 
        if (configure.LOG_RESPONSE_HEADERS):
            page.on("response", log_response_headers)

        if (configure.SUPER_STEALTH):
            logging.info("Running in Super Stealth Mode")
            raise Exception("SUPER STEALTH MODE (configure.SUPER_STEALTH) NO LONGER SUPPORTED. (configure.py)")
            await stealth_async(page)
        else:
            logging.info("Running Simple Stealth Mode")
            await page.add_init_script(javascripts.FIREFOX_STEALTH_SCRIPT + javascripts.WEBAUTH_HOOK)

        #asyncio.create_task(handle_404_page(page, "https://atoz.amazon.work/voluntary_time_off")) 
        #asyncio.create_task(handle_refresh(page, poll_timer_wrapper))

        verificaton_event = EventWrapper()
        opportunity_event = EventWrapper()

        answer_event = EventWrapper()

        #mqtt_sms_task = receive_sms(verificaton_event, opportunity_event)
        #asyncio.gather(mqtt_sms_task)


        # MQTT event handling. 
        asyncio.create_task(receive_sms(verificaton_event, opportunity_event))
        asyncio.create_task(receive_captcha_answer(answer_event)),

        asyncio.create_task(handle_wakeup_event(opportunity_event))

        asyncio.create_task(handle_captcha_form(page, answer_event)),

        asyncio.create_task(handle_session_modal(page)) # Modal window which asks do 'we want to stay logged-in?'
        asyncio.create_task(monitor_url(page))

        # Attempt to click on ANY VTO that happens to be on the page
        asyncio.create_task(handle_vto_page(page))
        asyncio.create_task(handle_vto_accept_page(page))
        asyncio.create_task(handle_vto_view_page(page))


        asyncio.create_task(handle_login(page))
        asyncio.create_task(handle_aa_login(page))

        asyncio.create_task(handle_otp_pin(page,verificaton_event))
        asyncio.create_task(handle_opt_device_select(page, configure.OTP_INDEX))

        asyncio.create_task(handle_passkey_pin(page, webauthn_event))
        asyncio.create_task(handle_webauthn(webauthn_event)),

        atoz_task = asyncio.create_task(handle_content(main_url, context, page, opportunity_event))

        try:
            await atoz_task
        except TargetClosedError as tce:
            print(f"Caught TargetClosedError: {tce}")
            await asyncio.sleep(1) 
            exit(-1)
            
        except Exception as e:
            print(f"Caught exception: {e}")
            await asyncio.sleep(1) 
            #exit(-1)
        while True:
            print("Sleep 4 EVER!")
            await asyncio.sleep(6000)  # .Sleep for Ever.

        #await browser.close()

async def work_session():
    MAIN_PAGE = "https://atoz.amazon.work/"
    MAIN_PAGE = "https://atoz.amazon.work/voluntary_time_off"

    await authenticate_with_playwright(MAIN_PAGE, headless=configure.HEADLESS, javascript_enabled=True)
    
    while True:
        logging.info("work_session")
        await asyncio.sleep(10)

async def webbot_session():

    logging.basicConfig(filename=None, format='%(name)s %(levelname)s: %(asctime)s: %(message)s', level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.info(f"{'*** WARNING! WARNING! *** ' if configure.Mock else ''}Mock:{configure.Mock} Limited: {configure.Limited}")

    try:
        await work_session()
        print("ws-------------->", e, type(e), "<====================")
    except InvalidStateError as ise:
        print("Invalid State Error trapped")
    except Exception as e:
        print("General Exception -------------->", e, type(e), "<====================")



asyncio.run(webbot_session())