# run.py
# This is the main entry point to start the Flask application.
# To run the application:
# 1. Make sure you have all packages from requirements.txt installed.
# 2. Run this script from your terminal: python run.py
# 3. Open your web browser and go to http://127.0.0.1:5000

from farm_management import create_app

app = create_app()

if __name__ == '__main__':
    # The debug=True flag allows for live reloading and provides detailed error pages.
    # It should be set to False in a production environment.
    # Bind to all network interfaces so other devices on the same Wi-Fi/hotspot can reach it.
    app.run(debug=True, host='0.0.0.0', port=5000)

