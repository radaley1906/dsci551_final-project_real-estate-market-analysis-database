import os
import streamlit as st
import psycopg2 as pg2
from psycopg2 import sql
import os
from openai import OpenAI
import pandas as pd


#--Environment & API keys ---------------------------------

# Add connnection to mysql server
mydb = 'test'

# Establish a connection to PostgreSQL database
secret = 'YOUR_POSTGRES_PASSWORD'

# pass in the database name 
conn = pg2.connect(database= mydb ,user='postgres', password = secret )

# retrieve cursor - control structor that allows me to iterate over database and execute query
cur = conn.cursor()
mycursor = cur


#--Helper Functions ------------------------------------

# list tables
def list_tables(schema = "public"):
    mycursor.execute(
        """
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_schema = %s
        """, (schema,)
    )
    return [row[0] for row in mycursor]

# describe table

def describe_table(table, schema = "public"):
    mycursor.execute(
       """
       SELECT column_name, data_type 
       FROM information_schema.columns
       WHERE table_name = %s 
       AND table_schema = %s
       """, (table, schema)
    )
    return mycursor.fetchall()

# sample data

def sample_rows(table, n=5):
    qry = sql.SQL("SELECT * FROM {} LIMIT %s").format(
        sql.Identifier(table)
    )

    mycursor.execute(qry, (n,))
    rows = mycursor.fetchall()
    cols = [c[0] for c in mycursor.description]
    return cols, rows

# Error handling & feedback

def run_sql(sql, params=None):
    try:
        mycursor.execute(sql, params or ())
        conn.commit()
        return mycursor.fetchall(), [d[0] for d in mycursor.description]
    except Exception as e:
        st.error(f"Database error: {e}")
        return [], []

# NL to SQL Translation------------- #


import re

def get_time_columns(table: str) -> list[str]:
    """Extracts all time-series columns from the schema dynamically."""
    return [
        col for col, _ in describe_table(table)
        if re.match(r"\d{4}-\d{2}-\d{2}", col)
    ]


client = OpenAI(
  api_key="YOUR_OPENAI_API_KEY") # REMOVED API KEY

def nl_to_sql(nl: str, schema: str) -> str:
    
    table_name = "home_value_index"
    time_cols = get_time_columns("home_value_index")
    col_expr = " + ".join(f'"{table_name}"."{c}"' for c in time_cols)
    avg_expr = f"(ROUND(({col_expr})::numeric / {len(time_cols)}, 2)) AS avg_home_value"



    prompt = f"""
You are an assistant that converts natural language to SQL.

IMPORTANT:
- Enclose all table and column names in double quotes (e.g., "City", "State", "home_value_index").
- Match the exact casing from the schema.
- Only return a valid SQL query, with no explanations or formatting like markdown.

Context:
- The table is time-series: each row is a region (like a city), and each column, excluding "RegionID", "City", "State", is a date (e.g. "2023-09-30", "2023-10-31", etc.) representing a home value.
- To calculate the average for a single city across time, use this formula:

    {avg_expr}

Here is the database schema:
{schema}

User question: "{nl}"
Only output valid SQL.
"""
    # use new client API 
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":prompt}]
    )
    return resp.choices[0].message.content.strip()





#--streamlit APP ------------------------------------


#-- new home affordability app

def main():
    

    #-- edit wireframe / ui

    # set page config
    st.set_page_config(
        page_title="Real Estate Market Research Dashboard",
        layout = "wide",
        initial_sidebar_state="expanded"
    )

    st.title("Market Research Dashboard")

    st.markdown(
    """
    <style>
    .header-container {
        background-color: #00BFFF; 
        padding: 10px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .header-container h1 {
        color: white;
        font-size: 24px;
        margin: 0;
    }
    </style>
    <div class="header-container">
        <h1>🏡 Real Estate Market Insights</h1>
    </div>
    """,
    unsafe_allow_html=True
    )


    st.sidebar.title("Navigation")
    st.sidebar.markdown("---")
    st.sidebar.caption("Version 1.0 • April 2025 • Built by Ron Daley")



    #-- Mode section code ------------------------------------------------------

    # Top‐level operations
    mode = st.sidebar.selectbox("Mode",
        ["Table Exploration", "Sample Queries", "Query Execution (NL→SQL)",
         "Create", "Update", "Delete"]
    )

    if mode == "Table Exploration":
        st.subheader("Explore Tables")
        t = st.selectbox("Choose table", list_tables())
        cols, rows = sample_rows(t, n=st.slider("Sample rows", 1, 1000, 5))
        st.write("**Sample Data**")
        df = pd.DataFrame(rows, columns=cols)
        st.dataframe(df)

    elif mode == "Sample Queries":
        st.subheader("Pre‑built Sample Queries")
        table = st.selectbox("Table", list_tables())
        
        
        sample_queries = {
    # SELECT / FROM        
    "1. Top 10 Regions (ORDER BY / DESC)": 
        f'SELECT "RegionID", "City", "State", "2025-02-28" FROM {table} ORDER BY "2025-02-28" DESC LIMIT 10',

    # ORDER BY / LIMIT
    "2. Top 10 Regions by 5-Month Average (ORDER BY / LIMIT)": 
        f'''
        SELECT "RegionID", "City", "State",
            ROUND(("2024-10-31" + "2024-11-30" + "2024-12-31" + "2025-01-31" + "2025-02-28")::numeric / 5, 2) AS avg_recent_price
        FROM {table}
        ORDER BY avg_recent_price DESC
        LIMIT 10
        ''',

    # WHERE / DESC / LIMIT
    "3. Top 10 California Cities (WHERE / DESC / LIMIT)": 
        f'SELECT "RegionID", "City", "2025-02-28" FROM {table} WHERE "State" = \'CA\' ORDER BY "2025-02-28" DESC LIMIT 10',

    # ORDER BY / DESC
    "4. Average per State (ORDER BY / DESC)": 
        f'SELECT "State", ROUND(AVG("2025-02-28")::numeric, 0) AS avg_price_feb_2025 FROM {table} GROUP BY "State" ORDER BY avg_price_feb_2025 DESC',

    # ORDER BY / DESC / LIMIT 10
    "5. Top 10 Regions by YoY Growth (ORDER BY / DESC / LIMIT 10)": 
        f'SELECT "RegionID", "City", "State", (("2025-02-28" - "2024-02-29") / "2024-02-29") * 100 AS yoy_growth_pct FROM {table} ORDER BY yoy_growth_pct DESC LIMIT 10',

    # WHERE / ORDER BY / LIMIT
    "6.  Regions with 6-Month Avg Price > $1M (WHERE / ORDER BY / LIMIT)": 
        f"""
        SELECT "RegionID", "City", "State",
            ROUND((
                "2024-09-30" + "2024-10-31" + "2024-11-30" +
                "2024-12-31" + "2025-01-31" + "2025-02-28"
            )::numeric / 6, 2) AS avg_price
        FROM {table}
        WHERE (
            ("2024-09-30" + "2024-10-31" + "2024-11-30" +
            "2024-12-31" + "2025-01-31" + "2025-02-28") / 6
        ) > 1000000
        ORDER BY avg_price DESC
        LIMIT 10
        """,
    

    # JOIN + TIME-SERIES AVG
    "7. Avg Value by Investor State of Interest (JOIN)" :
        f"""
        SELECT 
            i."Name" AS investor_name,
            i."State_Interest" AS investor_state,
            ROUND(AVG((
                COALESCE(m."2020-02-29", 0) + COALESCE(m."2020-03-31", 0) + COALESCE(m."2020-04-30", 0) +
                COALESCE(m."2020-05-31", 0) + COALESCE(m."2020-06-30", 0) + COALESCE(m."2020-07-31", 0) +
                COALESCE(m."2020-08-31", 0) + COALESCE(m."2020-09-30", 0) + COALESCE(m."2020-10-31", 0) +
                COALESCE(m."2020-11-30", 0) + COALESCE(m."2020-12-31", 0) + COALESCE(m."2021-01-31", 0) +
                COALESCE(m."2021-02-28", 0) + COALESCE(m."2021-03-31", 0) + COALESCE(m."2021-04-30", 0) +
                COALESCE(m."2021-05-31", 0) + COALESCE(m."2021-06-30", 0) + COALESCE(m."2021-07-31", 0) +
                COALESCE(m."2021-08-31", 0) + COALESCE(m."2021-09-30", 0) + COALESCE(m."2021-10-31", 0) +
                COALESCE(m."2021-11-30", 0) + COALESCE(m."2021-12-31", 0) + COALESCE(m."2022-01-31", 0) +
                COALESCE(m."2022-02-28", 0) + COALESCE(m."2022-03-31", 0) + COALESCE(m."2022-04-30", 0) +
                COALESCE(m."2022-05-31", 0) + COALESCE(m."2022-06-30", 0) + COALESCE(m."2022-07-31", 0) +
                COALESCE(m."2022-08-31", 0) + COALESCE(m."2022-09-30", 0) + COALESCE(m."2022-10-31", 0) +
                COALESCE(m."2022-11-30", 0) + COALESCE(m."2022-12-31", 0) + COALESCE(m."2023-01-31", 0) +
                COALESCE(m."2023-02-28", 0) + COALESCE(m."2023-03-31", 0) + COALESCE(m."2023-04-30", 0) +
                COALESCE(m."2023-05-31", 0) + COALESCE(m."2023-06-30", 0) + COALESCE(m."2023-07-31", 0) +
                COALESCE(m."2023-08-31", 0) + COALESCE(m."2023-09-30", 0) + COALESCE(m."2023-10-31", 0) +
                COALESCE(m."2023-11-30", 0) + COALESCE(m."2023-12-31", 0) + COALESCE(m."2024-01-31", 0) +
                COALESCE(m."2024-02-29", 0) + COALESCE(m."2024-03-31", 0) + COALESCE(m."2024-04-30", 0) +
                COALESCE(m."2024-05-31", 0) + COALESCE(m."2024-06-30", 0) + COALESCE(m."2024-07-31", 0) +
                COALESCE(m."2024-08-31", 0) + COALESCE(m."2024-09-30", 0) + COALESCE(m."2024-10-31", 0) +
                COALESCE(m."2024-11-30", 0) + COALESCE(m."2024-12-31", 0) + COALESCE(m."2025-01-31", 0) +
                COALESCE(m."2025-02-28", 0)
            ) / 61)::numeric, 2) AS avg_value
        FROM investors i
        JOIN {table} m
            ON m."State" = CASE i."State_Interest"
                WHEN 'California' THEN 'CA'
                WHEN 'Texas' THEN 'TX'
                WHEN 'Illinois' THEN 'IL'
                WHEN 'New York' THEN 'NY'
                -- Add more states as needed
            END
        GROUP BY i."Name", i."State_Interest"
        ORDER BY avg_value DESC
        """
        }


        q = st.selectbox("Choose a query", list(sample_queries.keys()))
        q_sql = sample_queries[q]

        if st.button("Run"):
            data, cols = run_sql(q_sql)
            df = pd.DataFrame(data, columns=cols)
            st.dataframe(df)

    elif mode == "Query Execution (NL→SQL)":
        st.subheader("Ask anything in English")
        nl = st.text_area("Natural‑language query (i.e. What is the average home value of all time-based columns for Los Angeles?)")
        if st.button("Translate & Run"):
            schema_desc = "\n".join(
                f"{t}: {', '.join(c for c,_ in describe_table(t)) }"
                for t in list_tables()
            )

            sql_code = nl_to_sql(nl, schema_desc)
            
            # Clean up the generated SQL
            sql_code = sql_code.strip().removeprefix("```sql").removesuffix("```").strip()
            
            st.code(sql_code, language="sql")
            data, cols = run_sql(sql_code)
            df = pd.DataFrame(data, columns=cols)
            st.dataframe(df)
            

    elif mode.startswith("Create"):
        st.subheader("INSERT via NL")
        nl = st.text_area("E.g. “Add a new city called Championsville in California”")
        if st.button("Run"):
            
            schema_desc = "\n".join(
                f"{t}: {', '.join(c for c,_ in describe_table(t)) }"
                for t in list_tables()
            )

            sql = nl_to_sql(nl, schema=schema_desc)

            st.code(sql, language="sql")
            try:
                mycursor.execute(sql)
                conn.commit()
                st.success("Insert succeeded")
            except Exception as e:
                st.error(f"Insert failed: {e}")

    elif mode.startswith("Update"):
        st.subheader("UPDATE via NL")
        nl = st.text_area("E.g. “update the name of CA to CALI")
        if st.button("Run"):
            
            schema_desc = "\n".join(
                f"{t}: {', '.join(c for c,_ in describe_table(t)) }"
                for t in list_tables()
            )

            sql = nl_to_sql(nl, schema=schema_desc)

            st.code(sql, language="sql")
            try:
                mycursor.execute(sql)
                conn.commit()
                st.success("Update succeeded")
            except Exception as e:
                st.error(f"Update failed: {e}")

    elif mode.startswith("Delete"):
        st.subheader("DELETE via NL")
        nl = st.text_area("E.g. “Remove all rows where state is Oregon”")
        if st.button("Run"):

            schema_desc = "\n".join(
                f"{t}: {', '.join(c for c,_ in describe_table(t)) }"
                for t in list_tables()
            )

            sql = nl_to_sql(nl, schema=schema_desc)
            st.code(sql, language="sql")
            try:
                mycursor.execute(sql)
                conn.commit()
                st.success("Delete succeeded")
            except Exception as e:
                st.error(f"Delete failed: {e}")


# Run the app
if __name__ == "__main__":
    main()
