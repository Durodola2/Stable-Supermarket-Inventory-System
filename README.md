# 🛒 Stable Supermarket Inventory Management System

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blue)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange?logo=mysql)
![XAMPP](https://img.shields.io/badge/Server-XAMPP-FB7A24?logo=xampp)
![License](https://img.shields.io/badge/License-MIT-green)

A modern desktop-based **Inventory and Sales Management System** developed using **Python**, **CustomTkinter**, and **MySQL/MariaDB**.

The application helps supermarkets manage inventory, monitor stock levels, process sales, generate receipts, track customers and suppliers, and generate business reports through a modern desktop interface.

---

# ✨ Features

- Secure Administrator Login
- Staff User Management
- Product Management
- Category Management
- Supplier Management
- Customer Management
- Inventory Tracking
- Product Search (SKU & Name)
- Sales Processing
- Shopping Cart System
- Automatic Stock Deduction
- Receipt Generation
- Sales History
- Inventory Reports
- Low Stock Monitoring
- Stock Adjustment (Restock/Damaged Items)
- Database Backup
- Modern CustomTkinter User Interface

---

# 🛠 Technologies Used

- Python 3
- CustomTkinter
- MySQL / MariaDB
- XAMPP
- python-dotenv
- Pillow
- ReportLab

---

# 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Stable-Supermarket-Inventory-System.git
```

### 2. Open the project

```bash
cd Stable-Supermarket-Inventory-System
```

### 3. Start MySQL

Start **Apache** and **MySQL** using XAMPP.

### 4. Import the database

Import

```
database/schema.sql
```

using **phpMyAdmin**.

### 5. Configure Environment Variables

Copy

```
.env.example
```

to

```
.env
```

and update your database credentials.

### 6. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 7. Run the application

```powershell
.\.venv\Scripts\python.exe main.py
```

The first launch allows you to create the administrator account.

---

# 🖥 Windows Executable

The compiled executable is located inside:

```
dist/
```

Simply:

- Keep `.env` beside the executable.
- Start MySQL using XAMPP.
- Double-click:

```
StableSupermarket.exe
```

---

# 📸 Screenshots

### Login Screen

![Login](screenshots/login.png)

---

### Dashboard

![Dashboard](screenshots/dashboard.png)

---

### Product Management

![Products](screenshots/products.png)

---

### Sales

![Sales](screenshots/sales.png)

---

### Reports

![Reports](screenshots/reports.png)

---

# 📂 Project Structure

```
Stable-Supermarket-Inventory-System
│
├── database/
│   └── schema.sql
│
├── docs/
│
├── receipts/
│
├── screenshots/
│
├── build/
│
├── dist/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
└── .env.example
```

---

# 📚 Documentation

Complete project documentation is available inside:

```
docs/PROJECT_DOCUMENTATION.md
```

The documentation includes:

- System Overview
- Database Design
- Features
- User Roles
- System Workflow
- Backup Guide
- Installation Guide
- Development Notes

---

# 🚀 Future Improvements

- Barcode Scanner Integration
- QR Code Product Lookup
- Sales Analytics Dashboard
- Employee Activity Logs
- Multi-Branch Support
- Cloud Synchronization
- Email Receipts
- SMS Notifications

---

# 🔒 Security

The project uses:

- Environment Variables (.env)
- Password Authentication
- Database Validation
- Input Validation
- Automatic Inventory Updates

> **Important:** Never upload your `.env` file. It contains local database credentials and is ignored by `.gitignore`.

---

# 👨‍💻 Author

**David Durodola**

Backend & Data Engineer

GitHub:
https://github.com/Durodola2

Email:
durodoladavid3@gmail.com

---

# 📄 License

This project is licensed under the MIT License.