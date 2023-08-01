token = ""

if token == "":
    print("Edit headers.py and add the authorization token")
    exit(0)

headers= {
    "origin": "https://garlic-bread.reddit.com",
    "referer": "https://garlic-bread.reddit.com/",
    "authorization": f"Bearer {token}",
    "apollographql-client-name": "garlic-bread",
    "Content-Type": "application/json",
}