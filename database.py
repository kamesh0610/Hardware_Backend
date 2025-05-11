from pymongo import MongoClient

# Connect to MongoDB Atlas
client = MongoClient("mongodb+srv://kameshoffical06:kamesh1906@doctor.k2n8v.mongodb.net/?retryWrites=true&w=majority")
db = client.pill_dispenser
prescriptions = db.prescriptions

def get_prescription_by_code(code):
    doc = prescriptions.find_one({"codeId": code})
    if not doc:
        return None
    return {
        "patient": doc.get("patientName"),
        "medicines": [
            {"name": med["name"], "quantity": med["noOfTablets"]}
            for med in doc.get("medicines", [])
        ]
    }