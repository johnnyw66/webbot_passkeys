ATTEMPT_GRABBING = True     # Smash and Grab (We now always use GraphQL for grabbing opportunities.

UPDATE_OPPORTUNITIES = True # 
USE_RESTFUL_API = True      # Use Restful API For Full listing of Opportunities.(Not used if UPDATE_OPPORTUNITIES is False)
REPORT_OPPORTUNTIES = False

VERSION="2.0"

DEBUG_EXCEPTION = False
Mock = False  # Mock Grabbing - set to True for testing Requirements - no grabbing done.
Limited = True # Grab one opportuntity per stealth delay
#
BROWSER_DRIVER = 'playwright'
HEADLESS = False
USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
USE_PLAYWRIGHT_BROWSER = False  # Set to False if you want a persistent real browser.


START_DATE_OFFSET = 1
END_DATE_OFFSET = 365

ATOZ_USERNAME = 'smithjkw'
ATOZ_PASSWORD = 'mypassw0rd!'  # Password not needed if registered for 'passkeys'
ATOZ_EMPLOYEE_ID = '111283278'
# (PEDRO,3), (PICO,1), (ZIPPY, 4)
DEVICE_CHOICES = [('MYSMSVERIFIER',0),('PEDRO',3), ('PICO',1), ('ZIPPY',4)]
DEVICE_NAME, OTP_INDEX = DEVICE_CHOICES[0]

# PASSKEY PIN USED FOR YOUR PICO FIDO KEY ON ATOZ DOMAIN
PASSKEYPIN = '0000'

# HTTPX.get/post timeout
HTTPX_TIMEOUT=4.0
HTTPX_RETRIES=4


# MQTT Credentials
MQTT_USERNAME = 'mqtt_user'
MQTT_SECRET = 'mys3cret'
MQTT_BROKER = '132.145.21.76'
MQTT_PORT = 1883

# Email credentials
EMAIL = "myemail@gmail.com"
EMAIL_APP_PASSWORD = "gtihgvchdhdjosx"  # APP Password
IMAP_SERVER = "imap.gmail.com"  # For Gmail. Use your provider's IMAP server.
TEST_EMAIL_ALERTS=True
EMAIL_ALERT_SUBJECTS=["vto"] #['vto','vet']
EMAIL_PEEKER=False

#
STEALTH_GRAB_DELAY = 5

# Logging
LOG_INTERCEPTS = False
LOG_RESPONSE_HEADERS = False


# Notify Me and Voice Monkey - announcements to Echo/Alex speaker devices
NOTIFICATIONS_TOKEN='amzn1.ask.account.AF6Y36IXG2FA4JBGCLP2SZFZAXAWMQXBLPHKX24YSQGNSD33RSVARHDRVFBESNUZTZEOF5TFVQMXT5PVEZDCYRPHMYX6VCDA4ZWU76YQFTR5ZM6EEDT3V3GSJPFWUVGRRGJYP5PTMQWKUH6S6TCS3EEN4IGDQ6DY'
VOICEMONKEY_TOKEN="8c98ca46f72c080_0472109ba1d9ebfdc968ee79b5326ed9"
VOICEMONKEY_DEVICE="johns-echo-plus"

# 2CAPTCHA SECRET KEY - NOT NEEDED IF REGISTERED TO USE PASSKEYS
TWO_CAPTCHA_API_KEY = "c888577c5881e4f4c86a3"


# Stealth Script - Beaware that RPi fails when SUPER_STEALTH is set to True
SUPER_STEALTH=False

