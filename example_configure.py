ATTEMPT_GRABBING = True     # Smash and Grab (We now always use GraphQL for grabbing opportunities.

UPDATE_OPPORTUNITIES = True # 
USE_RESTFUL_API = True      # Use Restful API For Full listing of Opportunities.(Not used if UPDATE_OPPORTUNITIES is False)
REPORT_OPPORTUNTIES = False

VERSION="1.0"

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
ATOZ_PASSWORD = 'mypassw0rd!'
ATOZ_EMPLOYEE_ID = '111283278'
# (PEDRO,3), (PICO,1), (ZIPPY, 4)
DEVICE_CHOICES = [('PEDRO',3), ('PICO',1), ('ZIPPY',4)]
DEVICE_NAME, OTP_INDEX = DEVICE_CHOICES[2]

# HTTPX.get/post timeout
HTTPX_TIMEOUT=4.0
HTTPX_RETRIES=4


# MQTT Credentials
MQTT_USERNAME = 'mqtt_user'
MQTT_SECRET = 'mys3cret'
MQTT_HOSTNAME = '100-71-192-43.ip.linodeusercontent.com'
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


# Notify Me
NOTIFICATIONS_TOKEN='amzn1.ask.account.AF6Y36IXG2FA4JBGCLP2SZFZAXAWMQXBLPHKX24YSQGNSD33RSVARHDRVFBESNUZTZEOF5TFVQMXT5PVEZDCYRPHMYX6VCDA4ZWU76YQFTR5ZM6EEDT3V3GSJPFWUVGRRGJYP5PTMQWKUH6S6TCS3EEN4IGDQ6DY'
VOICEMONKEY_TOKEN="8c98ca46f72c080_0472109ba1d9ebfdc968ee79b5326ed9"
VOICEMONKEY_DEVICE="johns-echo-plus"

# 2CAPTCHA SECRET KEY
TWO_CAPTCHA_API_KEY = "c888577c5881e4f4df4eebc86a3"


# Stealth Script - Beaware that RPi fails when SUPER_STEALTH is set to True
SUPER_STEALTH=False

FIREFOX_STEALTH_SCRIPT = """

window.originalFetch = window.fetch;
window.fetch = (...args) => {
    console.log("Intercepted fetch call with args:", args);
    return window.originalFetch(...args);
};


window.webapi = async (...args) => {
    const [url, service, body] = args;

    function generateUID(length = 12) {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        const charactersLength = characters.length;
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * charactersLength));
        }
        return result;
    }
    const uuid = generateUID();
    try {
        const headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "x-atoz-client-id": `${service}`,
            "x-atoz-client-request-id": `${uuid}`,
            'X-Requested-With': 'XMLHttpRequest',
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Origin":"https://atoz.amazon.work",
            "Referer":"https://atoz.amazon.work"
        };

        const response = await fetch(url, {
            method: "POST",
            headers: headers,
            body: body,
            //mode:'no-cors',
            credentials: 'include'
        });

        console.log(`webapi - Response = ${response.status}`);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        return {
            content: await response.json(),
            request: headers,
            uuid: uuid,
            status: response.status,
        };

    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
};


function setupCursor(parentId) {

        const cursor = document.createElement('div');
        cursor.id = 'playwright-mouse';
        cursor.style.position = 'absolute';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '10000';

        // Create the stem (shaft)
        const stem = document.createElement('div');
        stem.style.width = '2px';
        stem.style.height = '6px';
        stem.style.backgroundColor = 'red';
        stem.style.position = 'absolute';
        stem.style.top = '50%';
        stem.style.left = '50%';

        // Create the arrowhead
        const arrowhead = document.createElement('div');
        arrowhead.style.width = '0';
        arrowhead.style.height = '0';
        arrowhead.style.borderLeft = '5px solid transparent';
        arrowhead.style.borderRight = '5px solid transparent';
        arrowhead.style.borderBottom = '10px solid red';
        arrowhead.style.position = 'absolute';
        arrowhead.style.top = '-10px';
        arrowhead.style.left = '-5px';

        // Append to cursor and body
        cursor.appendChild(stem);
        cursor.appendChild(arrowhead);

        const parentDiv = document.getElementById(parentId);

        if (parentDiv) {
            parentDiv.appendChild(cursor);
        }


        // Apply rotation to the entire cursor

        let angle = -22;  // Angle of rotation in degrees (can be adjusted)
        cursor.style.transform = `rotate(${angle}deg)`;  // Rotate the arrow at a slight angle

        document.addEventListener('mousemove', function(event) {
            console.log(`FIREFOX_STEALTH_SCRIPT (new version) ${parentDiv}: mousemove Event Listener. Mouse coordinates: X=${event.clientX}, Y=${event.clientY}`);
            cursor.style.left = `${event.pageX - 0}px`;  // Adjust the position to center the cursor
            cursor.style.top = `${event.pageY + 4}px`;  // Adjust to center the cursor
        });

}



// 1. Remove navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Modify navigator.permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: 'denied' }) :
        originalQuery(parameters)
);

// 3. Modify navigator.plugins and navigator.mimeTypes
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3], // Fake plugins
});
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => [1, 2, 3], // Fake mimeTypes
});

// 4. Mock WebGL vendor and renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
    if (parameter === 37445) return 'Mozilla'; // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Mozilla Renderer'; // UNMASKED_RENDERER_WEBGL
    return getParameter(parameter);
};

// 5. Modify navigator.languages for UK
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-GB', 'en']
});

// 6. Mock navigator.hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 4 // Set to 4 CPU cores
});

// 7. Mock screen dimensions
Object.defineProperty(window, 'outerWidth', {
    get: () => window.innerWidth
});
Object.defineProperty(window, 'outerHeight', {
    get: () => window.innerHeight
});

// 8. Disable console.debug
console.debug = () => {};


// 9. Mouse Movement Script
function moveMouseRandomly() {
    console.log('moveMouseRandomly set up...')
    const moveMouse = () => {
        const x = Math.floor(Math.random() * window.innerWidth);
        const y = Math.floor(Math.random() * window.innerHeight);
        console.log(`Moving mouse to coordinates: (${x}, ${y})`);

        window.dispatchEvent(new MouseEvent('mousemove', {
            clientX: x,
            clientY: y,
            bubbles: true
        }));
    };

    // Move the mouse every 2-5 seconds
    setInterval(moveMouse, Math.random() * 3000 + 2000);
}

// 10. Mouse Activity - Listen out for mouse event listeners being added
(function() {
    // Store the original addEventListener function
    const originalAddEventListener = EventTarget.prototype.addEventListener;
    console.log('*******add Event Listener Tracker*********');
    // Override addEventListener to log events
    EventTarget.prototype.addEventListener = function(type, listener, options) {
        if (type === 'mousemove' || type === 'mousedown' || type === 'mouseup') {
            console.log(`Event listener added for: ${type}`);
        }
        // Call the original addEventListener method
        originalAddEventListener.call(this, type, listener, options);
    };
})();

function findFirstExistingElement(ids) {
    for (const id of ids) {
        const element = document.getElementById(id);
        if (element) {
            return { id, element }; // Return both the ID and the element
        }
    }
    return null; // Return null if none of the IDs exist
}


function waitForElementAndAddChild(parentId) {
    const intervalId = setInterval(() => {
        const parentDiv = document.getElementById(parentId);
        if (parentDiv) {
            clearInterval(intervalId); // Stop checking
            setupCursor(parentId);

        }
    }, 100); // Check every 100 milliseconds
}

//const rootId = 'main-content';
//const rootId = 'atoz-app-root';

const rootId = 'atoz-content';
""" 



CHROME_STEALTH_SCRIPT = """
// 1. Remove navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Mock window.chrome
window.chrome = {
    runtime: {}
};

// 3. Modify navigator.permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: 'denied' }) :
        originalQuery(parameters)
);

// 4. Modify navigator.plugins and navigator.mimeTypes
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3], // Fake plugins
});
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => [1, 2, 3], // Fake mimeTypes
});

// 5. Mock WebGL vendor and renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
    if (parameter === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    return getParameter(parameter);
};

// 6. Modify navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-GB', 'en']
});

// 7. Mock navigator.hardwareConcurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 4 // Set to 4 CPU cores
});

// 8. Mock screen dimensions
Object.defineProperty(window, 'outerWidth', {
    get: () => window.innerWidth
});
Object.defineProperty(window, 'outerHeight', {
    get: () => window.innerHeight
});

// 9. Disable console.debug
console.debug = () => {};

// 10. Mouse Movement Script



function moveMouseRandomly() {
    const moveMouse = () => {
        const x = Math.floor(Math.random() * window.innerWidth);
        const y = Math.floor(Math.random() * window.innerHeight);
        console.log(`Moving mouse to coordinates: (${x}, ${y})`);

        window.dispatchEvent(new MouseEvent('mousemove', {
            clientX: x,
            clientY: y,
            bubbles: true
        }));
    };

    // Move the mouse every 2-5 seconds
    setInterval(moveMouse, Math.random() * 3000 + 2000);
}

moveMouseRandomly();

"""

