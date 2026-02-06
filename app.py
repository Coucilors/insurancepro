from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from functools import wraps
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email, EmailNotValidError
import os
import secrets
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///insurance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Email configuration - configure these via environment variables
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@insurancepro.com')

# Database Models
class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    insurance_type = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, unsubscribed, bounced
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_campaign_sent = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'status': self.status,
            'subscribed_at': self.subscribed_at.strftime('%Y-%m-%d %H:%M')
        }

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    template_type = db.Column(db.String(50), default='default')
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, sending, sent, failed
    target_segment = db.Column(db.String(50), default='all')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    total_recipients = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    opened_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'subject': self.subject,
            'status': self.status,
            'total_recipients': self.total_recipients,
            'sent_count': self.sent_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Forms
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Length(max=20)])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=5000)])
    submit = SubmitField('Send Message')

class NewsletterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[Length(max=100)])
    submit = SubmitField('Subscribe')

class CampaignForm(FlaskForm):
    name = StringField('Campaign Name', validators=[DataRequired(), Length(max=200)])
    subject = StringField('Email Subject', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Email Content', validators=[DataRequired()])
    template_type = SelectField('Template', choices=[('default', 'Default'), ('promotional', 'Promotional'), ('newsletter', 'Newsletter')])
    target_segment = SelectField('Target Segment', choices=[('all', 'All Subscribers'), ('active', 'Active Only')])
    submit = SubmitField('Create Campaign')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Email Functions
def validate_email_address(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def send_email(to_email, subject, html_content, text_content=None):
    if not all([SMTP_USERNAME, SMTP_PASSWORD]):
        print("SMTP credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_email_template(template_type, content, unsubscribe_token):
    unsubscribe_link = f"http://localhost:5000/unsubscribe/{unsubscribe_token}"
    
    templates = {
        'default': f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; line-height: 1.6; color: #333333; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666666; }}
                .footer a {{ color: #2a5298; }}
                .button {{ display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #ffffff; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>InsurancePro</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>© 2026 InsurancePro. All rights reserved.</p>
                    <p>If you no longer wish to receive emails, <a href="{unsubscribe_link}">unsubscribe here</a>.</p>
                </div>
            </div>
        </body>
        </html>
        """,
        'promotional': f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 40px; text-align: center; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 28px; }}
                .content {{ padding: 40px; line-height: 1.8; color: #333333; }}
                .highlight {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }}
                .footer {{ background-color: #343a40; padding: 20px; text-align: center; font-size: 12px; color: #ffffff; }}
                .footer a {{ color: #ffc107; }}
                .cta-button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: #ffffff; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Special Offer!</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>© 2026 InsurancePro. All rights reserved.</p>
                    <p><a href="{unsubscribe_link}">Unsubscribe</a> from promotional emails</p>
                </div>
            </div>
        </body>
        </html>
        """,
        'newsletter': f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Georgia', serif; margin: 0; padding: 0; background-color: #f9f9f9; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                .header {{ background-color: #2c3e50; padding: 25px; text-align: center; }}
                .header h1 {{ color: #ecf0f1; margin: 0; font-size: 26px; font-weight: normal; }}
                .content {{ padding: 35px; line-height: 1.7; color: #2c3e50; }}
                .article {{ margin-bottom: 25px; padding-bottom: 25px; border-bottom: 1px solid #ecf0f1; }}
                .article:last-child {{ border-bottom: none; }}
                .footer {{ background-color: #ecf0f1; padding: 20px; text-align: center; font-size: 11px; color: #7f8c8d; }}
                .footer a {{ color: #2c3e50; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>InsurancePro Newsletter</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>© 2026 InsurancePro. Stay informed, stay protected.</p>
                    <p><a href="{unsubscribe_link}">Manage subscription preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
    }
    
    return templates.get(template_type, templates['default'])

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            subject=form.subject.data,
            message=form.message.data
        )
        db.session.add(message)
        db.session.commit()
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    insurance_type = request.form.get('insurance_type', '').strip()
    
    if not email or not validate_email_address(email):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Please provide a valid email address.'})
        flash('Please provide a valid email address.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if existing.status == 'unsubscribed':
            existing.status = 'active'
            existing.name = name or existing.name
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Welcome back! Your subscription has been reactivated.'})
            flash('Welcome back! Your subscription has been reactivated.', 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'You are already subscribed!'})
            flash('You are already subscribed!', 'info')
    else:
        subscriber = Subscriber(email=email, name=name, insurance_type=insurance_type)
        db.session.add(subscriber)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thank you for subscribing! You will receive our latest updates.'})
        flash('Thank you for subscribing! You will receive our latest updates.', 'success')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/unsubscribe/<token>')
def unsubscribe(token):
    try:
        email = serializer.loads(token, salt='unsubscribe', max_age=31536000)  # 1 year
        subscriber = Subscriber.query.filter_by(email=email).first()
        if subscriber:
            subscriber.status = 'unsubscribed'
            db.session.commit()
            flash('You have been successfully unsubscribed.', 'success')
        else:
            flash('Subscriber not found.', 'error')
    except:
        flash('Invalid or expired unsubscribe link.', 'error')
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            if admin.is_active:
                session['admin_id'] = admin.id
                session.permanent = True
                admin.last_login = datetime.utcnow()
                db.session.commit()
                flash('Welcome back!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Account is deactivated.', 'error')
        else:
            flash('Invalid username or password.', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    stats = {
        'total_subscribers': Subscriber.query.count(),
        'active_subscribers': Subscriber.query.filter_by(status='active').count(),
        'total_campaigns': Campaign.query.count(),
        'sent_campaigns': Campaign.query.filter_by(status='sent').count(),
        'unread_messages': ContactMessage.query.filter_by(is_read=False).count()
    }
    recent_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, campaigns=recent_campaigns)

@app.route('/admin/subscribers')
@login_required
def admin_subscribers():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    query = Subscriber.query
    if status != 'all':
        query = query.filter_by(status=status)
    
    subscribers = query.order_by(Subscriber.subscribed_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/subscribers.html', subscribers=subscribers, status=status)

@app.route('/admin/campaigns')
@login_required
def admin_campaigns():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('admin/campaigns.html', campaigns=campaigns)

@app.route('/admin/campaigns/new', methods=['GET', 'POST'])
@login_required
def new_campaign():
    form = CampaignForm()
    if form.validate_on_submit():
        campaign = Campaign(
            name=form.name.data,
            subject=form.subject.data,
            content=form.content.data,
            template_type=form.template_type.data,
            target_segment=form.target_segment.data,
            status='draft'
        )
        db.session.add(campaign)
        db.session.commit()
        flash('Campaign created successfully!', 'success')
        return redirect(url_for('admin_campaigns'))
    return render_template('admin/new_campaign.html', form=form)

@app.route('/admin/campaigns/<int:campaign_id>/send', methods=['POST'])
@login_required
def send_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    if campaign.status == 'sent':
        return jsonify({'success': False, 'message': 'Campaign has already been sent.'})
    
    # Get target subscribers
    if campaign.target_segment == 'active':
        subscribers = Subscriber.query.filter_by(status='active').all()
    else:
        subscribers = Subscriber.query.filter(Subscriber.status.in_(['active', ''])).all()
    
    if not subscribers:
        return jsonify({'success': False, 'message': 'No subscribers found for this campaign.'})
    
    campaign.status = 'sending'
    campaign.total_recipients = len(subscribers)
    db.session.commit()
    
    sent_count = 0
    failed_count = 0
    
    for subscriber in subscribers:
        try:
            token = serializer.dumps(subscriber.email, salt='unsubscribe')
            html_content = get_email_template(campaign.template_type, campaign.content, token)
            
            if send_email(subscriber.email, campaign.subject, html_content):
                sent_count += 1
                subscriber.last_campaign_sent = datetime.utcnow()
            else:
                failed_count += 1
        except Exception as e:
            print(f"Error sending to {subscriber.email}: {e}")
            failed_count += 1
    
    campaign.status = 'sent'
    campaign.sent_at = datetime.utcnow()
    campaign.sent_count = sent_count
    campaign.failed_count = failed_count
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Campaign sent! {sent_count} successful, {failed_count} failed.',
        'sent': sent_count,
        'failed': failed_count
    })

@app.route('/admin/campaigns/<int:campaign_id>/preview')
@login_required
def preview_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    token = serializer.dumps('preview@example.com', salt='unsubscribe')
    html_content = get_email_template(campaign.template_type, campaign.content, token)
    return html_content

@app.route('/admin/campaigns/<int:campaign_id>/delete', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.status == 'sent':
        flash('Cannot delete sent campaigns.', 'error')
    else:
        db.session.delete(campaign)
        db.session.commit()
        flash('Campaign deleted successfully.', 'success')
    return redirect(url_for('admin_campaigns'))

@app.route('/admin/messages')
@login_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)

@app.route('/admin/messages/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    message = ContactMessage.query.get_or_404(message_id)
    message.is_read = True
    db.session.commit()
    return jsonify({'success': True})

# API Routes
@app.route('/api/subscribers/count')
def subscribers_count():
    count = Subscriber.query.filter_by(status='active').count()
    return jsonify({'count': count})

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', email='admin@insurancepro.com')
            admin.set_password('admin123')  # Change this in production
            db.session.add(admin)
            db.session.commit()
            print("Default admin created - username: admin, password: admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)


# Initialize database and create admin user on startup
with app.app_context():
    init_db()

