# 🛡️ AML Transaction Monitoring System

A production-ready SaaS platform for Anti-Money Laundering (AML) transaction monitoring and alert generation.

## ✨ Features

- **Real-time Transaction Monitoring**: Upload CSV files with up to 50,000 transactions
- **Intelligent Rule Engine**: 4 built-in AML detection rules
  - Large Transaction Detection
  - High-Frequency Transaction Detection  
  - Rapid Money Movement Detection
  - High-Risk Country Detection
- **Alert Management**: Review, investigate, and manage suspicious activity alerts
- **Interactive Dashboard**: Real-time statistics and recent alerts
- **Multi-User Support**: Role-based access control (Admin, Analyst, Viewer)
- **Modern UI**: Clean, responsive interface with Tailwind CSS

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.10+) with async/await
- **Database**: PostgreSQL with async SQLAlchemy
- **Caching**: Redis
- **Frontend**: HTMX + Jinja2 Templates
- **Styling**: Tailwind CSS

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL 15+
- Redis 7+
- Docker (optional, for easy PostgreSQL + Redis setup)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd transaction-monitoring-saas
```

### 2. Set Up Database (Option A: Docker)

```bash
# Start PostgreSQL and Redis with Docker Compose
docker-compose up -d

# Verify containers are running
docker ps
```

### 2. Set Up Database (Option B: Local PostgreSQL)

If you have PostgreSQL installed locally:

```bash
# Create database
psql -U postgres
CREATE DATABASE aml_monitoring;
\q
```

Update `.env` file with your PostgreSQL credentials.

### 3. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings (database password, etc.)
# Make sure DATABASE_URL matches your PostgreSQL setup
```

### 5. Initialize Database

```bash
# Create all tables and test user
python scripts/init_db.py

# When prompted, type 'yes' to create test user
```

This creates:
- All database tables
- Test user: `admin@test.com` / `password123`
- Default AML rules

### 6. Generate Sample Data (Optional)

```bash
# Generate 50,000 sample transactions
python scripts/create_sample_data.py

# This creates: sample_transactions_50k.csv
```

### 7. Start the Application

```bash
# Start development server
uvicorn app.main:app --reload

# Or use Python directly
python -m app.main
```

The application will be available at:
- **Dashboard**: http://localhost:8000/dashboard
- **Login**: http://localhost:8000/login
- **API Docs**: http://localhost:8000/api/docs

## 📖 Usage Guide

### First Time Setup

1. **Navigate to**: http://localhost:8000/login
2. **Login with test credentials**:
   - Email: `admin@test.com`
   - Password: `password123`
3. **Or register a new account** at http://localhost:8000/register

### Upload Transactions

1. Go to **Upload** page
2. Select the CSV file (use `sample_transactions_50k.csv` for testing)
3. Click **Upload & Process**
4. Wait for processing (30-60 seconds for 50K transactions)
5. View results on Dashboard

### Review Alerts

1. Go to **Alerts** page
2. Click on any alert to view details
3. Review transaction information
4. Update status:
   - **Under Review**: Investigation in progress
   - **Closed**: Confirmed suspicious
   - **False Positive**: Legitimate transaction
5. Add notes for audit trail

## 🔧 Configuration

### Database Settings

Edit `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/aml_monitoring
```

### Rule Configuration

Default rule parameters in `app/utils/constants.py`: