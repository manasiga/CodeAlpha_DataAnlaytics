import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="BookLens | Book Analytics",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# CUSTOM CSS - UI / UX DESIGN
# --------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #080b18, #11152b, #17112e);
    color: #ffffff;
}

/* Main container */

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #11152b, #1b1535);
    border-right: 1px solid #34305b;
}

section[data-testid="stSidebar"] h1 {
    color: #c4a5ff;
}

/* Headings */

h1, h2, h3 {
    color: #ffffff !important;
    font-weight: 700;
}

/* Paragraph */

p, label, span {
    color: #d0d2e5;
}

/* Buttons */

.stButton > button {
    background: linear-gradient(90deg, #8054e9, #b45cff);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1.5rem;
    font-weight: 600;
    transition: 0.3s;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #a276ff, #d17aff);
    transform: translateY(-2px);
}

/* Metric Cards */

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #20264a, #302052);
    border: 1px solid #51417c;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

[data-testid="stMetricLabel"] {
    color: #c4b5fd !important;
}

[data-testid="stMetricValue"] {
    color: #ffffff !important;
}

/* Dataframe */

[data-testid="stDataFrame"] {
    border: 1px solid #51417c;
    border-radius: 12px;
}

/* Input fields */

.stTextInput input,
.stNumberInput input {
    background-color: #202443;
    color: white;
    border-radius: 8px;
}

/* Select boxes */

.stSelectbox div[data-baseweb="select"] {
    background-color: #202443;
}

/* File uploader */

[data-testid="stFileUploader"] {
    background: #1c2140;
    border: 1px dashed #9569ff;
    border-radius: 12px;
    padding: 15px;
}

/* Custom cards */

.custom-card {
    background: linear-gradient(135deg, #20264a, #302052);
    border: 1px solid #51417c;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 15px;
    min-height: 145px;
}

.custom-card h3 {
    color: #c4a5ff !important;
    font-size: 20px;
}

.custom-card p {
    color: #d0d2e5;
    font-size: 14px;
}

.hero {
    background: linear-gradient(120deg, #39246c, #6639a5, #25204d);
    border: 1px solid #8060c9;
    border-radius: 22px;
    padding: 45px 35px;
    margin-bottom: 30px;
}

.hero h1 {
    font-size: 43px;
    color: white !important;
}

.hero p {
    font-size: 17px;
    color: #e5d9ff;
}

.footer {
    text-align: center;
    padding: 25px;
    color: #9994bd;
    border-top: 1px solid #34305b;
    margin-top: 50px;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# COMMON FUNCTIONS
# --------------------------------------------------

def show_header(title, description):
    st.markdown(f"## {title}")
    st.markdown(f"<p>{description}</p>", unsafe_allow_html=True)
    st.markdown("---")


def load_uploaded_or_scraped_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)

    if "books_data" in st.session_state:
        return st.session_state["books_data"]

    return None


def prepare_numeric_columns(df):
    numeric_df = df.copy()

    for col in numeric_df.columns:
        if numeric_df[col].dtype == "object":
            cleaned = (
                numeric_df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace(r"[£$€]", "", regex=True)
                .str.strip()
            )

            converted = pd.to_numeric(cleaned, errors="coerce")

            if converted.notna().any():
                numeric_df[col] = converted

    numeric_columns = numeric_df.select_dtypes(
        include=["number"]
    ).columns.tolist()

    return numeric_df, numeric_columns


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.markdown("# 📚 BookLens")

    st.markdown(
        "<p style='color:#a9a2d0;'>Book Data Analytics Platform</p>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "🏠 Home",
            "🌐 Web Scraping",
            "🔍 Exploratory Data Analysis",
            "📊 Data Visualization",
            "💬 Sentiment Analysis"
        ]
    )

    st.markdown("---")

    st.markdown(
        """
        <div class="custom-card">
            <h3>✨ BookLens</h3>
            <p>Discover Books.<br>
            Explore Data.<br>
            Uncover Insights.</p>
        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">
        <h1>📚 Welcome to BookLens</h1>
        <p>Discover Books. Explore Data. Uncover Insights.</p>
        <p>
        A smart book data analytics platform to collect,
        explore and visualize book information.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🚀 Explore Your Platform")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="custom-card">
            <h3>🌐 Web Scraping</h3>
            <p>Collect book titles, prices, ratings
            and availability from websites.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="custom-card">
            <h3>🔍 Data Analysis</h3>
            <p>Understand datasets through
            statistical analysis and insights.</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="custom-card">
            <h3>📊 Visualization</h3>
            <p>Transform numerical data into
            meaningful charts and graphs.</p>
        </div>
        """, unsafe_allow_html=True)

    col4, col5 = st.columns(2)

    with col4:
        st.markdown("""
        <div class="custom-card">
            <h3>💬 Sentiment Analysis</h3>
            <p>Analyze text and identify
            positive, negative and neutral sentiment.</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="custom-card">
            <h3>📁 Data Export</h3>
            <p>Download collected and analyzed
            datasets in CSV format.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("## 📈 Your Dataset Overview")

    if "books_data" in st.session_state:

        df = st.session_state["books_data"]

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Books", len(df))

        if "Price" in df.columns:
            c2.metric(
                "Average Price",
                f"£{df['Price'].mean():.2f}"
            )

        if "Rating" in df.columns:
            c3.metric(
                "Average Rating",
                f"{df['Rating'].mean():.2f} / 5"
            )

    else:
        st.info("Go to Web Scraping to collect your book dataset.")


# --------------------------------------------------
# TASK 1 - WEB SCRAPING
# --------------------------------------------------

elif page == "🌐 Web Scraping":

    show_header(
        "🌐 Web Scraping",
        "Collect book information from Books to Scrape website."
    )

    st.markdown("### ⚙️ Scraping Configuration")

    col1, col2 = st.columns(2)

    with col1:
        website_url = st.text_input(
            "Website URL",
            "https://books.toscrape.com/"
        )

    with col2:
        max_pages = st.number_input(
            "Number of Pages",
            min_value=1,
            max_value=50,
            value=50
        )

    st.info("50 pages can contain up to 1000 books on this demo website.")

    if st.button("🚀 Start Web Scraping"):

        books = []
        current_url = website_url
        progress = st.progress(0)
        status = st.empty()

        rating_map = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5
        }

        try:

            for page_number in range(int(max_pages)):

                status.write(
                    f"Collecting page {page_number + 1} of {max_pages}..."
                )

                response = requests.get(
                    current_url,
                    headers={
                        "User-Agent": "Mozilla/5.0"
                    },
                    timeout=20
                )

                response.raise_for_status()

                soup = BeautifulSoup(
                    response.text,
                    "html.parser"
                )

                book_items = soup.select("article.product_pod")

                if not book_items:
                    break

                for item in book_items:

                    title = item.h3.a["title"]

                    price_text = item.select_one(
                        ".price_color"
                    ).text.strip()

                    price = float(
                        re.sub(r"[^0-9.]", "", price_text)
                    )

                    availability = item.select_one(
                        ".availability"
                    ).text.strip()

                    rating_class = item.select_one(
                        "p.star-rating"
                    )["class"]

                    rating_word = rating_class[1]

                    rating = rating_map.get(
                        rating_word, 0
                    )

                    books.append({
                        "Title": title,
                        "Price": price,
                        "Availability": availability,
                        "Rating": rating
                    })

                next_button = soup.select_one("li.next a")

                if next_button is None:
                    break

                current_url = urljoin(
                    current_url,
                    next_button["href"]
                )

                progress.progress(
                    (page_number + 1) / int(max_pages)
                )

            progress.progress(1.0)
            status.success("Scraping completed successfully!")

            if books:

                df = pd.DataFrame(books)

                st.session_state["books_data"] = df

                st.success(
                    f"Successfully collected {len(df)} books!"
                )

            else:
                st.warning("No books were collected. Check the website URL.")

        except Exception as e:

            st.error(f"Scraping Error: {e}")

    if "books_data" in st.session_state:

        df = st.session_state["books_data"]

        st.markdown("---")
        st.markdown("## 📚 Scraped Book Dataset")

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Books", len(df))

        c2.metric(
            "Average Price",
            f"£{df['Price'].mean():.2f}"
        )

        c3.metric(
            "Average Rating",
            f"{df['Rating'].mean():.2f} / 5"
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=350
        )

        st.download_button(
            "⬇️ Download Books Dataset",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="books_data.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# TASK 2 - EXPLORATORY DATA ANALYSIS
# --------------------------------------------------

elif page == "🔍 Exploratory Data Analysis":

    show_header(
        "🔍 Exploratory Data Analysis",
        "Explore the structure, quality and statistics of your book dataset."
    )

    uploaded_file = st.file_uploader(
        "Upload your CSV dataset (optional)",
        type=["csv"],
        key="eda_upload"
    )

    df = load_uploaded_or_scraped_data(uploaded_file)

    if df is not None:

        st.markdown("### 📋 Dataset Preview")

        st.dataframe(
            df.head(10),
            use_container_width=True
        )

        st.markdown("### 📊 Dataset Summary")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Rows", df.shape[0])
        col2.metric("Total Columns", df.shape[1])
        col3.metric("Missing Values", int(df.isnull().sum().sum()))
        col4.metric("Duplicate Rows", int(df.duplicated().sum()))

        st.markdown("---")

        st.markdown("### 📈 Statistical Summary")

        st.dataframe(
            df.describe(include="all").T,
            use_container_width=True
        )

        st.markdown("### 🧹 Missing Values Analysis")

        missing_data = df.isnull().sum()

        if missing_data.sum() > 0:

            st.bar_chart(missing_data)

        else:

            st.success("Great! No missing values found.")

        st.markdown("### 🔁 Duplicate Records")

        st.write(
            f"Duplicate records: {df.duplicated().sum()}"
        )

    else:

        st.warning(
            "Upload a CSV file or first collect books using Web Scraping."
        )


# --------------------------------------------------
# TASK 3 - DATA VISUALIZATION
# --------------------------------------------------

elif page == "📊 Data Visualization":

    show_header(
        "📊 Data Visualization",
        "Create meaningful charts and understand your book data."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV dataset (optional)",
        type=["csv"],
        key="visual_upload"
    )

    df = load_uploaded_or_scraped_data(uploaded_file)

    if df is not None:

        numeric_df, numeric_columns = prepare_numeric_columns(df)

        st.markdown("### 📁 Dataset Preview")

        st.dataframe(
            df.head(10),
            use_container_width=True
        )

        if numeric_columns:

            st.markdown("### 📊 Chart Configuration")

            col1, col2 = st.columns(2)

            with col1:

                selected_column = st.selectbox(
                    "Select Numeric Column",
                    numeric_columns
                )

            with col2:

                chart_type = st.selectbox(
                    "Select Chart Type",
                    [
                        "Bar Chart",
                        "Line Chart",
                        "Histogram"
                    ]
                )

            if chart_type == "Bar Chart":

                chart_data = numeric_df[
                    selected_column
                ].value_counts().sort_index()

                st.bar_chart(chart_data)

            elif chart_type == "Line Chart":

                st.line_chart(
                    numeric_df[selected_column]
                )

            elif chart_type == "Histogram":

                fig, ax = plt.subplots(figsize=(10, 5))

                ax.hist(
                    numeric_df[selected_column].dropna(),
                    bins=15,
                    edgecolor="black"
                )

                ax.set_title(
                    f"Distribution of {selected_column}"
                )

                ax.set_xlabel(selected_column)
                ax.set_ylabel("Frequency")

                st.pyplot(fig)

            st.success(
                f"Visualization generated using {selected_column}."
            )

        else:

            st.warning(
                "No numeric columns found. Please upload a dataset containing numerical values."
            )

    else:

        st.warning(
            "Upload a CSV file or first collect books using Web Scraping."
        )


# --------------------------------------------------
# TASK 4 - SENTIMENT ANALYSIS
# --------------------------------------------------

elif page == "💬 Sentiment Analysis":

    show_header(
        "💬 Sentiment Analysis",
        "Analyze text and identify positive, negative and neutral opinions."
    )

    uploaded_file = st.file_uploader(
        "Upload CSV file containing text",
        type=["csv"],
        key="sentiment_upload"
    )

    if uploaded_file is not None:

        df = pd.read_csv(uploaded_file)

        st.markdown("### 📋 Dataset Preview")

        st.dataframe(
            df.head(),
            use_container_width=True
        )

        text_columns = df.select_dtypes(
            include=["object"]
        ).columns.tolist()

        if text_columns:

            selected_column = st.selectbox(
                "Select Text Column",
                text_columns
            )

            if st.button("🔍 Analyze Sentiment"):

                analyzer = SentimentIntensityAnalyzer()

                def analyze_sentiment(text):

                    score = analyzer.polarity_scores(
                        str(text)
                    )["compound"]

                    if score >= 0.05:
                        return "Positive"

                    elif score <= -0.05:
                        return "Negative"

                    else:
                        return "Neutral"

                df["Sentiment"] = df[
                    selected_column
                ].apply(analyze_sentiment)

                st.session_state["sentiment_data"] = df

                st.success("Sentiment analysis completed!")

        else:

            st.warning("No text columns found in this dataset.")

    if "sentiment_data" in st.session_state:

        result_df = st.session_state["sentiment_data"]

        st.markdown("---")
        st.markdown("## 📊 Sentiment Results")

        sentiment_counts = result_df[
            "Sentiment"
        ].value_counts()

        positive = sentiment_counts.get("Positive", 0)
        negative = sentiment_counts.get("Negative", 0)
        neutral = sentiment_counts.get("Neutral", 0)

        c1, c2, c3 = st.columns(3)

        c1.metric("😊 Positive", positive)
        c2.metric("😞 Negative", negative)
        c3.metric("😐 Neutral", neutral)

        st.markdown("### Sentiment Distribution")

        st.bar_chart(sentiment_counts)

        st.markdown("### 📋 Analysis Results")

        st.dataframe(
            result_df,
            use_container_width=True
        )

        st.download_button(
            "⬇️ Download Sentiment Results",
            data=result_df.to_csv(index=False).encode("utf-8"),
            file_name="sentiment_analysis.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("""
<div class="footer">
    <h3>📚 BookLens</h3>
    <p>Book Data Analytics & Visualization Platform</p>
    <p>Developed with Python and Streamlit</p>
    <p>© 2026 BookLens | All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)
