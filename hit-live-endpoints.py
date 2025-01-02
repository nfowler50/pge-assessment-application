import requests

# Get user input for URL
base_url = input("Enter your base url: ")
# If assessor copies URL from ALB console it will not have "http://"" prefix, so add it here
base_url = base_url if base_url.startswith(("http://", "https://")) else "http://" + base_url

# Define login credentials
login_data = {
    "username": "demo",
    "password": "password"
}

# Send the login request to obtain the JWT token

login_url = f"{base_url}/login"
login_response = requests.post(login_url, json=login_data)

# Check if the login was successful
if login_response.status_code == 200:
    # Extract the token from the response
    access_token = login_response.json().get("access_token")
    print("Login successful! Access token:", access_token)

    # Prepare the headers with the JWT token for the predict route
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Get user input for model input data
    input_data=input("Enter model input value between 0 and 4: ")

    # Send the request to the predict route
    predict_url = f"{base_url}/predict"
    predict_params = {
        "input": input_data
    }
    
    predict_response = requests.get(predict_url, headers=headers, params=predict_params)

    # Check the response from the predict route
    if predict_response.status_code == 200:
        print("Prediction response:", predict_response.json())
    else:
        print("Failed to get prediction:", predict_response.json())
else:
    print("Login failed:", login_response.json())