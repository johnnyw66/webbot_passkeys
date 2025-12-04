import requests
import json

challenge_json = {
    "rpId": "atozworkforce.idprism-auth.amazon.com",
    "challenge": "BASE64URL_ENCODED_CHALLENGE",
    "allowCredentials": [
        {"type": "public-key", "id": "BASE64URL_ENCODED_CREDENTIAL_ID"}
    ],
    "userVerification": "preferred"
}

r = requests.post("http://127.0.0.1:9100/assertion", json=challenge_json)
print(r.status_code)
print(json.dumps(r.json(), indent=2))
