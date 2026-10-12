import requests

r = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "lucia", "password": "changeme123"},
)

if r.status_code != 200:
    print(f"Login failed: {r.status_code}")
    print(r.text)
else:
    data = r.json()
    print("TOKEN_START")
    print(data["access_token"])
    print("TOKEN_END")
    print(f"\nname: {data['name']}")
    print(f"role: {data['role']}")