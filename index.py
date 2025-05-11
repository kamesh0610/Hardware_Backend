from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)

# Allow CORS for all domains
CORS(app, resources={r"/*": {"origins": "*"}})

# Optionally add CORS headers after each request (browser compatibility)
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response

# Connect to MongoDB Atlas
client = MongoClient(
    "mongodb+srv://kameshoffical06:kamesh1906@doctor.k2n8v.mongodb.net/?retryWrites=true&w=majority&appName=Doctor",
    server_api=ServerApi('1')
)

# Test connection
try:
    client._connect()
except Exception as e:
    print("MongoDB connection error:", e)

# Database and collection
db = client["pillDispenser"]
collection = db["prescriptions"]

@app.route('/')
def home():
    return 'Home Page Route'

# Endpoint to get prescription
@app.route('/get-prescription', methods=['POST'])
def get_prescription():
    data = request.get_json()
    patient_id = data.get('patientId')

    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    prescription = collection.find_one({"codeId": patient_id}, projection={"_id": 0})
    
    if prescription and "medicines" in prescription:
        for med in prescription["medicines"]:
            med.pop("_id", None)

    if not prescription:
        return jsonify({"error": "No prescription found for this patient ID"}), 404

    return jsonify(prescription)

# Run the Flask server on all network interfaces so other devices can access it
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
