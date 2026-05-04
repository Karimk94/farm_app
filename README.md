# Farm Management System — Backend (Flask)

This is the Flask-based backend for your farm management system. It provides a web interface for managing farm operations and serves as the API for the mobile app.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Setup](#2-project-setup)
3. [Running the Application](#3-running-the-application)
4. [Setting Up Public Access](#4-setting-up-public-access)
5. [Database](#5-database)
6. [Deployment](#6-deployment)
7. [API Endpoints](#7-api-endpoints)
8. [Troubleshooting](#8-troubleshooting)

## 1. Prerequisites

- Python 3.8 or higher
- Git

## 2. Project Setup

1. Clone or navigate to the project directory:
   ```
   cd D:\projects\farm_app
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## 3. Running the Application

### Local Development

1. Activate the virtual environment:
   ```
   .venv\Scripts\activate  # On Windows
   ```

2. Run the application:
   ```
   python run.py
   ```

3. Open your browser and go to `http://127.0.0.1:5000`

### Public Access (for Mobile App)

To make the backend accessible from the mobile app:

1. **Start the Flask server** (in one terminal):
   ```
   cd D:\projects\farm_app
   .venv\Scripts\activate
   python run.py
   ```

2. **Start the Serveo tunnel** (in another terminal):
   ```
   ssh -R 80:localhost:5000 serveo.net
   ```
   - This gives you: `https://3d72f62e66a26bed-5-30-201-24.serveousercontent.com`
   - Keep both terminals running

3. **Test the public URL**: Visit `https://3d72f62e66a26bed-5-30-201-24.serveousercontent.com` in your browser

The mobile app should use: `https://3d72f62e66a26bed-5-30-201-24.serveousercontent.com/login`

## 4. Setting Up Public Access

To make the backend accessible from the mobile app over the internet, use Cloudflare Tunnel (free alternative to ngrok):

### Install Cloudflare Tunnel

1. Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/
2. Or using Chocolatey: `choco install cloudflared`

### Setup Tunnel

1. Authenticate with Cloudflare:
   ```
   cloudflared tunnel login
   ```
   - This opens your browser for login (create a free Cloudflare account if needed).

2. Create a tunnel:
   ```
   cloudflared tunnel create farm-backend
   ```

3. Start the tunnel (keep this running):
   ```
   cloudflared tunnel run --url http://localhost:5000 farm-backend
   ```
   - This provides a URL like `https://abc123.cfargotunnel.com`

4. Update the mobile app's `.env` file with this URL.

### Alternative: Serveo (Simple SSH-based tunneling)

Serveo provides free tunneling via SSH.

1. Generate an SSH key if you have not already:
   ```bash
   ssh-keygen
   ```
   Accept the default path and press Enter through the prompts.

2. Start the tunnel with your reserved subdomain:
   ```bash
   ssh -R farmapp:80:localhost:5000 serveo.net
   ```
   This should map your app to `https://farmapp.serveousercontent.com`.

If Serveo still shows a random URL such as `https://0a996384d7124b3b-86-98-11-20.serveousercontent.com`, then your key has not been registered for the reserved name yet, the key was registered under a different Serveo account, or the SSH session is still using an old or wrong key.

If you already registered the key, do this:

1. Close the current tunnel session (Ctrl+C).
2. Verify the public key fingerprint from your local file:
   ```bash
   ssh-keygen -E sha256 -lf "%USERPROFILE%\.ssh\id_ed25519.pub"
   ```
3. Confirm that fingerprint matches the one shown in the Serveo console.
4. Restart the tunnel with the same registered key:
   ```bash
   ssh -i "%USERPROFILE%\.ssh\id_ed25519" -o IdentitiesOnly=yes -R farmapp:80:localhost:5000 serveo.net
   ```

If the issue persists, run the connection with verbose output:

```bash
ssh -v -i "%USERPROFILE%\.ssh\id_ed25519" -o IdentitiesOnly=yes -R farmapp:80:localhost:5000 serveo.net
```

Look for these lines in the output:
- `Offering public key: ...` (should show your registered key)
- `Authenticated to serveo.net using "keyboard-interactive"` or `publickey`
- `remote forward success for: listen farmapp:80`

If Serveo still asks you to register the key, then the key is not recognized by the Serveo account you are connecting with. Check that you registered it under the same Google/GitHub account and the same fingerprint, then try again.

### Manual Key Registration in Serveo Console

If the automatic registration link doesn't work or you need to add the key manually:

1. Go to https://console.serveo.net
2. Log in with your Google or GitHub account (use the same account each time)
3. Go to the "SSH Keys" section
4. Click "Add SSH Key" or "Add Key"
5. Copy your public key content:
   ```bash
   type "%USERPROFILE%\.ssh\id_ed25519.pub"
   ```
   This will output something like:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGmJy8HqEXAMPLEKEYCONTENT kwahe@Karim
   ```
6. Paste the **entire line** (starting with `ssh-ed25519`) into the key field
7. Click Save or Add
8. Go to "Reserved Names" section
9. Click "Reserve Name" or "Add Reserved Name"
10. Enter `farmapp` as the name
11. Click Reserve or Save
12. Restart the SSH tunnel:
    ```bash
    ssh -i "%USERPROFILE%\.ssh\id_ed25519" -o IdentitiesOnly=yes -R farmapp:80:localhost:5000 serveo.net
    ```

If you see "Key already exists" when adding, it means the key is already registered - just proceed to reserve the name.

Keep this command running to maintain the tunnel.

> Note: Serveo requires an SSH key for fixed hostnames. After registering the public key at https://console.serveo.net, restart the SSH tunnel so Serveo can use that key for `farmapp`.

## 5. Database

The application uses SQLite (`farm_db.sqlite`) for data storage. The database is created automatically when you first run the app.

## 6. Deployment

For production deployment:

1. Set `app.run(debug=False)` in `run.py`
2. Use a production WSGI server like Gunicorn
3. Set up proper environment variables
4. Use a reverse proxy like Nginx

## 7. API Endpoints

The application provides standard web routes. All endpoints are served as HTML pages that work with the mobile app's WebView.

## 8. Troubleshooting

- **Module not found**: Ensure virtual environment is activated and dependencies are installed.
- **Port already in use**: Kill the process using port 5000 or change the port in `run.py`.
- **Database issues**: Delete `farm_db.sqlite` and restart (data will be lost).
- **Tunnel issues**: Ensure Cloudflare login is completed and tunnel is running.</content>
<parameter name="filePath">d:\projects\farm_app\README.md