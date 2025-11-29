import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🌐 ENVIRONMENT VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")   # ex: Monitoring_2


# 🎨 FORMATAGE SENSOR
def format_sensor(v):
    if not v:
        return ""
    v = v.lower()
    if v == "error":
        return "🔴 Error"
    if v == "log":
        return "🟢 Log"
    return v


# 🎨 FORMATAGE STATUT
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

        # 📥 Lire JSON du POST
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

        # 🟦 CAS 1 : PAS D'IA → C'est le HTTP AVANT IA
        # ➜ On NE crée PAS de ligne Airtable
        # ➜ On renvoie juste le JSON pour Parse Response
        if "IA_Score" not in body and "IA_Diagnostic" not in body:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "PRE_IA_OK",
                "received": body
            }).encode())

            return  # ❗ on ARRÊTE ici → pas de création Airtable


        # 🟩 CAS 2 : IA PRÉSENTE → C'est le HTTP APRÈS IA
        # ➜ On crée la ligne Airtable complète

        # Préparation champs Airtable
        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", ""),
            "IA_Score": body.get("IA_Score", ""),
            "IA_Diagnostic": body.get("IA_Diagnostic", ""),
            "IA_Recommendation": body.get("IA_Recommendation", "")
        }

        # Date si envoyée
        if "Date" in body:
            fields["Date"] = body.get("Date")

        # Construction payload Airtable
        data = {"fields": fields}
        payload = json.dumps(data).encode()

        # URL Airtable
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        # 📤 Envoi Airtable
        try:
            with urllib.request.urlopen(req) as response:

                # Réponse envoyée à Make
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "status": "STORED",
                    "stored": fields
                }).encode())

        except Exception as e:

            # ❌ Erreur côté Airtable
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "error": f"Airtable error: {e}"
            }).encode())
