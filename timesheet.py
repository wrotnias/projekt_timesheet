from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Model użytkownika
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    username_and_id = db.Column(db.String(100), unique=True, nullable=False)
    campaigns = db.relationship('Campaign', backref='user', lazy=True)

# Model kampanii
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, unique=True, nullable=False, default=lambda: random.randint(1000, 9999))
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

# Model raportu czasu pracy
class WorkReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hours_worked = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)

# Tworzenie tabel w bazie danych
with app.app_context():
    db.create_all()

# Dodanie przykładowego użytkownika i kampanii do bazy danych
with app.app_context():
    existing_user = User.query.filter_by(username_and_id='example_user').first()
    if not existing_user:
        new_user = User(first_name='John', last_name='Doe', username_and_id='example_user')
        db.session.add(new_user)
        db.session.commit()

    existing_campaign = Campaign.query.filter_by(name='example_campaign').first()
    if not existing_campaign:
        example_user = User.query.filter_by(username_and_id='example_user').first()
        new_campaign = Campaign(name='example_campaign', user=example_user)
        db.session.add(new_campaign)
        db.session.commit()

# Trasa główna
@app.route('/')
def index():
    users = User.query.all()
    return render_template('index.html', users=users)

# Trasa dodawania użytkownika
@app.route('/add_user', methods=['POST'])
def add_user():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if first_name and last_name:
        with app.app_context():
            # Tworzenie unikalnego usernameAndID
            username_and_id = f"{first_name}{last_name}{User.query.count() + 1}"
            
            new_user = User(first_name=first_name, last_name=last_name, username_and_id=username_and_id)
            db.session.add(new_user)
            db.session.commit()
    return redirect(url_for('index'))


# Trasa kampanii użytkownika
@app.route('/user/<int:user_id>')
def user_campaigns(user_id):
    user = User.query.get(user_id)
    campaigns = user.campaigns
    return render_template('user_campaigns.html', user=user, campaigns=campaigns)

# Trasa dodawania kampanii
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

# Trasa raportu czasu pracy
@app.route('/add_work_report/<int:campaign_id>', methods=['POST'])
def add_work_report(campaign_id):
    hours_worked = request.form.get('hours_worked')
    if hours_worked:
        with app.app_context():
            new_work_report = WorkReport(hours_worked=hours_worked, campaign_id=campaign_id)
            db.session.add(new_work_report)
            db.session.commit()
    return redirect(url_for('user_campaigns', user_id=Campaign.query.get(campaign_id).user.id))

if __name__ == '__main__':
    app.run(debug=True)
