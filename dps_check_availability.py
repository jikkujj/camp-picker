import requests
from datetime import datetime
import time

# ================= CONFIGURATION =================
email = 'jikku.joseph@gmail.com'
first_name = 'Jikku'
last_name = 'John'
date_of_birth = '01/18/1983'
last4ssn = '9146'
zipcode = '75036'
type_id = 81  
distance = 50 
check_interval = 60 

BASE_URL = "https://apptapi.txdpsscheduler.com/api"

# These headers are the "secret sauce" to avoid the 401 error.
# They make the server think you are using the actual website.
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://www.txdpsscheduler.com",
    "Referer": "https://www.txdpsscheduler.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site"
}

# Current date to beat (starting with next year as you are booking from scratch)
cur_appointment_date = datetime(2027, 1, 1)

def login():
    global cur_appointment_date
    print("Logging in via Eligibility check...")
    
    payload = {
        "FirstName": first_name,
        "LastName": last_name,
        "DateOfBirth": date_of_birth,
        "LastFourDigitsSsn": last4ssn 
    }
    
    # Use json=payload to ensure it sends a proper JSON object, NOT a string.
    res = requests.post(f"{BASE_URL}/Eligibility", json=payload, headers=headers)
    
    if res.status_code == 200:
        print("Login successful!")
        # Check if you already have an appointment to set a 'date to beat'
        booking_res = requests.post(f"{BASE_URL}/Booking", json=payload, headers=headers)
        if booking_res.status_code == 200:
            appointments = booking_res.json()
            if appointments:
                dt_str = appointments[0]['BookingDateTime']
                cur_appointment_date = datetime.strptime(dt_str[:10], "%Y-%m-%d")
                print(f"Current appointment: {dt_str}")
        return True
    
    print(f"Login Failed ({res.status_code}): {res.text}")
    return False

def check_availability():
    search_payload = {
        "TypeId": type_id,
        "ZipCode": zipcode,
        "CityName": "",
        "PreferredDay": 0
    }
    
    res = requests.post(f"{BASE_URL}/AvailableLocation", json=search_payload, headers=headers)
    if res.status_code == 200:
        locations = res.json()
        nearby = [l for l in locations if l['Distance'] <= distance]
        nearby.sort(key=lambda l: datetime.strptime(l['NextAvailableDate'], '%m/%d/%Y'))

        found = False
        for loc in nearby:
            avail_date = datetime.strptime(loc['NextAvailableDate'], '%m/%d/%Y')
            if avail_date < cur_appointment_date:
                print(f"!!! EARLIER SLOT: {loc['Name']} on {loc['NextAvailableDate']} ({loc['Distance']} miles)")
                found = True
        if not found:
            print(f"No dates earlier than {cur_appointment_date.date()} found.")
    else:
        print(f"Search failed with status {res.status_code}")

if __name__ == "__main__":
    if login():
        count = 1
        while True:
            print(f"\n--- Search #{count} at {datetime.now().strftime('%H:%M:%S')} ---")
            try:
                check_availability()
            except Exception as e:
                print(f"Error: {e}")
            count += 1
            time.sleep(check_interval)