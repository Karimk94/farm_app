# farm_management/__init__.py
import os
from flask import Flask, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# Initialize the database extension
db = SQLAlchemy()# farm_management/__init__.py
# This file is ESSENTIAL. It tells Python that the 'farm_management' directory
# should be treated as a package, allowing you to import from its other files.
# Even if this file were empty, its presence is required.

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# Initialize the database extension
db = SQLAlchemy()

def create_app():
    """Create and configure an instance of the Flask application."""
    # The 'template_folder' argument explicitly tells Flask where to find the HTML files.
    app = Flask(__name__, 
                instance_relative_config=True,
                template_folder='templates')
    
    # --- Configuration ---
    app.config['SECRET_KEY'] = 'a-very-secret-key-for-farm-management'
    
    # Set the database URI. It points to 'farm_db.sqlite' in the parent directory (farm_app).
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'farm_db.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    # --- User Loader ---
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # --- Database Initialization ---
    with app.app_context():
        db.create_all()
        
        # Create a default admin user on the first run
        if not User.query.filter_by(username='admin').first():
            print("Creating default admin user...")
            hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin_user = User(
                username='admin',
                email='admin@farm.local',
                password_hash=hashed_password,
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created with username 'admin' and password 'admin123'.")

    return app



def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # --- Configuration ---
    # Use a secret key for session management and security.
    # In a real application, this should be a complex, random string.
    app.config['SECRET_KEY'] = 'a-very-secret-key-for-farm-management'
    
    # Set the database URI. It will point to a file named 'farm_db.sqlite'
    # in the same directory as the application script.
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'farm_db.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'main.login'  # The route to redirect to for login
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized_handler():
        wants_json = request.is_json or 'application/json' in (request.headers.get('Accept') or '')
        if wants_json:
            return jsonify({'error': 'unauthorized', 'message': 'Authentication required.'}), 401
        return redirect(url_for('main.login'))

    # --- User Loader ---
    # This function is used by Flask-Login to load a user from the database.
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    # Register the main blueprint that contains all the application routes.
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # --- Database Initialization ---
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        
        # Create a default admin user on the first run
        if not User.query.filter_by(username='admin').first():
            print("Creating default admin user...")
            # IMPORTANT: Change this password immediately after the first login!
            hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
            admin_user = User(
                username='admin',
                email='admin@farm.local',
                password_hash=hashed_password,
                role='admin'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created with username 'admin' and password 'admin123'.")

    return app

