from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import serial
import serial.tools.list_ports
import time
import re
import os
from bson import ObjectId
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Optional: Add CORS headers manually
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri, server_api=ServerApi('1'))
db = client["pillDispenser"]
collection = db["prescriptions"]

# Tablet mapping
tablet_mapping = {
    "Diazepam - 5mg": "1",
    "Paracetamol - 500mg": "2",
    "Amoxicillin - 250mg": "3",
    "Ibuprofen - 400mg": "4",
    "Azithromycin - 250mg": "5",
    "Metformin - 500mg": "6",
    "Amlodipine - 5mg": "7",
    "Losartan - 50mg": "8",
}

# Attempt to detect Arduino
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "ttyUSB" in port.device:
            return port.device
    return None

# Fallback: mock Arduino if not found
class MockArduino:
    def write(self, data): print("🧪 Mock write:", data)
    def readline(self): return b"OK\n"
    @property
    def in_waiting(self): return 1

# Setup serial communication
try:
    port = find_arduino_port() or 'COM10'  # Default to COM10 if auto-detect fails
    arduino = serial.Serial(port, 9600, timeout=2)
    time.sleep(2)
    print(f"✅ Arduino connected on {port}")
except Exception as e:
    print(f"❌ Failed to connect to Arduino: {e}")
    arduino = MockArduino()

# ObjectId to str utility
def convert_objectid_to_str(obj):
    if isinstance(obj, list):
        return [convert_objectid_to_str(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj

@app.route('/')
def home():
    return '🏠 Pill Dispenser Flask Server is Running!'

@app.route('/get-prescription', methods=['POST'])
def get_prescription():
    try:
        data = request.get_json()
        patient_id = data.get('patientId')

        if not patient_id:
            return jsonify({"error": "Patient ID (codeId) is required"}), 400

        if not re.fullmatch(r'[a-zA-Z0-9]{7}', patient_id):
            return jsonify({"error": "Invalid patientId format"}), 400

        prescription = collection.find_one({"codeId": patient_id})

        if not prescription:
            return jsonify({"error": "No prescription found for this patient ID"}), 404

        prescription = convert_objectid_to_str(prescription)

        medicines = prescription.get("medicines", [])
        if isinstance(medicines, str):
            try:
                medicines = json.loads(medicines)
            except json.JSONDecodeError:
                return jsonify({"error": "Malformed medicines field in DB"}), 500

        if not isinstance(medicines, list):
            return jsonify({"error": "Invalid medicines format in DB"}), 500

        prescription["medicines"] = medicines

        tablet_codes = []
        for med in medicines:
            med_name = med.get("name")
            code = tablet_mapping.get(med_name)
            if code:
                tablet_codes.append(code)
            else:
                print(f"⚠️ Unmapped medicine: '{med_name}'")

        if not tablet_codes:
            return jsonify({"error": "No matching tablets found in mapping"}), 404

        

        return jsonify({
            "status": "success",
            "tablets": tablet_codes,
            "prescription": prescription
        })

    except Exception as e:
        print("❌ Unexpected error:", e)
        return jsonify({"error": "Server error occurred"}), 500

@app.route('/send-to-arduino', methods=['POST'])
async def send_to_arduino():
    try:
        data = request.get_json()
        patient_id = data.get('patientId')

        if not patient_id:
            return jsonify({"error": "Patient ID (codeId) is required"}), 400

        if not re.fullmatch(r'[a-zA-Z0-9]{7}', patient_id):
            return jsonify({"error": "Invalid patientId format"}), 400

        prescription = collection.find_one({"codeId": patient_id})

        if not prescription:
            return jsonify({"error": "No prescription found for this patient ID"}), 404

        prescription = convert_objectid_to_str(prescription)

        medicines = prescription.get("medicines", [])
        if isinstance(medicines, str):
            try:
                medicines = json.loads(medicines)
            except json.JSONDecodeError:
                return jsonify({"error": "Malformed medicines field in DB"}), 500

        if not isinstance(medicines, list):
            return jsonify({"error": "Invalid medicines format in DB"}), 500

        prescription["medicines"] = medicines

        tablet_codes = []
        for med in medicines:
            med_name = med.get("name")
            code = tablet_mapping.get(med_name)
            if code:
                tablet_codes.append(code)
            else:
                print(f"⚠️ Unmapped medicine: '{med_name}'")

        if not tablet_codes:
            return jsonify({"error": "No matching tablets found in mapping"}), 404
        try:
            to_send = ",".join(tablet_codes) + "\n"
            print(f"➡️ Sending to Arduino: {to_send.strip()}")
            arduino.write(to_send.encode())

            #  Wait for Arduino to process and respond
            timeout = 30  # maximum wait time in seconds
            start_time = time.time()

            # Wait until there's data available or timeout
            while arduino.in_waiting == 0 and (time.time() - start_time) < timeout:
                time.sleep(0.1)  # check every 100ms

            # Now collect all responses
            time.sleep(5)
            responses = []
            while arduino.in_waiting:
                response = arduino.readline().decode().strip()
                responses.append(response)
                print("⬅️ Arduino response:", response)

            return jsonify({
                "status": "sent",
                "sentCodes": tablet_codes,
                "arduinoResponse": responses
            })

        except Exception as e:
            print("❌ Arduino communication error:", e)
            return jsonify({"error": "Failed to communicate with Arduino"}), 500

    except Exception as e:
        print("❌ Unexpected error:", e)
        return jsonify({"error": "Server error occurred"}), 500

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
