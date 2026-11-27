import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# PAGE CONFIGURATION
st.set_page_config(
    page_title="BookLens",
    page_icon="📚",
    layout="wide"
)

# SESSION STATE
if "books_data" not in st.session_state:
    st.session_state["books_data"] = None

if "dataset" not in st.session_state:
    st.session_state["dataset"] = None

if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# CUSTOM CSS
st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: bold;
    text-align: center;
    color: #6C63FF;
}
.subtitle {
    text-align: center;
    font-size: 18px;
    color: gray;
}
div.stButton > button {
    width: 100%;
    height: 65px;
    border-radius: 12px;
    font-size: 17px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# NAVIGATION
pages = [
    "Home",
    "Task 1 - Web Scraping",
    "Task 2 - Exploratory Data Analysis",
    "Task 3 - Data Visualization",
    "Task 4 - Sentiment Analysis",
    "Data Export"
]

st.sidebar.title("📚 BookLens")
st.sidebar.markdown("---")

selected_page = st.sidebar.radio(
    "Navigation",
    pages,
    index=pages.index(st.session_state["page"])
)

st.session_state["page"] = selected_page

# HOME PAGE
if st.session_state["page"] == "Home":

    st.markdown(
        '<p class="main-title">📚 BookLens</p>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<p class="subtitle">Discover Books • Explore Data • Gain Insights</p>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.subheader("Welcome to BookLens!")

    st.write(
        "An interactive Book Data Analytics platform "
        "to collect, analyze and visualize book information."
    )

    st.markdown("### Explore Our Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🌐 Web Scraping"):
            st.session_state["page"] = "Task 1 - Web Scraping"
            st.rerun()

    with col2:
        if st.button("📈 Data Analysis"):
            st.session_state["page"] = "Task 2 - Exploratory Data Analysis"
            st.rerun()

    with col3:
        if st.button("📊 Data Visualization"):
            st.session_state["page"] = "Task 3 - Data Visualization"
            st.rerun()

    col4, col5 = st.columns(2)

    with col4:
        if st.button("💬 Sentiment Analysis"):
            st.session_state["page"] = "Task 4 - Sentiment Analysis"
            st.rerun()

    with col5:
        if st.button("📥 Data Export"):
            st.session_state["page"] = "Data Export"
            st.rerun()

    st.markdown("---")

    if st.session_state["books_data"] is not None:
        st.success(
            f"Dataset Available: {len(st.session_state['books_data'])} Books"
        )
    else:
        st.info("Start Web Scraping to collect book data.")

    st.markdown(
        "<center>Developed using Python, Streamlit and Data Analytics</center>",
        unsafe_allow_html=True
    )

# TASK 1 - WEB SCRAPING
elif st.session_state["page"] == "Task 1 - Web Scraping":

    st.header("🌐 Web Scraping")

    st.write("Collect book information using Python.")

    pages_count = st.slider(
        "Number of pages to scrape",
        1, 50, 50
    )

    if st.button("Start Web Scraping"):

        books = []

        progress = st.progress(0)
        status = st.empty()

        try:
            for page in range(1, pages_count + 1):

                url = (
                    "https://books.toscrape.com/catalogue/"
                    f"page-{page}.html"
                )

                response = requests.get(
                    url,
                    timeout=20,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                response.raise_for_status()

                soup = BeautifulSoup(
                    response.text,
                    "html.parser"
                )

                book_items = soup.select("article.product_pod")

                for book in book_items:

                    title = book.h3.a["title"]

                    price = book.select_one(
                        ".price_color"
                    ).get_text(strip=True)

                    availability = book.select_one(
                        ".availability"
                    ).get_text(strip=True)

                    rating_element = book.select_one(
                        ".star-rating"
                    )

                    rating = rating_element.get("class", ["", "Unknown"])[1]

                    book_url = urljoin(
                        url,
                        book.h3.a["href"]
                    )

                    books.append({
                        "Title": title,
                        "Price": float(price.replace("£", "").replace("Â", "")),
                        "Availability": availability,
                        "Rating": rating,
                        "URL": book_url
                    })

                progress.progress(page / pages_count)
                status.write(f"Scraping page {page} of {pages_count}")

            df = pd.DataFrame(books)

            st.session_state["books_data"] = df
            st.session_state["dataset"] = df

            st.success(f"Successfully scraped {len(df)} books!")

        except requests.RequestException as e:
            st.error(f"Network error: {e}")

        except Exception as e:
            st.error(f"Scraping failed: {e}")

    if st.session_state["books_data"] is not None:

        df = st.session_state["books_data"]

        st.subheader("Scraped Book Data")

        st.dataframe(df, use_container_width=True)

        st.metric("Total Books", len(df))

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download CSV",
            csv,
            "books_data.csv",
            "text/csv"
        )

# TASK 2 - EDA
elif st.session_state["page"] == "Task 2 - Exploratory Data Analysis":

    st.header("📈 Exploratory Data Analysis")

    st.write("Analyze your book dataset.")

    uploaded_file = st.file_uploader(
        "Upload your CSV dataset (Optional)",
        type=["csv"],
        key="eda_upload"
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state["dataset"] = df
            st.success("Dataset uploaded successfully!")

        except Exception as e:
            st.error(f"Unable to read CSV: {e}")

    if st.session_state["dataset"] is not None:

        df = st.session_state["dataset"]

        st.subheader("Dataset Preview")
        st.dataframe(df.head(10), use_container_width=True)

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Rows", df.shape[0])
        col2.metric("Total Columns", df.shape[1])
        col3.metric(
            "Missing Values",
            int(df.isnull().sum().sum())
        )

        st.subheader("Dataset Information")
        st.dataframe(
            pd.DataFrame({
                "Column": df.columns,
                "Data Type": df.dtypes.astype(str)
            })
        )

        st.subheader("Statistical Summary")
        st.dataframe(df.describe(include="all"))

        st.subheader("Missing Values")
        st.dataframe(df.isnull().sum().to_frame("Missing Count"))

        st.subheader("Duplicate Rows")
        st.write(int(df.duplicated().sum()))

    else:
        st.info("Run Web Scraping first or upload a CSV dataset.")

# TASK 3 - DATA VISUALIZATION
elif st.session_state["page"] == "Task 3 - Data Visualization":

    st.header("📊 Data Visualization")

    st.write("Create charts and graphs from your book dataset.")

    uploaded_file = st.file_uploader(
        "Upload your CSV dataset (Optional)",
        type=["csv"],
        key="visual_upload"
    )

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state["dataset"] = df

        except Exception as e:
            st.error(f"Unable to read CSV: {e}")

    if st.session_state["dataset"] is not None:

        df = st.session_state["dataset"]

        numeric_columns = df.select_dtypes(
            include="number"
        ).columns.tolist()

        if numeric_columns:

            column = st.selectbox(
                "Select a column",
                numeric_columns
            )

            st.subheader("Bar Chart")
            st.bar_chart(df[column])

            st.subheader("Histogram")

            fig, ax = plt.subplots()

            ax.hist(df[column].dropna(), bins=15)

            ax.set_xlabel(column)
            ax.set_ylabel("Frequency")
            ax.set_title(f"Distribution of {column}")

            st.pyplot(fig)
            plt.close(fig)

            st.subheader("Correlation Matrix")

            if len(numeric_columns) > 1:
                st.dataframe(df[numeric_columns].corr())
            else:
                st.info("At least two numeric columns are needed.")

        else:
            st.warning("No numeric columns found.")

    else:
        st.info("Run Web Scraping first or upload a CSV dataset.")

# TASK 4 - SENTIMENT ANALYSIS
elif st.session_state["page"] == "Task 4 - Sentiment Analysis":

    st.header("💬 Sentiment Analysis")

    st.write("Analyze text reviews and identify their sentiment.")

    positive_words = [
        "good", "great", "excellent", "amazing",
        "happy", "love", "wonderful", "best",
        "awesome", "fantastic", "nice"
    ]

    negative_words = [
        "bad", "worst", "poor", "terrible",
        "hate", "awful", "disappointed",
        "boring", "sad", "waste"
    ]

    def analyze_sentiment(text):

        words = text.lower().split()

        positive = sum(
            word.strip(".,!?") in positive_words
            for word in words
        )

        negative = sum(
            word.strip(".,!?") in negative_words
            for word in words
        )

        if positive > negative:
            return "Positive"

        elif negative > positive:
            return "Negative"

        return "Neutral"

    review = st.text_area("Enter your review here:")

    if st.button("Analyze Sentiment"):

        if review.strip():

            result = analyze_sentiment(review)

            if result == "Positive":
                st.success("😊 Positive Sentiment")

            elif result == "Negative":
                st.error("😞 Negative Sentiment")

            else:
                st.info("😐 Neutral Sentiment")

            st.write("Result:", result)

        else:
            st.warning("Please enter a review.")

# DATA EXPORT
elif st.session_state["page"] == "Data Export":

    st.header("📥 Data Export")

    st.write("Download your collected book dataset.")

    if st.session_state["books_data"] is not None:

        df = st.session_state["books_data"]

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Books Dataset",
            csv,
            "books_data.csv",
            "text/csv"
        )

        st.success("Your dataset is ready to download.")

    elif st.session_state["dataset"] is not None:

        df = st.session_state["dataset"]

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Dataset",
            csv,
            "dataset.csv",
            "text/csv"
        )

    else:
        st.info("No dataset available. Run Web Scraping first.")

# SIDEBAR FOOTER
st.sidebar.markdown("---")
st.sidebar.caption("📚 BookLens")
st.sidebar.caption("Developed using Python & Streamlit")
st.sidebar.caption("CodeAlpha Data Analytics Internship")
