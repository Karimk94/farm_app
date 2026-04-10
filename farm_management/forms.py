# farm_management/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from .models import User, Animal, BreedingSeason
from datetime import date

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class UserForm(FlaskForm):
    """Form for admins to add or edit users."""
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('readonly', 'Read-Only'), ('super_user', 'Super User'), ('admin', 'Admin')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Save User')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user and (not hasattr(self, 'obj') or not self.obj or self.obj.id != user.id):
            raise ValidationError('This username is already taken.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user and (not hasattr(self, 'obj') or not self.obj or self.obj.id != user.id):
            raise ValidationError('This email address is already in use.')


class AnimalForm(FlaskForm):
    """Form for adding or editing an animal."""
    tag_id = StringField('Tag ID', validators=[DataRequired()])
    name = StringField('Name')
    species = SelectField('Species', choices=[('sheep', 'Sheep'), ('goat', 'Goat'), ('other', 'Other')], validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female')], validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    animal_status = SelectField('Animal Status', 
        choices=[
            ('Active', 'Active'), 
            ('Pregnant', 'Pregnant'), 
            ('Lactating', 'Lactating'),
            ('Sold', 'Sold'), 
            ('Deceased', 'Deceased'),
            ('Slaughtered', 'Slaughtered')
        ], 
        default='Active'
    )
    sire_id = SelectField('Sire (Father)', coerce=str, validators=[Optional()])
    dam_id = SelectField('Dam (Mother)', coerce=str, validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Animal')

    def validate_tag_id(self, tag_id):
        animal = Animal.query.filter_by(tag_id=tag_id.data).first()
        if animal and (not hasattr(self, 'obj') or not self.obj or self.obj.id != animal.id):
            raise ValidationError('This Tag ID is already in use. Please choose a different one.')
    
    def validate_date_of_birth(self, date_of_birth):
        if date_of_birth.data and date_of_birth.data > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

    def validate_sire_id(self, sire_id):
        if hasattr(self, 'obj') and self.obj and sire_id.data == str(self.obj.id):
             raise ValidationError("An animal cannot be its own sire.")
        
        if not self.date_of_birth.data or not sire_id.data or sire_id.data == '0':
            return
        sire = Animal.query.get(int(sire_id.data))
        if sire and sire.date_of_birth and sire.date_of_birth >= self.date_of_birth.data:
            raise ValidationError(f"Sire ({sire.tag_id}) cannot be younger than or born on the same day as the offspring.")

    def validate_dam_id(self, dam_id):
        if hasattr(self, 'obj') and self.obj and dam_id.data == str(self.obj.id):
             raise ValidationError("An animal cannot be its own dam.")

        if not self.date_of_birth.data or not dam_id.data or dam_id.data == '0':
            return
        dam = Animal.query.get(int(dam_id.data))
        if dam and dam.date_of_birth and dam.date_of_birth >= self.date_of_birth.data:
            raise ValidationError(f"Dam ({dam.tag_id}) cannot be younger than or born on the same day as the offspring.")

    def validate_animal_status(self, animal_status):
        if self.gender.data == 'male' and animal_status.data in ['Pregnant', 'Lactating']:
            raise ValidationError("A male animal cannot have the status 'Pregnant' or 'Lactating'.")


class BreedingSeasonForm(FlaskForm):
    """Form for creating a new breeding season."""
    name = StringField('Season Name', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Season')

    def validate_end_date(self, end_date):
        if end_date.data and self.start_date.data and end_date.data < self.start_date.data:
            raise ValidationError('End date cannot be before the start date.')

class MatingEventForm(FlaskForm):
    """Form for recording a mating event."""
    ewe_id = SelectField('Ewe', coerce=int, validators=[DataRequired()])
    sire_id = SelectField('Sire', coerce=int, validators=[DataRequired()])
    exposure_date = DateField('Exposure Date', format='%Y-%m-%d', validators=[DataRequired()])
    scan_date = DateField('Scan Date', format='%Y-%m-%d', validators=[Optional()])
    scan_result = SelectField('Scan Result', 
        choices=[
            ('', 'Not Scanned'), 
            ('Single', 'Single'), 
            ('Twins', 'Twins'),
            ('Triplets', 'Triplets'),
            ('Empty', 'Empty')
        ],
        validators=[Optional()]
    )
    expected_due_date = DateField('Expected Due Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Save Event')
    
    def __init__(self, *args, **kwargs):
        self.season = kwargs.pop('season', None)
        super(MatingEventForm, self).__init__(*args, **kwargs)

    def validate_exposure_date(self, exposure_date):
        if exposure_date.data > date.today():
            raise ValidationError("Exposure date cannot be in the future.")
        if self.season:
            if exposure_date.data < self.season.start_date:
                raise ValidationError(f"Exposure date cannot be before the season start date ({self.season.start_date.strftime('%Y-%m-%d')}).")
            if self.season.end_date and exposure_date.data > self.season.end_date:
                 raise ValidationError(f"Exposure date cannot be after the season end date ({self.season.end_date.strftime('%Y-%m-%d')}).")

    def validate_scan_date(self, scan_date):
        if scan_date.data and self.exposure_date.data and scan_date.data < self.exposure_date.data:
            raise ValidationError("Scan date cannot be before the exposure date.")

    def validate_expected_due_date(self, expected_due_date):
        if expected_due_date.data and self.exposure_date.data and expected_due_date.data < self.exposure_date.data:
            raise ValidationError("Expected due date cannot be before the exposure date.")

    def validate_scan_result(self, scan_result):
        if scan_result.data and not self.scan_date.data:
            raise ValidationError("A scan result can only be recorded if a scan date is also provided.")

    def _is_old_enough(self, animal_dob, event_date):
        if not animal_dob or not event_date:
            return False
        return (event_date.year - animal_dob.year) * 12 + (event_date.month - animal_dob.month) >= 6

    def validate_ewe_id(self, ewe_id):
        ewe = Animal.query.get(ewe_id.data)
        if not ewe: return
        if ewe.gender != 'female':
            raise ValidationError(f"Animal {ewe.tag_id} is a male and cannot be selected as a ewe.")
        inactive_statuses = ['Sold', 'Deceased', 'Slaughtered']
        if ewe.animal_status in inactive_statuses:
            raise ValidationError(f"Ewe {ewe.tag_id} is inactive ({ewe.animal_status}) and cannot be in a mating event.")
        if ewe.animal_status == 'Pregnant':
            if not hasattr(self, 'obj') or not self.obj or self.obj.ewe_id != ewe_id.data:
                raise ValidationError(f"Ewe {ewe.tag_id} is already marked as Pregnant.")
        if not self._is_old_enough(ewe.date_of_birth, self.exposure_date.data):
             raise ValidationError(f"Ewe {ewe.tag_id} is too young for breeding (must be at least 6 months old).")

    def validate_sire_id(self, sire_id):
        sire = Animal.query.get(sire_id.data)
        if not sire: return
        if sire.gender != 'male':
            raise ValidationError(f"Animal {sire.tag_id} is a female and cannot be selected as a sire.")
        inactive_statuses = ['Sold', 'Deceased', 'Slaughtered']
        if sire.animal_status in inactive_statuses:
            raise ValidationError(f"Sire {sire.tag_id} is inactive ({sire.animal_status}) and cannot be in a mating event.")
        if not self._is_old_enough(sire.date_of_birth, self.exposure_date.data):
             raise ValidationError(f"Sire {sire.tag_id} is too young for breeding (must be at least 6 months old).")

