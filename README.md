# InsightMiner – Educational Data Mining Application

InsightMiner is a web-based data mining application developed using Python and Flask to analyse educational datasets and extract meaningful insights that support data-driven decision-making.

## Features

- Upload CSV and Excel datasets
- Explore datasets and generate descriptive statistics
- Identify and handle missing values
- Clean and prepare datasets
- Generate data visualisations and correlation heatmaps
- Discover meaningful patterns and insights
- Perform predictive analysis
- Generate downloadable reports
- Manage users and access permissions
- Track user activities and notifications

## Technologies Used

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Database:** MySQL
- **Data Analysis:** Pandas, NumPy, Scikit-learn
- **Visualisation:** Matplotlib
- **Development Tools:** Visual Studio Code, Git, GitHub

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

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-secret-key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your-database-password
DB_NAME=insightminer
```

Replace the example values with your local configuration. Never upload your actual `.env` file.

### 5. Configure the MySQL database

Create the MySQL database named `insightminer` and configure the required database tables.

### 6. Run the application

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
├── dataset_processor.py
├── requirements.txt
├── routes/
├── templates/
├── static/
├── .gitignore
└── README.md
```

## Project Purpose

The main purpose of InsightMiner is to simplify educational data analysis by providing tools for dataset exploration, data cleaning, visualisation and predictive analysis through a web-based interface.

## Author

**Jawahira Casim**

GitHub: [Jawahira-casim](https://github.com/Jawahira-casim)

---

*Developed as an academic and practical software development project.*