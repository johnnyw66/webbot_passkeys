from fido2.hid import CtapHidDevice
from fido2.client import Fido2Client
import os
import base64

# Pick first FIDO2 device
dev = next(CtapHidDevice.list_devices())
client = Fido2Client(dev, "localhost")  # RP ID

# Build creation options as a dict (v2.x style)
creation_options = {
    "rp": {"id": "localhost", "name": "Local Test RP"},
    "user": {"id": b"user123", "name": "testuser", "displayName": "Test User"},
    "challenge": os.urandom(32),
    "pubKeyCredParams": [{"type": "public-key", "alg": -7}],  # ES256
    "timeout": 60000,
    "attestation": "direct"
}

print("Touch your security key now...")
attestation_object, client_data = client.make_credential(creation_options)

cred_id_b64 = base64.urlsafe_b64encode(
    attestation_object.auth_data.credential_data.credential_id
).decode("utf-8")
print("Credential created!")
print("Credential ID:", cred_id_b64)
