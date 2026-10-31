# InsightMiner – Data Mining and Analytics Platform

**InsightMiner** is a web-based data mining application developed for IF Professional Studies Institute. It helps users upload, process, clean, analyze, visualize, and extract meaningful insights from datasets.

## Project Overview

InsightMiner provides an integrated platform for exploring datasets and supporting data-driven decision-making through statistical analysis, visualization, and predictive analytics.

## Key Features

- User registration and authentication
- Role-based user management
- CSV and Excel dataset uploads
- Dataset exploration and statistical summaries
- Data cleaning and preprocessing
- Interactive data visualizations
- AI-assisted insights
- Predictive analytics
- PDF and Excel report generation
- Activity logs and notifications
- Database backup functionality
- User profile management

## Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Database | MySQL |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn |
| Visualization | Matplotlib |
| Development Tools | VS Code, Git, GitHub |

## Application Screenshots

### Dashboard
![InsightMiner Dashboard](screenshots/Dashboard.png)

### Data Cleaning
![Data Cleaning](screenshots/Data%20Cleaning.png)

### Generate Charts
![Generate Chart](screenshots/Generate%20Chart.png)

### Predictive Analysis
![Predictive Analysis](screenshots/Predictive%20analysis.png)

### Generate AI Insights
![AI Insights](screenshots/Generate%20AI%20Insights.png)

### Reports
![Reports](screenshots/Reports.png)

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Jawahira-casim/InsightMiner.git
cd InsightMiner
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root directory:

```env
FLASK_SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=insightminer
```

Replace the example values with your own local configuration. Never upload your actual `.env` file to GitHub.

### 6. Set up the MySQL database

Create a MySQL database named `insightminer` and configure the required tables according to the application's database structure.

### 7. Run the application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
InsightMiner/
├── app.py
├── db.py
├── config.py
├── dataset_processor.py
├── notification_helper.py
├── routes/
├── templates/
├── static/
├── screenshots/
├── requirements.txt
├── .gitignore
└── README.md
```

## Project Purpose

This project demonstrates the practical application of web development, database management, data preprocessing, data mining, machine learning, and data visualization.

## Author

**Jawahira Casim**

Master of Information Technology (MIT)

GitHub: [Jawahira-casim](https://github.com/Jawahira-casim)

Repository: [InsightMiner](https://github.com/Jawahira-casim/InsightMiner)