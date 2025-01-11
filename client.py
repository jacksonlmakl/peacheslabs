import requests

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None

    def register_user(self, email, username, password):
        url = f"{self.base_url}/register"
        payload = {
            "email": email,
            "username": username,
            "password": password
        }
        response = requests.post(url, json=payload)
        print("Register Response:", response.status_code, response.json())
        return response

    def login_user(self, username, password):
        url = f"{self.base_url}/login"
        payload = {
            "username": username,
            "password": password
        }
        response = requests.post(url, json=payload)
        print("Login Response:", response.status_code, response.json())
        if response.status_code == 200:
            self.token = response.json().get("token")
        return self.token

    def access_protected_endpoint(self):
        if not self.token:
            print("No token available. Please log in first.")
            return None

        url = f"{self.base_url}/protected"
        headers = {
            "Authorization": self.token
        }
        response = requests.get(url, headers=headers)
        print("Protected Endpoint Response:", response.status_code, response.json())
        return response

def main():
    base_url = "http://127.0.0.1:5001"
    client = APIClient(base_url)

    # Sample user details
    email = "test@example.com"
    username = "testuser2"
    password = "password1232"

    # Step 1: Register a new user
    client.register_user(email, username, password)

    # Step 2: Log in to get a token
    token = client.login_user(username, password)
    if not token:
        print("Login failed. Exiting.")
        return

    # Step 3: Access the protected endpoint with the token
    client.access_protected_endpoint()

if __name__ == "__main__":
    main()
