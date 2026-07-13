import requests, json

url = "http://127.0.0.1:5001/chat"
payload = {
    "messages": [
        {"role": "user", "content": "graph of medicine inventory"}
    ],
    "language": "EN"
}

headers = {"Content-Type": "application/json"}
response = requests.post(url, headers=headers, json=payload)
print("Response Status Code:", response.status_code)
print("Raw Response Output:")
print(response.text)
