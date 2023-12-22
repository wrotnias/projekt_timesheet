import random
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'secret_key'  # Klucz sekretny dla Flask-Login
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

# Formularz logowania
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

##################################### MODELE ########################################
# Model użytkownika
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    pesel = db.Column(db.String(11), unique=True, nullable=False)
    service_line = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    username_and_id = db.Column(db.String(100), unique=True, nullable=False)
    campaigns = db.relationship('Campaign', back_populates='user', lazy=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    supervised = db.relationship('User', back_populates='supervisor', foreign_keys=[supervisor_id])
    supervisor = db.relationship('User', back_populates='supervised', remote_side=[id], post_update=True)
# Model kampanii
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, unique=True, nullable=False, default=lambda: random.randint(1000, 9999))
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_work_time = db.Column(db.Float, default=0.0)
    user = db.relationship('User', back_populates='campaigns')
# Model Raportu
class WorkReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hours_worked = db.Column(db.Float, nullable=False)
    minutes_worked = db.Column(db.Float, nullable=False) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)

##################################### LOGOWANIE ########################################
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Tworzenie tabel w bazie danych
with app.app_context():
    db.create_all()
    # Tworzenie admina aby sie zalogowac 
    existing_admin = User.query.filter_by(username_and_id='admin').first()
    if not existing_admin:
        new_user = User(first_name='Admin', last_name='Admin', pesel='12345678902', service_line='IT', username_and_id='admin', supervisor_id='admin', password=generate_password_hash('admin'))
        db.session.add(new_user)
        db.session.commit()

##################################### TRASY ########################################
# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username_and_id=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Nieprawidłowy login lub hasło.', 'danger')

    return render_template('login.html', form=form)

# Wylogowanie
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Strona glowna
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    users = User.query.all()
    campaigns = Campaign.query.filter_by(user_id=current_user.id).all()  # Pobiera kampanie dla aktualnie zalogowanego użytkownika
    if request.method == 'POST':
        for campaign in campaigns:
            work_time = request.form.get(f'work_time_{campaign.id}')
            if work_time:  # Sprawdza, czy pole wprowadzania czasu pracy nie jest puste
                if ':' in work_time:
                    # Wprowadzony czas zawiera godziny i minuty
                    hours, minutes = map(int, work_time.split(':'))
                else:
                    # Wprowadzony czas zawiera tylko godziny
                    hours = int(work_time)
                    minutes = 0
                total_hours = hours + minutes / 60  # Przelicza minuty na godziny - wczesniej przy wprowadzeniu np. 6 traktowalo to jako 6 minut, chcemy zeby to bylo 6 godzin
                campaign.total_work_time += total_hours  # Aktualizuje total_work_time w bazie danych
                db.session.commit()

    # Zwraca odpowiedź dla żądań GET
    return render_template('index.html', users=users, campaigns=campaigns)  # Przekaż kampanie do szablonu

# Dodawanie nowego uzytkownika
from flask import render_template, request, redirect, url_for
@app.route('/add_user_page', methods=['GET', 'POST'])
def add_user_page():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        pesel = request.form.get('pesel')  
        service_line = request.form.get('service_line') 
        password = request.form.get('password') 
        supervisor_id = request.form.get('supervisor') 

        if first_name and last_name and pesel and service_line and password:
            with app.app_context():
                # Tworzy unikalne usernameAndID, uzywane jako login
                username_and_id = f"{first_name}{last_name}{User.query.count() + 1}"
                new_user = User(first_name=first_name, last_name=last_name, pesel=pesel, service_line=service_line, supervisor_id=supervisor_id, password=generate_password_hash(password), username_and_id=username_and_id)  # Uaktualnionee
                db.session.add(new_user)
                db.session.commit()
        return redirect(url_for('index'))
    else:
        # Pobiera wszystkich użytkowników
        users = User.query.all()
        # Przekazuje użytkowników do szablonu z wszystkimi aktywnymi uzytkownikami
        return render_template('add_user.html', users=users)

#Aktualizacja uzytkownika
@app.route('/update_users', methods=['POST'])
def update_users():
    if request.method == 'POST':
        # Pobiera dane z formularza
        for user in User.query.all():
            user.service_line = request.form.get(f'service_line_{user.id}')
            supervisor_id = int(request.form.get(f'supervisor_{user.id}'))
            supervisor = User.query.get(supervisor_id)
            user.supervisor = supervisor

        # Zapisuje zmiany w bazie danych
        db.session.commit()

    return redirect(url_for('index'))


# Usuwanie kampanii
@app.route('/delete_campaign/<int:campaign_id>', methods=['GET', 'POST']) 
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if campaign:
        db.session.delete(campaign)
        db.session.commit()
    return redirect(url_for('index'))

# Kampanie użytkownika
@app.route('/user/<int:user_id>')
def user_campaigns(user_id):
    user = User.query.get(user_id)
    campaigns = user.campaigns
    return render_template('user_campaigns.html', user=user, campaigns=campaigns)

# Dodawanie kampanii
@app.route('/add_campaign/<int:user_id>', methods=['POST'])
def add_campaign(user_id):
    user = User.query.get(user_id)
    campaign_name = request.form.get('campaign_name')
    if campaign_name:
        with app.app_context():
            new_campaign = Campaign(name=campaign_name, user=user)
            db.session.add(new_campaign)
            db.session.commit()
    return redirect(url_for('user_campaigns', user_id=user_id))

# Raport czasu pracy
@app.route('/add_work_report/<int:campaign_id>', methods=['GET', 'POST'])
def add_work_report(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if request.method == 'POST':
        hours_worked = float(request.form.get('hours_worked'))
        minutes_worked = float(request.form.get('minutes_worked')) 
        if hours_worked and minutes_worked:
            with app.app_context():
                new_work_report = WorkReport(hours_worked=hours_worked, minutes_worked=minutes_worked, campaign_id=campaign_id)
                db.session.add(new_work_report)
                db.session.commit()
        return redirect(url_for('user_campaigns', user_id=campaign.user.id))

    # Obsługa wyświetlania formularza dodawania raportu o przepracowanych godzinach
    return render_template('add_work_report.html', campaign=campaign)

# Formularz dodawania kampanii
@app.route('/add_campaign_page/<int:user_id>', methods=['GET', 'POST'])
def add_campaign_page(user_id):
    if request.method == 'POST':
        campaign_name = request.form.get('campaign_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d') 
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')  
        if campaign_name and start_date and end_date:
            with app.app_context():
                user = User.query.get(user_id)
                new_campaign = Campaign(name=campaign_name, start_date=start_date, end_date=end_date, user=user) 
                db.session.add(new_campaign)
                db.session.commit()
                user_id_redirect = user.id
            return redirect(url_for('index', user_id=user_id_redirect))
    else:
        # Obsługa wyświetlania formularza dodawania kampanii
        user = User.query.get(user_id)
        return render_template('add_campaign.html', user=user)

# Raport czasu pracy dla przelozonych
@app.route('/report', methods=['GET'])
@login_required
def report():
    # Pobierz użytkowników, których supervisorem jest zalogowany użytkownik
    users = current_user.supervised
    return render_template('report.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
