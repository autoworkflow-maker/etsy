import requests

ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
KEYSTRING = "YOUR_KEYSTRING"
SHARED_SECRET = "YOUR_SHARED_SECRET"
SHOP_ID = "YOUR_SHOP_ID"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "x-api-key": f"{KEYSTRING}:{SHARED_SECRET}"
}

url = f"https://openapi.etsy.com/v3/application/shops/{SHOP_ID}"

response = requests.get(url, headers=headers)

print("Status:", response.status_code)
print(response.text)
