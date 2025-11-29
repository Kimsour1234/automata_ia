import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🔧 Variables d’environnement Vercel
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")  # "Monitoring_2"


# 🎨 Formatage des valeurs
def format_sensor(value):
    if not value:
        return ""
    v = value.lower()
    if v == "log":
        return "🟢 Log"
    if v == "error":
        return "🔴 Erreur"
    return value


def format_status(value):
    if not value:
        return ""
    v = value.lower()
    if v == "succès" or v == "success":
        return "🟢 Succès"
    if v == "échec" or v == "failed":
        return "🔴 Échec"
    return value


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # 📥 Lecture du JSON envoyé par Make
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            body = json.loads(raw)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON: {e}".encode())
            return

        # 🔗 URL Airtable
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        # 📝 Champs envoyés à Airtable
        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", "")
        }

        # 🕒 Ajout date si fournie
        if "Date" in body:
            fields["Date"] = body["Date"]

        # 🧠 Champs IA (facultatifs)
        if "IA_Score" in body:
            fields["IA_Score"] = body["IA_Score"]

        if "IA_Diagnostic" in body:
            fields["IA_Diagnostic"] = body["IA_Diagnostic"]

        if "IA_Recommendation" in body:
            fields["IA_Recommendation"] = body["IA_Recommendation"]

        payload = json.dumps({"fields": fields}).encode()

        req = urllib.request.Request(
            url, data=payload, headers=headers, method="POST"
        )

        # 🚀 Envoi vers Airtable
        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Airtable error: {e}".encode())
