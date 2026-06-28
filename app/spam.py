import requests
import threading

results = []
success = 0
sold_out = 0

def send_request():
    global success, sold_out
    try:
        response = requests.post("http://127.0.0.1:5000/buy", json={"user_id": "nain", "item_id": ["1"]})
        data = response.json()
        print(data)
        if data.get("message") == "success":
            success += 1
        else:
            sold_out += 1
    except Exception as e:
        print("Error:", e)

threads = []
for i in range(20):
    t = threading.Thread(target=send_request)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Success: {success}, Sold Out: {sold_out}")