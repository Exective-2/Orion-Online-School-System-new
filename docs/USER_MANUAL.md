# 📖 Orion Online School System — Comprehensive User Manual

Welcome to the **Orion Online School Management System**. This user manual provides step-by-step instructions for all user roles (Headteachers, Administrators, Teachers, Accountants, Parents, Students, and System Administrators).

---

## 1. Getting Started & Authentication

### 1.1 Accessing the Portal
Open any modern web browser (Google Chrome, Microsoft Edge, Safari, or Mozilla Firefox) and navigate to your school's portal URL:
👉 `https://your-school-domain.com` (or your school's dedicated IP/domain on Hostinger).

![Login Screen Portal](/Users/a252857/Desktop/Antigravity project/Orion-Online-School-System-new/docs/screenshots/01_login_screen.png)

### 1.2 Sign In Methods
1. **Standard Username & Password Login**:
   - Enter your assigned **Username** (e.g. `headteacher`, `teacher_kofi`) and **Password**.
   - Click **Sign In to Workspace**.
2. **Phone Number SMS OTP Login**:
   - Click **Request SMS Login OTP**.
   - Enter your registered mobile phone number (e.g. `+233 24 123 4567`).
   - You will receive a 6-digit OTP code on your mobile phone via SMS.
   - Enter the 6-digit code to log in securely without typing your password.

### 1.3 Progressive Web App (PWA) & Mobile Installation
Orion is fully equipped as a Progressive Web App (PWA). Teachers, administrators, accountants, and parents can install the app directly onto their smartphone, tablet, or desktop home screen without downloading from app stores.

#### Installing on iOS (iPhone & iPad)
1. Open **Safari** on your iOS device and navigate to your school's portal URL (e.g. `https://your-school-domain.com`).
2. Tap the **Share** button (the `[↑]` box icon in the Safari bottom toolbar).
3. Scroll down the menu options and select **Add to Home Screen**.
4. Confirm the app name (**Orion SMS**) and tap **Add** in the top-right corner.
5. The **Orion SMS** icon will appear on your Home Screen, launching in full-screen standalone mode without browser bars.

#### Installing on Android & Chrome Mobile
1. Open **Google Chrome** on your Android device and navigate to the portal.
2. An **"Install Orion SMS"** banner will slide up at the bottom of the screen. Tap **Install**.
3. If the banner does not appear, tap the three dots `⋮` menu in the top right corner of Chrome and select **Install app** or **Add to Home screen**.
4. The app icon is added to your home screen and app drawer.

#### Installing on Desktop (Windows / macOS / ChromeOS)
1. Open the portal in **Google Chrome** or **Microsoft Edge**.
2. Click the **Install Icon** (`⊕` or monitor icon) located on the right side of the browser address bar.
3. Click **Install**. Orion will open in its own dedicated, chromeless window.

---

## 2. Dashboard Overview & Workspace Navigation

### 2.1 Workspace Dashboard
Upon logging in, users are presented with a role-based Glassmorphic dashboard displaying active student metrics, staff counts, library books, termly fee collections, and real-time class distribution analytics charts.

![Dashboard Overview](/Users/a252857/Desktop/Antigravity project/Orion-Online-School-System-new/docs/screenshots/02_dashboard_overview.png)

### 2.2 Real-Time Notification Badges & Live Header Bell
The system features a **Server-Sent Events (SSE) Real-Time Notification Engine** that broadcasts live updates to connected users without needing manual page refreshes.

1. **Header Notification Bell**:
   - Located in the top header action bar.
   - Features a glowing red count badge (`notif-badge-global`) summarizing unread events.
   - Clicking the bell opens the **Live Notification Panel**, displaying:
     - **Unread Parent Messages**
     - **Pending Fee Bills & Unpaid Accounts**
     - **New Announcements & Notices (Past 7 days)**
   - The green pulsing dot (**Live Dot**) confirms an active real-time SSE stream with the backend server.
2. **Sidebar Navigation Badges**:
   - **Communication Badge**: Displays live unread messages sent by parents.
   - **Finance & Fees Badge**: Displays live count of unpaid student bills.

---

## 3. Headteacher & Administrator Guide

### 3.1 Updating School Profile, Logo & Digital Signature
1. Navigate to **Settings** in the left sidebar menu.
2. Under the **School Profile & Branding** tab:
   - Enter **School Name**, **School Motto**, **Tagline**, **Phone Number**, **Email**, and **GPS Address**.
   - **Upload School Logo**: Click *Choose File* under School Logo. Select a PNG or JPG logo image. The logo updates immediately and is saved securely to the database.
   - **Upload Headteacher Signature**: Click *Choose File* under Headteacher / Authorization Signature. Upload a transparent PNG image of the headteacher's signature. This signature will automatically watermark official terminal report cards and transcripts.
3. Click **Save School Profile**.

![School Profile & Settings Panel](/Users/a252857/Desktop/Antigravity project/Orion-Online-School-System-new/docs/screenshots/03_school_settings.png)

### 3.2 Headteacher Profile & Authorization Signature Modal
Headteachers and authorized administrative staff can also manage their account settings and signature directly from the **My Profile & Account Settings** modal.

![Headteacher Signature Modal](/Users/a252857/Desktop/Antigravity project/Orion-Online-School-System-new/docs/screenshots/05_headteacher_signature_modal.png)

### 3.3 Registering Staff Members & Automated SMS Credentials
1. Navigate to **Staff Directory** in the left sidebar.
2. Click **+ Register Staff**.
3. Fill in the staff member's details:
   - **First Name & Last Name** (e.g. *Kwame Appiah*)
   - **Assigned Role**: Select *Teacher*, *Headteacher*, *Accountant*, *Librarian*, or *IT Admin*.
   - **Username**: Create a unique username (e.g. *kwame.appiah*).
   - **Mobile Phone Number**: Enter their valid 10-digit mobile phone number (e.g. `0241112233`).
   - **Initial Password**: Enter a password (or leave blank to assign default `Orion@123`).
4. Click **Register Staff Profile**.
5. **Automated SMS Action**: The system automatically dispatches an SMS to the new staff member's mobile phone containing their username, initial password, and portal link.

![Register Staff Modal](/Users/a252857/Desktop/Antigravity project/Orion-Online-School-System-new/docs/screenshots/04_register_staff_modal.png)

### 3.4 Approving Class Terminal Reports
1. Navigate to **Exams & Reports** -> **Score Approvals**.
2. Review submitted class marksheets submitted by subject teachers.
3. Verify Class Scores (30%), Exam Scores (70%), and calculated Total Scores.
4. Click **Approve Assessment Roster**. Approved scores are immediately locked and rendered onto official student terminal report cards.

### 3.5 Batch Printing Student Terminal Report Cards
1. Navigate to **Exams & Reports** -> **Report Cards**.
2. Select the **Academic Term** and **Class** (e.g., *Basic 7 - Alpha*).
3. Click **Generate Batch PDF Report Cards**.
4. The system compiles official Report Cards containing:
   - School Logo Header & School Contacts.
   - Student Rank / Position in Class.
   - Subject Grade Breakdown, Totals & Remarks.
   - Embedded Headteacher Signature Watermark.

---

## 4. Teacher Guide

### 4.1 Marking Daily Student Attendance
1. Navigate to **Attendance** in the left sidebar.
2. Select your assigned **Class** and the **Date**.
3. Click **Present**, **Absent**, or **Late** for each student.
4. Click **Save Attendance Record**.
5. *Automatic Parent Alert*: Parents of absent students automatically receive an instant SMS attendance notification.

### 4.2 Recording Continuous Assessment & Exam Scores
1. Navigate to **Exams & Reports** -> **Marks Entry**.
2. Select the **Class**, **Subject** (e.g., *Mathematics*), and **Academic Term**.
3. Enter scores into the roster:
   - **Class Score**: Max 30 marks (Continuous Assessment / Homework / Tests).
   - **Exam Score**: Max 70 marks (Terminal Examination).
4. Total Score, GES Grade (A, B, C, D, F), and Grade Remarks calculate automatically.
5. Click **Submit Marks to Headteacher for Approval**.

### 4.3 Offline Attendance & Mark Entry (Service Worker Sync)
Teachers working in remote areas or classrooms with unstable Wi-Fi/cellular connection can record attendance and enter marks completely offline.

1. **Automatic Offline Detection**:
   - If internet connectivity drops, an amber banner appears at the top of the app: *"You're offline — data is cached. Queued actions will sync when reconnected."*
   - The Service Worker (`sw.js`) automatically serves cached student rosters and application interfaces.
2. **Offline Data Queuing**:
   - When you click **Save Attendance** or **Submit Marks** while offline, the system safely stores your submission in the device's **IndexedDB Sync Queue**.
   - You will see a toast notification confirming: *"Saved offline. Will sync when connection restores."*
3. **Background Synchronization**:
   - As soon as your device reconnects to Wi-Fi or mobile data, the Service Worker automatically executes a **Background Sync**, transmitting all queued attendance logs and mark entries to the server.
   - A success alert notifies you: *"Offline actions synced successfully"*.

---

## 5. Accountant & Finance Guide

### 5.1 Setting Up Termly Fee Structures
1. Navigate to **Finance & Billing** -> **Fee Structures**.
2. Click **+ Add Fee Item**.
3. Specify Fee Title, Class Level, and Amount (GHS).
4. Click **Save Fee Structure**.

### 5.2 Recording Student Fee Payments & SMS Receipts
1. Navigate to **Finance & Billing** -> **Collect Payments**.
2. Search for the student by **Name** or **Student ID** (e.g., `ORION-26-A1B2`).
3. Enter Payment Amount, Payment Method (Cash/MoMo/Bank), and Reference Number.
4. Click **Process Payment & Generate Receipt**.
5. **Instant SMS Action**: An SMS receipt is instantly sent to the parent's mobile phone detailing payment amount and remaining balance.

### 5.3 Monthly Staff Payroll & Payslip Downloads
1. Navigate to **Finance & Billing** -> **Staff Payroll**.
2. Select the **Pay Period** (e.g., *July 2026*).
3. Click **Generate Monthly Payroll**. Review base salaries, allowances, and deductions.
4. Click **Process Payouts**. Download official PDF Payslips for staff distribution.

---

## 6. Parent & Student Guide

### 6.1 Accessing the Parent Portal
1. Open your school's portal URL (e.g. `https://your-school-domain.com` or launch the installed Orion PWA app).
2. Click **Request SMS Login OTP** or sign in with your registered phone number and PIN.
3. Select your linked ward/child (if you have multiple children enrolled).

### 6.2 Viewing Terminal Reports & Transcripts
1. On the Parent Dashboard, navigate to **Academic Reports**.
2. Select the **Term** to view terminal report card details online or click **Download PDF Report Card**.

### 6.3 Checking Fee Balances & Payment History
1. Navigate to **Financial Ledger**.
2. View total billed fees, total payments made, current outstanding balance, and download past digital receipts.

---

## 7. System Administrator Guide

### 7.1 Multi-Branch Provisioning
1. Log in with System Admin credentials (`sysadmin`).
2. Navigate to **System Admin Portal** -> **Branches**.
3. Click **+ Create Branch**. Specify Branch Name, Branch Code, and Tenant Database filename.

### 7.2 Managing SMS Gateway Configuration
1. Navigate to **System Admin Portal** -> **SMS Gateway Config**.
2. Select Gateway Provider (*Arkesel*, *Hubtel*, *mNotify*, or *Twilio*).
3. Enter your **Sender ID** (e.g., `ORION`), **API Key**, and **API Secret**.
4. Click **Test SMS Gateway**. The system sends a live test SMS to verify connection.

---

*Orion Online School System User Manual — PWA & SSE Release Build 2026.08*
