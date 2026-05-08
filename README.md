# 🏠 HostelPro — Full Stack Hostel Management System

## Features

### Student Portal
- Registration & Application
- Dashboard with fee status & due alerts
- Complaint submission with category & admin reply
- Leave application & approval tracking
- Parcel tracking (WhatsApp notification)
- Entry/Exit log view
- Room transfer requests
- Meal menu & star rating system
- Payment history with receipt numbers

### Admin Panel
- Secure login (username/password)
- Full student management (activate/deactivate)
- Application approval/rejection
- Room allocation & occupancy visualization
- Complaint management with reply system
- Leave approval/rejection
- Room transfer approval (auto room swap)
- Notice board (Urgent / Important / Normal)
- Meal menu posting
- Payment recording with receipts
- Analytics & Reports with charts

### Guard Panel
- Entry / Exit logging by phone number
- Parcel arrival logging with sender info
- Auto WhatsApp notification to student
- Live recent entries/parcels view

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Default Admin Credentials
- **Username:** admin
- **Password:** admin123

Change after first login!

## URLs
| URL | Description |
|-----|-------------|
| `/student` | Student login |
| `/apply` | New student application |
| `/dashboard` | Student dashboard |
| `/admin/login` | Admin login |
| `/admin` | Admin panel |
| `/guard` | Guard panel |
| `/report` | Analytics |
| `/pay/<phone>` | Fee payment |

## Optional Integrations
Set these environment variables:
```
RAZORPAY_KEY=your_key
RAZORPAY_SECRET=your_secret
TWILIO_SID=your_sid
TWILIO_AUTH=your_auth
TWILIO_NUMBER=whatsapp:+14155238886
```

## Security Notes
- Passwords hashed with Werkzeug (bcrypt)
- SQL injection prevented via parameterized queries
- Session-based authentication with decorators
- Admin & student sessions are separate
