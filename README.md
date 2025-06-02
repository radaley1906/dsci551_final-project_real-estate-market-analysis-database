# 🏡 Real Estate Market Research Dashboard

An interactive Streamlit-based dashboard for exploring real estate trends and querying time-series home value data using natural language. The application converts English queries into SQL using OpenAI's GPT models and interacts with a PostgreSQL database to return relevant results.

---

## 📦 Features

- Table exploration with column/type introspection.
- Sample SQL queries for immediate insights.
- Natural Language to SQL conversion using GPT-4.
- Create, Update, Delete database operations through English prompts.
- Interactive data visualizations powered by Streamlit.

---

### 🔧 Prerequisites

- Python 3.8 or newer
- PostgreSQL server running with accessible credentials
- [OpenAI API key](https://platform.openai.com/account/api-keys)
- Git (optional, for version control)

---

### 🔐 Required API Keys & Credentials

You must provide your own credentials in the script before running:

1. **PostgreSQL Database Password:**
   In `v2app_noAPIkeys.py`, locate the line (16):
   ```python
   secret = 'YOUR_POSTGRES_PASSWORD'

2. ***Open AI Password:***
   In `v2app_noAPIkeys.py`, locate the line (89):
   ```python
   api_key="YOUR_OPENAI_API_KEY"

---

***Course:*** DSCI 551 - Foundations of Data Management
