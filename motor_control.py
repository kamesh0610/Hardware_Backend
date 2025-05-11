def dispense_medicine(medicines):
    for med in medicines:
        print(f"Dispensing {med['name']} - {med['quantity']} tablets")
        # Add GPIO control logic here for Raspberry Pi