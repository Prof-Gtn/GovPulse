import requests

# Login
r = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "lucia", "password": "changeme123"},
)
token = r.json()["access_token"]

# Test /stories
headers = {"Authorization": f"Bearer {token}"}
r = requests.get("http://localhost:8000/stories", headers=headers)

print(f"GET /stories: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Count: {data['count']}")
    print(f"First headline: {data['stories'][0]['headline']}")
else:
    print(r.text)

# Test /brief/exists
r = requests.get("http://localhost:8000/brief/exists", headers=headers)
print(f"\nGET /brief/exists: {r.status_code}")
print(r.json() if r.status_code == 200 else r.text)

# Test /responses
r = requests.get("http://localhost:8000/responses", headers=headers)
print(f"\nGET /responses: {r.status_code}")
if r.status_code == 200:
    print(f"Response count: {len(r.json()['responses'])}")
else:
    print(r.text)