<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,12,18,24,30&height=170&section=header&text=HostelPro&fontSize=72&fontColor=ffffff&animation=fadeIn" width="100%" alt="HostelPro banner"/>

# 🏠 HostelPro — Full Stack Hostel Management System

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&pause=1200&color=22D3EE&center=true&vCenter=true&width=700&lines=Student+Portal;Admin+Panel;Guard+Panel;Payments+%7C+Complaints+%7C+Parcels+%7C+Analytics)](#features)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=ffd43b)
![Werkzeug](https://img.shields.io/badge/Werkzeug-hashed%20passwords-22c55e?style=for-the-badge)
![Razorpay](https://img.shields.io/badge/Razorpay-0C2451?style=for-the-badge&logo=razorpay&logoColor=3395FF)
![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)

![Student](https://img.shields.io/badge/Student%20Portal-0ea5e9?style=for-the-badge)
![Admin](https://img.shields.io/badge/Admin%20Panel-a855f7?style=for-the-badge)
![Guard](https://img.shields.io/badge/Guard%20Panel-f97316?style=for-the-badge)

[![Features](https://img.shields.io/badge/Go%20to-Features-22c55e?style=flat-square)](#features)
[![Setup](https://img.shields.io/badge/Go%20to-Setup-0ea5e9?style=flat-square)](#setup)
[![URLs](https://img.shields.io/badge/Go%20to-URLs-f97316?style=flat-square)](#urls)
[![Integrations](https://img.shields.io/badge/Go%20to-Integrations-a855f7?style=flat-square)](#optional-integrations)
[![Security](https://img.shields.io/badge/Go%20to-Security-ef4444?style=flat-square)](#security-notes)

</div>

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=6,12,18&height=10&section=header" width="100%" alt=""/>

## Features

<details open>
<summary><b>Student Portal</b></summary>

<br>

![Student Portal](https://img.shields.io/badge/Student%20Portal-0ea5e9?style=for-the-badge)

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

</details>

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=12,18,24&height=4&section=header" width="100%" alt=""/>

<details open>
<summary><b>Admin Panel</b></summary>

<br>

![Admin Panel](https://img.shields.io/badge/Admin%20Panel-a855f7?style=for-the-badge)

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

</details>

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=18,24,0&height=4&section=header" width="100%" alt=""/>

<details open>
<summary><b>Guard Panel</b></summary>

<br>

![Guard Panel](https://img.shields.io/badge/Guard%20Panel-f97316?style=for-the-badge)

### Guard Panel
- Entry / Exit logging by phone number
- Parcel arrival logging with sender info
- Auto WhatsApp notification to student
- Live recent entries/parcels view

</details>

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=24,0,6&height=10&section=header" width="100%" alt=""/>

## Setup

```bash
pip install -r requirements.txt
python app.py
```

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=30,6,12&height=10&section=header" width="100%" alt=""/>

## Default Admin Credentials

- **Username:** admin
- **Password:** admin123

Change after first login!

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=0,6,12&height=10&section=header" width="100%" alt=""/>

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

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=8,14,20&height=10&section=header" width="100%" alt=""/>

## Optional Integrations

Set these environment variables:
```
RAZORPAY_KEY=your_key
RAZORPAY_SECRET=your_secret
TWILIO_SID=your_sid
TWILIO_AUTH=your_auth
TWILIO_NUMBER=whatsapp:+14155238886
```

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=14,20,26&height=10&section=header" width="100%" alt=""/>

## Security Notes

- Passwords hashed with Werkzeug (bcrypt)
- SQL injection prevented via parameterized queries
- Session-based authentication with decorators
- Admin & student sessions are separate

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,12,18,24,30&height=150&section=footer" width="100%" alt="footer"/>

</div>
