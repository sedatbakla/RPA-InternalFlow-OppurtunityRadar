import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="InternalFlow Opportunity Radar",
    page_icon="📊",
    layout="wide"
)

st.title("InternalFlow Opportunity Radar")
st.write("This dashboard is designed to analyze and visualize opportunity data.")

# Sample data for the first dashboard version
data = {
    "Opportunity": ["Project A", "Project B", "Project C"],
    "Department": ["IT", "Sales", "Finance"],
    "Score": [85, 70, 92],
    "Status": ["Open", "In Progress", "Open"]
}

# Convert dictionary data into a pandas DataFrame
df = pd.DataFrame(data)

st.subheader("Opportunity List")
st.dataframe(df)

st.subheader("Average Score by Department")

# Group scores by department and calculate the average score
department_scores = df.groupby("Department")["Score"].mean()

st.bar_chart(department_scores)