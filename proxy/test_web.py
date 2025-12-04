from flask import Flask, request, jsonify
from fido2.hid import CtapHidDevice
from fido2.client import Fido2Client
import base64
import traceback

app = Flask(__name__)

# Pick the first FIDO2 device connected
devices = list(CtapHidDevice.list_devices())
if not devices:
    raise RuntimeError("No FIDO2 device found!")
dev = devices[0]

# Helper: decode base64url string to bytes
def b64url_decode(s: str) -> bytes:
    s += '=' * (-len(s) % 4)  # pad to multiple of 4
    return base64.urlsafe_b64decode(s)

@app.route("/assertion", methods=["POST"])
def webauthn_proxy():
    try:
        options = request.get_json()
        if not options:
            return jsonify({"error": "Missing JSON payload"}), 400

        # RP ID
        rp_id = options.get("rpId")
        if not rp_id:
            return jsonify({"error": "Missing rpId"}), 400

        # Challenge
        challenge_b64 = options.get("challenge")
        if not challenge_b64:
            return jsonify({"error": "Missing challenge"}), 400
        options["challenge"] = b64url_decode(challenge_b64)

        # Decode credential IDs
        for cred in options.get("allowCredentials", []):
            if "id" in cred:
                cred["id"] = b64url_decode(cred["id"])

        # Create a new client per request
        client = Fido2Client(dev, rp_id)

        # Get assertion
        assertion = client.get_assertion(options)

        # Convert assertion(s) to JSON-serializable form
        response_list = []
        for a in assertion.get_response(0):
            response_list.append({
                "credentialId": base64.urlsafe_b64encode(a.credential["id"]).decode("utf-8"),
                "authData": base64.urlsafe_b64encode(a.auth_data).decode("utf-8"),
                "signature": base64.urlsafe_b64encode(a.signature).decode("utf-8"),
                "userHandle": (base64.urlsafe_b64encode(a.user_handle).decode("utf-8")
                               if a.user_handle else None)
            })

        return jsonify({
            "rpId": rp_id,
            "assertions": response_list
        })

    except Exception as e:
        # Print traceback in server console
        traceback.print_exc()
        # Always return JSON
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9100)
