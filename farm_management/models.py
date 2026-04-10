# farm_management/models.py
from . import db
from flask_login import UserMixin
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='readonly') # 'admin', 'super_user', 'readonly'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Animal(db.Model):
    """Animal model to store details about each farm animal."""
    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    species = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date)
    life_stage = db.Column(db.String(20), default='Unknown') 
    animal_status = db.Column(db.String(20), default='Active')
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_by = db.relationship('User')

    # Relationships for parentage
    children = db.relationship('Parentage', foreign_keys='Parentage.parent_id', backref='parent', lazy=True, cascade="all, delete-orphan")
    parents = db.relationship('Parentage', foreign_keys='Parentage.child_id', backref='child', lazy=True, cascade="all, delete-orphan")
    
    # Relationships for breeding events
    mating_events_as_sire = db.relationship('MatingEvent', foreign_keys='MatingEvent.sire_id', backref='sire', lazy='dynamic')
    mating_events_as_ewe = db.relationship('MatingEvent', foreign_keys='MatingEvent.ewe_id', backref='ewe', lazy='dynamic')


    def get_sire(self):
        for p in self.parents:
            if p.parent_type == 'sire':
                return p.parent
        return None

    def get_dam(self):
        for p in self.parents:
            if p.parent_type == 'dam':
                return p.parent
        return None
        
    def calculate_life_stage(self):
        if not self.date_of_birth:
            self.life_stage = 'Unknown'
            return

        today = date.today()
        age_in_months = (today.year - self.date_of_birth.year) * 12 + (today.month - self.date_of_birth.month)

        if self.gender == 'female':
            if 0 <= age_in_months <= 3: self.life_stage = 'Ewe Lamb'
            elif 3 < age_in_months <= 6: self.life_stage = 'Growing Ewe'
            elif 6 < age_in_months <= 12: self.life_stage = 'Gimmer'
            elif age_in_months > 12: self.life_stage = 'Breeding Ewe'
            else: self.life_stage = 'Unknown'
        elif self.gender == 'male':
            if 0 <= age_in_months <= 3: self.life_stage = 'Ram Lamb'
            elif 3 < age_in_months <= 12: self.life_stage = 'Growing Ram'
            elif age_in_months > 12: self.life_stage = 'Breeding Ram'
            else: self.life_stage = 'Unknown'
        else: self.life_stage = 'Unknown'

    def __repr__(self):
        return f'<Animal {self.tag_id} ({self.name})>'

class Parentage(db.Model):
    """Association table to link animals to their parents."""
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('animal.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('animal.id'), nullable=False)
    parent_type = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<Parentage Child:{self.child_id} Parent:{self.parent_id}>'

# --- NEW MODELS FOR BREEDING MANAGEMENT ---

class BreedingSeason(db.Model):
    """Groups mating events into a specific period (e.g., Spring 2025)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    # Relationship to all mating events within this season
    events = db.relationship('MatingEvent', backref='season', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<BreedingSeason {self.name}>'

class MatingEvent(db.Model):
    """Records a specific instance of a sire being exposed to a ewe."""
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('breeding_season.id'), nullable=False)
    ewe_id = db.Column(db.Integer, db.ForeignKey('animal.id'), nullable=False)
    sire_id = db.Column(db.Integer, db.ForeignKey('animal.id'), nullable=False)
    
    exposure_date = db.Column(db.Date, nullable=False) # Date ewe was put with sire
    scan_date = db.Column(db.Date)
    scan_result = db.Column(db.String(50)) # e.g., 'Single', 'Twins', 'Empty'
    expected_due_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<MatingEvent Ewe:{self.ewe_id} with Sire:{self.sire_id}>'

