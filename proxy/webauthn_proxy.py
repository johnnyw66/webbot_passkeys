from flask import Flask, request, jsonify
from fido2.client import Fido2Client
from fido2.hid import CtapHidDevice
from fido2.webauthn import PublicKeyCredentialRequestOptions, PublicKeyCredentialDescriptor

app = Flask(__name__)

# Find the first connected FIDO device
devices = list(CtapHidDevice.list_devices())
if not devices:
    raise RuntimeError("No FIDO devices found")

device = devices[0]

print("FIDO2 Device", device)

@app.route("/webauthn", methods=["POST"])
def webauthn():
    data = request.get_json()
    print("Received WebAuthn request:", data)
    # You could do logging, analysis, or forward to real server here
    return jsonify({"status": "ok"})


# Create a FIDO2 client for your RP ID
# Replace with your derived rpId
rp_id = "atozworkforce.idprism-auth.amazon.com"
client = Fido2Client(device, rp_id)


    
@app.route("/webauthn_proxy", methods=["POST"])
def webauthn_proxy():
    data = request.json
    print("Received JSON:", data)

    # Extract challenge bytes
    challenge_bytes = bytes(
        data["publicKey"]["challenge"][str(i)] for i in range(len(data["publicKey"]["challenge"]))
    )

    # Extract allowed credentials
    allow_credentials = [
        PublicKeyCredentialDescriptor(
            id=bytes(c["id"][str(i)] for i in range(len(c["id"]))),
            type=c["type"]
        )
        for c in data["publicKey"].get("allowCredentials", [])
    ]

    # Build request options
    options = PublicKeyCredentialRequestOptions(
        challenge=challenge_bytes,
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=data["publicKey"].get("userVerification", "required")
    )

    # Ask the FIDO device for an assertion
    assertion = client.get_assertion(options)

    # Convert assertion to dict to send back to Playwright
    response = assertion.get_response(0).to_json()
    return jsonify(response)


if __name__ == "__main__":
    app.run(port=5000)


