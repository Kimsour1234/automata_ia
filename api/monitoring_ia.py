import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🔐 ENVIRONMENT VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")   # ex: Monitoring_2


# 🎨 FORMATAGE SENSOR
def format_sensor(v):
    if not v:
        return ""
    v = v.lower()
    if v == "error":
        return "🔴 Erreur"
    if v == "log":
        return "🟢 Log"
    return v


# 🎨 FORMATAGE STATUT
def format_status(v):
    if not v:
        return ""
    v = v.lower()
    if v in ["success", "succès"]:
        return "🟢 Succès"
    if v in ["échec", "failed", "error"]:
        return "🔴 Échec"
    return v


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        # 📥 Lire JSON
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

        ############################################
        # 🟥 PHASE 1 — BAD ENDING SANS IA → PAS DE STOCKAGE
        ############################################
        if "IA_Diagnostic" not in body and "IA_Score" not in body:
            # Renvoi brut pour Parse Response dans Make
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "status": "PRE_IA_OK",
                "received": body
            }).encode())

            return  # STOP → pas de stockage Airtable


        ############################################
        # 🟩 PHASE 2 — POST IA → STOCKAGE COMPLET
        # 🟩 GOOD ENDING → STOCKAGE DIRECT
        ############################################

        # Préparation des champs pour Airtable
        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", ""),

            # Champs IA
            "IA_Diagnostic": body.get("IA_Diagnostic", ""),
            "IA_Recommendation": body.get("IA_Recommendation", ""),
            "IA_Score": body.get("IA_Score", ""),
            "IA_Type_Problème": body.get("IA_Type_Problème", ""),
            "IA_Priorité": body.get("IA_Priorité", "")
        }

        # Ajouter Date si envoyée
        if "Date" in body:
            fields["Date"] = body.get("Date")

        # Payload Airtable
        payload = json.dumps({"fields": fields}).encode()

        # URL Airtable
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            urllib.request.urlopen(req)

            # Réponse Make
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "STORED",
                "stored": fields
            }).encode())

        except Exception as e:
            # Si Airtable plante
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": f"Airtable error: {e}"
            }).encode())
