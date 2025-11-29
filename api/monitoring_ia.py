import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🔧 Variables d’environnement
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
    if v in ["succès", "success"]:
        return "🟢 Succès"
    if v in ["échec", "failed"]:
        return "🔴 Échec"
    return value


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # 📥 Lire le JSON reçu
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            body = json.loads(raw)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Invalid JSON: {e}".encode())
            return

        # 🔗 Construire l’URL Airtable
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

        # 🕒 Date (optionnelle)
        if "Date" in body:
            fields["Date"] = body["Date"]

        # 🧠 Champs IA (optionnels)
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

        # 📤 Envoi vers Airtable + renvoi du record_id
        try:
            with urllib.request.urlopen(req) as response:
                airtable_response = json.loads(response.read().decode())

                record_id = airtable_response.get("id", "")

                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "OK",
                    "record_id": record_id
                }).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Airtable error: {e}".encode())
