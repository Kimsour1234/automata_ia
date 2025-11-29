import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🔧 ENVIRONMENT VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")  # ex: Monitoring_2


# 🎨 FORMATAGE DES ÉMOTIONS
def format_sensor(v):
    if not v:
        return ""
    v = v.lower()
    if v == "error":
        return "🔴 Error"
    if v == "log":
        return "🟢 Log"
    return v


def format_status(v):
    if not v:
        return ""
    v = v.lower()
    if v == "success":
        return "🟢 Succès"
    if v == "échec" or v == "failed" or v == "error":
        return "🔴 Échec"
    return v


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        # 📥 Lecture du JSON reçu
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        try:
            body = json.loads(raw)
        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
            return

        # 🔗 URL Airtable
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        # 🧩 Construction de l’enregistrement Airtable
        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", "")
        }

        # Champs IA (facultatifs)
        if "IA_Score" in body:
            fields["IA_Score"] = body.get("IA_Score", "")

        if "IA_Diagnostic" in body:
            fields["IA_Diagnostic"] = body.get("IA_Diagnostic", "")

        if "IA_Recommendation" in body:
            fields["IA_Recommendation"] = body.get("IA_Recommendation", "")

        # Date (si fournie)
        if "Date" in body:
            fields["Date"] = body.get("Date")

        data = {"fields": fields}
        payload = json.dumps(data).encode()

        # 📤 Envoi Airtable
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as response:

                # Réponse Vercel → Make (important pour Parse response)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                # On renvoie à Make exactement ce qu’on a reçu
                self.wfile.write(json.dumps({
                    "status": "OK",
                    "stored": fields
                }).encode())

        except Exception as e:

            # ❌ Erreur Airtable
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "error": f"Airtable error: {e}"
            }).encode())
