from flask import Flask, request, jsonify
from pymongo import MongoClient
import serial
import time
import re
from bson import ObjectId

app = Flask(__name__)

# MongoDB connection
client = MongoClient(
    "mongodb+srv://kameshoffical06:kamesh1906@doctor.k2n8v.mongodb.net/?retryWrites=true&w=majority&appName=Doctor"
)
db = client["pillDispenser"]
collection = db["prescriptions"]

# Serial setup (update the port as per your system)
try:
    arduino = serial.Serial('COM6', 9600, timeout=1)  # Change COM port accordingly
    time.sleep(2)  # Wait for Arduino to reset
    print("✅ Arduino connected on COM6")
except Exception as e:
    print(f"❌ Failed to connect to Arduino: {e}")
    arduino = None

# Tablet mapping based on medicine names in DB
tablet_mapping = {
    "Diazepam - 5mg": "T1",
    "Paracetamol - 500mg": "T2",
    "Amoxicillin - 250mg": "T3",
    "Ibuprofen - 400mg": "T4",
    "Azithromycin - 250mg": "T5",
    "Metformin - 500mg": "T6",
    "Amlodipine - 5mg": "T7",
    "Losartan - 50mg": "T8",
}

def convert_objectid_to_str(obj):
    if isinstance(obj, list):
        return [convert_objectid_to_str(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj

@app.route('/')
def home():
    return '🏠 Pill Dispenser Flask Server is Running!'

@app.route('/get-prescription', methods=['POST'])
def get_prescription():
    data = request.get_json()

    # Validate input
    patient_id = data.get('patientId')
    if not patient_id:
        return jsonify({"error": "Patient ID (codeId) is required"}), 400

    # Validate patientId format: exactly 7 alphanumeric chars (adjust pattern as needed)
    if not re.fullmatch(r'[a-zA-Z0-9]{7}', patient_id):
        return jsonify({"error": "Invalid patientId format"}), 400

    # Find prescription by codeId (codeId is a string, not ObjectId)
    prescription = collection.find_one({"codeId": patient_id}, projection={"_id": 0})

    if not prescription:
        return jsonify({"error": "No prescription found for this patient ID"}), 404

    # Convert any ObjectId in the prescription just in case
    prescription = convert_objectid_to_str(prescription)

    # Map medicines to tablet codes
    tablet_codes = []
    for med in prescription.get("medicines", []):
        med_name = med.get("name")
        code = tablet_mapping.get(med_name)
        if code:
            tablet_codes.append(code)
        else:
            print(f"⚠️ Medicine name not in mapping: '{med_name}'")

    if not tablet_codes:
        return jsonify({"error": "No matching tablets found in mapping"}), 404

    # Send tablet codes to Arduino over serial
    if arduino:
        try:
            to_send = ",".join(tablet_codes) + "\n"
            print(f"Sending to Arduino: {to_send.strip()}")
            arduino.write(to_send.encode())

            time.sleep(1)  # Give Arduino some time to respond
            while arduino.in_waiting:
                response = arduino.readline().decode().strip()
                print("Arduino response:", response)

        except Exception as e:
            print("Error communicating with Arduino:", e)

    # Return success response with tablets and prescription data
    return jsonify({
        "status": "success",
        "tablets": tablet_codes,
        "prescription": prescription
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
