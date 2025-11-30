import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🌐 ENV VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")   # ex: Monitoring_2


def clean(s):
    """Supprime tous les caractères interdits JSON + contrôle"""
    if not isinstance(s, str):
        s = str(s)
    return ''.join(c for c in s if ord(c) >= 32)


def format_sensor(v):
    v = clean(v).lower()
    if v == "error":
        return "🔴 Erreur"
    if v == "log":
        return "🟢 Log"
    return v


def format_status(v):
    v = clean(v).lower()
    if v == "success":
        return "🟢 Succès"
    if v in ["failed", "error", "échec"]:
        return "🔴 Échec"
    return v


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        # 🛡️ SAFE JSON — On nettoie AVANT de parser
        string = raw.decode(errors="ignore")
        string = clean(string)

        try:
            body = json.loads(string)
        except:
            # 🔥 En dernier recours → on encapsule le message brut
            body = {"raw": string}

        workflow = clean(body.get("Workflow", ""))
        module = clean(body.get("Module", ""))
        sensor_raw = clean(body.get("Sensor", "")).lower()
        statut_raw = clean(body.get("Statut", ""))
        message_raw = clean(body.get("Message", ""))

        has_ia = any(k in body for k in ["IA_Score", "IA_Diagnostic", "IA_Recommendation"])

        # 🟥 BAD END 1er passage → pas de stockage
        if sensor_raw == "error" and not has_ia:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "PRE_IA_OK",
                "received": body
            }).encode())
            return

        # 🟩 TRUE END ou BAD END 2e passage → STOCKAGE
        fields = {
            "Workflow": workflow,
            "Module": module,
            "Sensor": format_sensor(sensor_raw),
            "Statut": format_status(statut_raw),
            "Message": message_raw,
            "IA_Score": clean(body.get("IA_Score", "")),
            "IA_Diagnostic": clean(body.get("IA_Diagnostic", "")),
            "IA_Recommendation": clean(body.get("IA_Recommendation", ""))
        }

        if "Date" in body:
            fields["Date"] = clean(body["Date"])

        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        payload = json.dumps({"fields": fields}).encode()

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "STORED",
                    "stored": fields
                }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": f"Airtable error: {clean(str(e))}"
            }).encode())
