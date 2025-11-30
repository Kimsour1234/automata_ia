import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# ENV VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")


def format_sensor(v):
    if not v:
        return ""
    v = v.lower()
    if v == "error":
        return "🔴 Erreur"
    if v == "log":
        return "🟢 Log"
    return v


def format_status(v):
    if not v:
        return ""
    v = v.lower()
    if v == "success":
        return "🟢 Succès"
    if v in ["failed", "échec", "error"]:
        return "🔴 Échec"
    return v


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            body = json.loads(raw)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
            return


        # 🟥 CAS 1 — BAD END PASSAGE 1 (PAS de champs IA → PAS de stockage)
        if "IA_Diagnostic" not in body and "IA_Recommendation" not in body:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "PRE_IA_OK",
                "received": body
            }).encode())
            return


        # 🟩 CAS 2 — SUCCESS OU BAD END PASSAGE 2 → STOCKAGE

        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", ""),
            "IA_Diagnostic": body.get("IA_Diagnostic", ""),
            "IA_Recommendation": body.get("IA_Recommendation", ""),
            "IA_Score": body.get("IA_Score", "")
        }

        if "Date" in body:
            fields["Date"] = body["Date"]

        payload = json.dumps({"fields": fields}).encode()

        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            urllib.request.urlopen(req)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "STORED",
                "fields": fields
            }).encode())
            return

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": f"Airtable error: {e}"
            }).encode())
            return
