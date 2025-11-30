import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

# 🔐 ENV VARIABLES
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME")  # ex: Monitoring_2


# 🎨 FORMAT SENSOR
def format_sensor(v):
    if not v:
        return ""
    v = v.lower()
    if v == "error":
        return "🔴 Erreur"
    if v == "log":
        return "🟢 Log"
    return v


# 🎨 FORMAT STATUT
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

        # Lire le JSON reçu
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

        # Détection IA
        has_ia = (
            "IA_Diagnostic" in body
            or "IA_Score" in body
            or "IA_Recommendation" in body
            or "IA_Type_Problème" in body
            or "IA_Priorité" in body
        )

        statut = body.get("Statut", "").lower()

        ########################################################
        # 🟥 BAD ENDING phase 1 (Erreur ET pas d’IA) → PAS stockage
        ########################################################
        if statut in ["échec", "failed", "error"] and not has_ia:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "PRE_IA_OK"}).encode())
            return

        ########################################################
        # 🟩 TRUE ENDING (Succès AND pas IA) → STOCKAGE
        ########################################################
        # On laisse passer vers stockage

        ########################################################
        # 🟦 BAD ENDING phase 2 (IA) → STOCKAGE
        ########################################################
        # On laisse passer vers stockage

        # Préparer champs Airtable
        fields = {
            "Workflow": body.get("Workflow", ""),
            "Module": body.get("Module", ""),
            "Sensor": format_sensor(body.get("Sensor", "")),
            "Statut": format_status(body.get("Statut", "")),
            "Message": body.get("Message", ""),
            "IA_Diagnostic": body.get("IA_Diagnostic", ""),
            "IA_Recommendation": body.get("IA_Recommendation", ""),
            "IA_Score": body.get("IA_Score", ""),
            "IA_Type_Problème": body.get("IA_Type_Problème", ""),
            "IA_Priorité": body.get("IA_Priorité", "")
        }

        # Ajouter Date si fournie
        if "Date" in body:
            fields["Date"] = body.get("Date")

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
                "error": f"Airtable error: {e}"
            }).encode())
