# InsurancePro - Insurance Website with Email Campaign System

A professional, responsive, and secure insurance website built with Flask, featuring a complete email campaign management system.

## Features

### Frontend
- **Professional Landing Page**: Modern design with hero section, features, services, testimonials
- **Responsive Design**: Fully responsive across all devices (mobile, tablet, desktop)
- **About Page**: Company information, values, and team
- **Services Page**: Detailed insurance service offerings with pricing plans
- **Contact Page**: Contact form with validation
- **Newsletter Subscription**: AJAX-powered subscription forms

### Admin Dashboard
- **Secure Authentication**: Password hashing with bcrypt, session management
- **Email Campaign Management**: Create, preview, and send email campaigns
- **Subscriber Management**: View, filter, and export subscriber lists
- **Message Management**: Handle contact form submissions
- **Campaign Statistics**: Track sent campaigns and subscriber counts

### Email Marketing
- **HTML Email Templates**: 3 professionally designed templates (Default, Promotional, Newsletter)
- **Campaign Targeting**: Send to all subscribers or active only
- **Email Preview**: Preview campaigns before sending
- **Unsubscribe Handling**: Automatic unsubscribe links in emails
- **Status Tracking**: Draft, scheduled, sending, sent, failed status tracking

### Security Features
- CSRF Protection on all forms
- Input validation and sanitization
- Secure session cookies (HttpOnly, Secure, SameSite)
- Password hashing with bcrypt
- SQL injection protection via SQLAlchemy ORM
- XSS protection via template auto-escaping

## Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (easily upgradeable to PostgreSQL/MySQL)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Styling**: Custom CSS with CSS Variables
- **Forms**: Flask-WTF with CSRF protection
- **Authentication**: Flask-Bcrypt
- **Icons**: Font Awesome

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. Create a virtual environment:
```bash
cd insurance-website
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python3 -c "from app import init_db; init_db()"
```

4. Run the application:
```bash
python3 run.py
```

5. Access the website:
- Frontend: http://localhost:5000
- Admin Panel: http://localhost:5000/admin/login

### Default Admin Credentials
- **Username**: admin
- **Password**: admin123

**Important**: Change the default password after first login!

## Email Configuration

To enable email sending, set these environment variables:

```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export FROM_EMAIL=noreply@insurancepro.com
export SECRET_KEY=your-secret-key-here
```

Or create a `.env` file:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@insurancepro.com
SECRET_KEY=your-secret-key-here
```

### Gmail Setup
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password at: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password) in SMTP_PASSWORD

## Project Structure

```
insurance-website/
├── app.py                  # Main Flask application
├── run.py                  # Startup script
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── instance/
│   └── insurance.db       # SQLite database
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Homepage
│   ├── about.html         # About page
│   ├── services.html      # Services page
│   ├── contact.html       # Contact page
│   └── admin/
│       ├── login.html     # Admin login
│       ├── base_admin.html # Admin dashboard base
│       ├── dashboard.html  # Admin dashboard
│       ├── subscribers.html # Subscriber management
│       ├── campaigns.html  # Campaign list
│       ├── new_campaign.html # Create campaign
│       └── messages.html   # Contact messages
```

## Usage

### Creating an Email Campaign

1. Login to admin panel at `/admin/login`
2. Click "Create Campaign" on the dashboard
3. Fill in campaign details:
   - Campaign Name (internal reference)
   - Email Subject
   - Select Template (Default, Promotional, or Newsletter)
   - Choose Target Segment
   - Enter HTML content
4. Click "Create Campaign"
5. Preview the campaign
6. Click the send button to send to all subscribers

### Managing Subscribers

- View all subscribers at `/admin/subscribers`
- Filter by status (All, Active, Unsubscribed)
- Export subscribers to CSV
- Subscribers can join via the newsletter form on the website

### Contact Messages

- View all contact form submissions at `/admin/messages`
- Mark messages as read
- Reply directly via email
- New messages are highlighted

## Customization

### Changing Colors
Edit CSS variables in `templates/base.html`:
```css
:root {
    --primary-color: #1e3c72;
    --accent-color: #00d4aa;
    /* ... other variables */
}
```

### Adding New Email Templates
Edit the `get_email_template` function in `app.py` to add new templates.

### Changing Company Info
Update the content in the HTML templates directly.

## Production Deployment

### Security Checklist
- [ ] Change default admin password
- [ ] Set strong SECRET_KEY environment variable
- [ ] Configure SMTP with valid credentials
- [ ] Enable HTTPS
- [ ] Set `SESSION_COOKIE_SECURE = True` in production
- [ ] Use PostgreSQL/MySQL instead of SQLite
- [ ] Set up proper logging
- [ ] Configure rate limiting
- [ ] Use a WSGI server (Gunicorn, uWSGI)

### Environment Variables for Production
```bash
export FLASK_ENV=production
export SECRET_KEY=your-256-bit-secret-key
export DATABASE_URL=postgresql://user:pass@localhost/insurance
export SMTP_SERVER=smtp.provider.com
export SMTP_PORT=587
export SMTP_USERNAME=noreply@yourdomain.com
export SMTP_PASSWORD=your-password
export FROM_EMAIL=noreply@yourdomain.com
```

## License

This project is open source and available for personal and commercial use.

## Support

For issues or questions, please refer to the Flask documentation or contact the developer.

---

**Built with ❤️ using Flask**
