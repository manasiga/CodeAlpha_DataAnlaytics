import streamlit as st

st.set_page_config(
    page_title="CodeAlpha Data Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CodeAlpha Data Analytics Internship")
st.write("Welcome to my Data Analytics project portfolio!")

st.sidebar.title("Navigation")

task = st.sidebar.radio(
    "Select a Task",
    [
        "Home",
        "Task 1 - Web Scraping",
        "Task 2 - Exploratory Data Analysis",
        "Task 3 - Data Visualization",
        "Task 4 - Sentiment Analysis"
    ]
)

if task == "Home":
    st.header("Data Analytics Projects")
    st.write("This website contains all four tasks completed during my internship.")

    col1, col2 = st.columns(2)

    with col1:
        st.info("🌐 Task 1: Web Scraping")
        st.info("📈 Task 2: Exploratory Data Analysis")

    with col2:
        st.info("📊 Task 3: Data Visualization")
        st.info("💬 Task 4: Sentiment Analysis")

elif task == "Task 1 - Web Scraping":
    st.header("🌐 Web Scraping")
    st.write("Collecting data from websites using Python.")

elif task == "Task 2 - Exploratory Data Analysis":
    st.header("📈 Exploratory Data Analysis")
    st.write("Analyzing and understanding datasets using Python.")

elif task == "Task 3 - Data Visualization":
    st.header("📊 Data Visualization")
    st.write("Presenting data through charts and graphs.")

elif task == "Task 4 - Sentiment Analysis":
    st.header("💬 Sentiment Analysis")
    st.write("Analyzing text data to identify positive and negative sentiments.")

st.sidebar.markdown("---")
st.sidebar.write("Created for CodeAlpha Internship")
