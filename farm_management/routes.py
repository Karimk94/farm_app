# farm_management/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Animal, Parentage, BreedingSeason, MatingEvent
from . import db
from .forms import LoginForm, AnimalForm, UserForm, BreedingSeasonForm, MatingEventForm
from .decorators import role_required
from sqlalchemy import or_
from wtforms.validators import DataRequired
import pandas as pd
from datetime import date, datetime

main = Blueprint('main', __name__)

# --- Authentication and Core Routes ---

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            # Update life stages on login
            update_all_life_stages()
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', title='Sign In', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    active_statuses = ['Active', 'Pregnant', 'Lactating']
    stats = {
        'total_animals': Animal.query.filter(Animal.animal_status.in_(active_statuses)).count(),
        'total_sheep': Animal.query.filter(Animal.species == 'sheep', Animal.animal_status.in_(active_statuses)).count(),
        'total_goats': Animal.query.filter(Animal.species == 'goat', Animal.animal_status.in_(active_statuses)).count(),
        'recently_added': Animal.query.order_by(Animal.created_at.desc()).limit(5).all()
    }
    return render_template('dashboard.html', stats=stats)


# --- Animal Management ---

@main.route('/animals')
@login_required
def list_animals():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    animals_query = Animal.query
    if query:
        search_term = f"%{query}%"
        animals_query = animals_query.filter(
            or_(
                Animal.tag_id.ilike(search_term),
                Animal.name.ilike(search_term),
                Animal.species.ilike(search_term),
                Animal.life_stage.ilike(search_term),
                Animal.animal_status.ilike(search_term)
            )
        )
    animals = animals_query.order_by(Animal.tag_id).paginate(page=page, per_page=15)
    return render_template('animals.html', animals=animals, query=query)

@main.route('/animal/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_user')
def add_animal():
    form = AnimalForm()
    form.sire_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='male').all()]
    form.dam_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='female').all()]
    if form.validate_on_submit():
        new_animal = Animal(
            tag_id=form.tag_id.data,
            name=form.name.data,
            species=form.species.data,
            gender=form.gender.data,
            date_of_birth=form.date_of_birth.data,
            animal_status=form.animal_status.data,
            notes=form.notes.data,
            created_by_id=current_user.id
        )
        new_animal.calculate_life_stage()
        db.session.add(new_animal)
        db.session.commit()
        if form.sire_id.data and form.sire_id.data != '0':
            sire_parentage = Parentage(child_id=new_animal.id, parent_id=int(form.sire_id.data), parent_type='sire')
            db.session.add(sire_parentage)
        if form.dam_id.data and form.dam_id.data != '0':
            dam_parentage = Parentage(child_id=new_animal.id, parent_id=int(form.dam_id.data), parent_type='dam')
            db.session.add(dam_parentage)
        db.session.commit()
        flash(f'Animal {new_animal.tag_id} has been added.', 'success')
        return redirect(url_for('main.list_animals'))
    return render_template('animal_form.html', title='Add Animal', form=form, legend='New Animal')

@main.route('/animal/<int:animal_id>')
@login_required
def animal_detail(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    return render_template('animal_detail.html', animal=animal)

@main.route('/animal/<int:animal_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_user')
def edit_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    form = AnimalForm(obj=animal)
    
    # Filter dropdowns for age validation
    if animal.date_of_birth:
        form.sire_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter(Animal.gender=='male', Animal.id != animal_id, Animal.date_of_birth < animal.date_of_birth).all()]
        form.dam_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter(Animal.gender=='female', Animal.id != animal_id, Animal.date_of_birth < animal.date_of_birth).all()]
    else:
        form.sire_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='male').filter(Animal.id != animal_id).all()]
        form.dam_id.choices = [('0', 'Unknown')] + [(str(a.id), f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='female').filter(Animal.id != animal_id).all()]


    if form.validate_on_submit():
        animal.tag_id = form.tag_id.data
        animal.name = form.name.data
        animal.species = form.species.data
        animal.gender = form.gender.data
        animal.date_of_birth = form.date_of_birth.data
        animal.animal_status = form.animal_status.data
        animal.notes = form.notes.data
        animal.calculate_life_stage()
        
        # --- ROBUST PARENTAGE LOGIC (UPDATE/CREATE/DELETE) ---
        # Handle Sire (Father)
        new_sire_id = int(form.sire_id.data) if form.sire_id.data and form.sire_id.data.isdigit() else 0
        sire_link = Parentage.query.filter_by(child_id=animal.id, parent_type='sire').first()

        if new_sire_id > 0:
            if sire_link:
                sire_link.parent_id = new_sire_id
            else:
                db.session.add(Parentage(child_id=animal.id, parent_id=new_sire_id, parent_type='sire'))
        elif sire_link:
            db.session.delete(sire_link)

        # Handle Dam (Mother)
        new_dam_id = int(form.dam_id.data) if form.dam_id.data and form.dam_id.data.isdigit() else 0
        dam_link = Parentage.query.filter_by(child_id=animal.id, parent_type='dam').first()

        if new_dam_id > 0:
            if dam_link:
                dam_link.parent_id = new_dam_id
            else:
                db.session.add(Parentage(child_id=animal.id, parent_id=new_dam_id, parent_type='dam'))
        elif dam_link:
            db.session.delete(dam_link)
        
        db.session.commit()
        flash(f'Animal {animal.tag_id} has been updated successfully.', 'success')
        return redirect(url_for('main.animal_detail', animal_id=animal.id))
    
    # This block populates the form on a GET request
    elif request.method == 'GET':
        sire = animal.get_sire()
        dam = animal.get_dam()
        form.sire_id.data = str(sire.id) if sire else '0'
        form.dam_id.data = str(dam.id) if dam else '0'

    return render_template('animal_form.html', title='Edit Animal', form=form, legend=f'Edit {animal.tag_id}')

@main.route('/animal/<int:animal_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_animal(animal_id):
    animal = Animal.query.get_or_404(animal_id)
    db.session.delete(animal)
    db.session.commit()
    flash(f'Animal {animal.tag_id} has been deleted.', 'success')
    return redirect(url_for('main.list_animals'))

# --- Genealogy and Compatibility ---

@main.route('/api/check_compatibility')
@login_required
def check_breeding_compatibility():
    sire_id = request.args.get('sire_id', type=int)
    dam_id = request.args.get('dam_id', type=int)
    if not sire_id or not dam_id:
        return jsonify({'error': 'Missing sire_id or dam_id'}), 400
    sire = Animal.query.get(sire_id)
    dam = Animal.query.get(dam_id)
    if not sire or not dam:
        return jsonify({'error': 'Sire or Dam not found'}), 404
    sire_offspring_ids = {p.child_id for p in sire.children}
    if dam_id in sire_offspring_ids:
        return jsonify({
            'is_compatible': False,
            'message': f'Inbreeding Risk: The selected dam ({dam.tag_id}) is a direct offspring of the sire ({sire.tag_id}).'
        })
    return jsonify({'is_compatible': True})

# --- Breeding Management ---

@main.route('/breeding')
@login_required
def list_seasons():
    seasons = BreedingSeason.query.order_by(BreedingSeason.start_date.desc()).all()
    return render_template('breeding_seasons.html', seasons=seasons)

@main.route('/breeding/season/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_user')
def add_season():
    form = BreedingSeasonForm()
    if form.validate_on_submit():
        new_season = BreedingSeason(name=form.name.data, start_date=form.start_date.data, end_date=form.end_date.data, notes=form.notes.data)
        db.session.add(new_season)
        db.session.commit()
        flash('New breeding season has been added.', 'success')
        return redirect(url_for('main.list_seasons'))
    return render_template('season_form.html', form=form, legend='Add New Breeding Season')

@main.route('/breeding/season/<int:season_id>')
@login_required
def season_detail(season_id):
    season = BreedingSeason.query.get_or_404(season_id)
    return render_template('season_detail.html', season=season)

@main.route('/breeding/season/<int:season_id>/add_event', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_user')
def add_mating_event(season_id):
    season = BreedingSeason.query.get_or_404(season_id)
    form = MatingEventForm(season=season)
    form.sire_id.choices = [(a.id, f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='male').all()]
    form.ewe_id.choices = [(a.id, f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='female').all()]
    if form.validate_on_submit():
        event = MatingEvent(
            season_id=season.id,
            ewe_id=form.ewe_id.data,
            sire_id=form.sire_id.data,
            exposure_date=form.exposure_date.data,
            scan_date=form.scan_date.data,
            scan_result=form.scan_result.data,
            expected_due_date=form.expected_due_date.data
        )
        if event.scan_result and event.scan_result != 'Empty':
            ewe = Animal.query.get(event.ewe_id)
            ewe.animal_status = 'Pregnant'
        db.session.add(event)
        db.session.commit()
        flash('Mating event has been recorded.', 'success')
        return redirect(url_for('main.season_detail', season_id=season.id))
    return render_template('mating_event_form.html', form=form, season=season, legend='Record Mating Event')

@main.route('/breeding/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_user')
def edit_mating_event(event_id):
    event = MatingEvent.query.get_or_404(event_id)
    form = MatingEventForm(obj=event, season=event.season)
    form.sire_id.choices = [(a.id, f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='male').all()]
    form.ewe_id.choices = [(a.id, f"{a.tag_id} - {a.name}") for a in Animal.query.filter_by(gender='female').all()]
    if form.validate_on_submit():
        event.ewe_id = form.ewe_id.data
        event.sire_id = form.sire_id.data
        event.exposure_date = form.exposure_date.data
        event.scan_date = form.scan_date.data
        event.scan_result = form.scan_result.data
        event.expected_due_date = form.expected_due_date.data
        
        ewe = Animal.query.get(event.ewe_id)
        if event.scan_result and event.scan_result != 'Empty':
            ewe.animal_status = 'Pregnant'
        elif ewe.animal_status == 'Pregnant': 
            ewe.animal_status = 'Active'

        db.session.commit()
        flash('Mating event has been updated.', 'success')
        return redirect(url_for('main.season_detail', season_id=event.season_id))
    return render_template('mating_event_form.html', form=form, season=event.season, legend='Edit Mating Event')

@main.route('/breeding/event/<int:event_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_mating_event(event_id):
    event = MatingEvent.query.get_or_404(event_id)
    season_id = event.season_id
    db.session.delete(event)
    db.session.commit()
    flash('Mating event has been deleted.', 'success')
    return redirect(url_for('main.season_detail', season_id=season_id))

# --- User Management ---

@main.route('/admin/users')
@login_required
@role_required('admin')
def list_users():
    users = User.query.all()
    return render_template('users.html', users=users)

@main.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    form = UserForm()
    form.password.validators.insert(0, DataRequired())
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('New user has been created.', 'success')
        return redirect(url_for('main.list_users'))
    return render_template('user_form.html', title='Add User', form=form, legend='New User')

@main.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('User has been updated.', 'success')
        return redirect(url_for('main.list_users'))
    return render_template('user_form.html', title='Edit User', form=form, legend=f'Edit {user.username}')

@main.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('main.list_users'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User has been deleted.', 'success')
    return redirect(url_for('main.list_users'))

# --- Data Import ---

@main.route('/admin/import', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def import_data():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected for upload.', 'warning')
            return redirect(request.url)
        if file and (file.filename.lower().endswith('.csv') or file.filename.lower().endswith('.xlsx')):
            try:
                if file.filename.lower().endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                
                df.columns = [str(col).strip().lower() for col in df.columns]
                
                required_cols = {'tag', 'sex'}
                if not required_cols.issubset(df.columns):
                    flash(f"File must contain the following columns: {', '.join(required_cols)}.", 'danger')
                    return redirect(request.url)
                
                new_animals_count, updated_parents_count = 0, 0
                
                # First pass: Create animals
                for _, row in df.iterrows():
                    tag_id = str(row['tag']).strip()
                    if not tag_id or Animal.query.filter_by(tag_id=tag_id).first():
                        continue
                    
                    gender = 'male' if str(row.get('sex', '')).strip().upper() == 'M' else 'female'
                    dob_str = str(row.get('dob', '')).strip()
                    dob = pd.to_datetime(dob_str, errors='coerce').date() if dob_str else None

                    animal = Animal(
                        tag_id=tag_id, 
                        name=str(row.get('name', '')).strip() or None, 
                        gender=gender,
                        date_of_birth=dob, 
                        species='sheep', 
                        created_by_id=current_user.id
                    )
                    animal.calculate_life_stage()
                    db.session.add(animal)
                    new_animals_count += 1
                db.session.commit()

                # Second pass: Link parents
                for _, row in df.iterrows():
                    child_tag = str(row.get('tag', '')).strip()
                    child = Animal.query.filter_by(tag_id=child_tag).first()
                    if not child: continue

                    sire_tag = str(row.get('sire', '')).strip()
                    if sire_tag and pd.notna(sire_tag) and not child.get_sire():
                        sire = Animal.query.filter_by(tag_id=sire_tag).first()
                        if sire:
                            db.session.add(Parentage(child_id=child.id, parent_id=sire.id, parent_type='sire'))
                            updated_parents_count += 1
                    
                    dam_tag = str(row.get('dam', '')).strip()
                    if dam_tag and pd.notna(dam_tag) and not child.get_dam():
                        dam = Animal.query.filter_by(tag_id=dam_tag).first()
                        if dam:
                            db.session.add(Parentage(child_id=child.id, parent_id=dam.id, parent_type='dam'))
                            updated_parents_count += 1
                
                db.session.commit()
                flash(f'Import successful! Added {new_animals_count} new animals and linked {updated_parents_count} parent relationships.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred during import: {e}', 'danger')
            return redirect(url_for('main.list_animals'))
    return render_template('import_data.html')

# --- Utility and Error Handlers ---

def update_all_life_stages():
    """Function to recalculate life stage for all animals."""
    try:
        all_animals = Animal.query.all()
        for animal in all_animals:
            animal.calculate_life_stage()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating life stages: {e}")

@main.app_errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

