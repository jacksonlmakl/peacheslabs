import dash
from dash import dcc, html, Input, Output, State
import dash_uploader as du
import requests
import os

# Configure Dash app
app = dash.Dash(__name__)
server = app.server  # For deploying later
app.title = "File Management App"

# Set up Dash Uploader
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
du.configure_upload(app, UPLOAD_FOLDER)

# Base URLs for the APIs
AUTH_URL = "http://127.0.0.1:5001"
UPLOAD_URL = "http://127.0.0.1:5002"

# User token
token = None

# Layout of the Dash app
app.layout = html.Div(
    [
        html.H1("File Management System", style={"textAlign": "center"}),

        html.Div(
            [
                html.H2("Register"),
                dcc.Input(id="register-email", type="email", placeholder="Email", style={"marginRight": "10px"}),
                dcc.Input(id="register-username", type="text", placeholder="Username", style={"marginRight": "10px"}),
                dcc.Input(id="register-password", type="password", placeholder="Password"),
                html.Button("Register", id="register-button", n_clicks=0),
                html.Div(id="register-output", style={"marginTop": "10px", "color": "green"}),
            ],
            style={"marginBottom": "20px"},
        ),

        html.Div(
            [
                html.H2("Login"),
                dcc.Input(id="login-username", type="text", placeholder="Username", style={"marginRight": "10px"}),
                dcc.Input(id="login-password", type="password", placeholder="Password"),
                html.Button("Login", id="login-button", n_clicks=0),
                html.Div(id="login-output", style={"marginTop": "10px", "color": "blue"}),
            ],
            style={"marginBottom": "20px"},
        ),

        html.Div(
            [
                html.H2("Upload Files"),
                du.Upload(
                    id="file-uploader",
                    text="Drag and Drop or Click to Upload",
                    max_files=1,
                    max_file_size=1024 * 5,  # 5 MB limit
                ),
                html.Div(id="upload-output", style={"marginTop": "10px", "color": "purple"}),
            ],
            style={"marginBottom": "20px"},
        ),

        html.Div(
            [
                html.H2("Uploaded Files"),
                html.Button("List Files", id="list-files-button", n_clicks=0),
                html.Ul(id="files-list", style={"marginTop": "10px", "color": "brown"}),
            ]
        ),
    ],
    style={"width": "60%", "margin": "auto"},
)

# Callback for registering a new user
@app.callback(
    Output("register-output", "children"),
    Input("register-button", "n_clicks"),
    State("register-email", "value"),
    State("register-username", "value"),
    State("register-password", "value"),
)
def register_user(n_clicks, email, username, password):
    if n_clicks > 0:
        url = f"{AUTH_URL}/register"
        payload = {"email": email, "username": username, "password": password}
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            return "Registration successful!"
        else:
            return f"Registration failed: {response.json().get('message', 'Unknown error')}."
    return ""

# Callback for logging in
@app.callback(
    Output("login-output", "children"),
    Input("login-button", "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
)
def login_user(n_clicks, username, password):
    global token
    if n_clicks > 0:
        url = f"{AUTH_URL}/login"
        payload = {"username": username, "password": password}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            token = response.json().get("token")
            return "Login successful!"
        else:
            return f"Login failed: {response.json().get('message', 'Unknown error')}."
    return ""

@du.callback(
    output=Output("upload-output", "children"),
    id="file-uploader",
)
def upload_file(file_paths):
    """Handle the uploaded file(s) and send them to the API."""
    global token
    if not token:
        return "Please log in to upload files."

    if not file_paths or len(file_paths) == 0:
        return "No file provided."

    # Extract the first file path from the list
    file_path = file_paths[0]  # Dash Uploader always provides a list

    try:
        url = f"{UPLOAD_URL}/upload?token={token}"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "text/plain")}
            response = requests.post(url, files=files)

        if response.status_code == 201:
            return f"File uploaded successfully: {os.path.basename(file_path)}."
        else:
            return f"File upload failed: {response.json().get('message', 'Unknown error')}."
    except Exception as e:
        return f"An error occurred during file upload: {str(e)}."

@app.callback(
    Output("files-list", "children"),
    Input("list-files-button", "n_clicks"),
)
def list_files(n_clicks):
    global token
    if n_clicks > 0:
        if not token:
            return [html.Li("Please log in to view files.")]
        
        url = f"{UPLOAD_URL}/files?token={token}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                files = response.json().get("files", [])
                if not files:
                    return [html.Li("No files uploaded yet.")]
                return [
                    html.Li(f"{file['file_name']} (Uploaded: {file['uploaded_at']})") 
                    for file in files
                ]
            else:
                error_message = response.json().get("error", "Unknown error")
                return [html.Li(f"Failed to retrieve files: {error_message}")]
        except Exception as e:
            return [html.Li(f"An error occurred: {str(e)}")]
    return []


if __name__ == "__main__":
    app.run_server(port="9000",debug=True)
