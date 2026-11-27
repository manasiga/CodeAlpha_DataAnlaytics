```python
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# PAGE CONFIGURATION
st.set_page_config(
    page_title="CodeAlpha Data Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CodeAlpha Data Analytics Internship")
st.write("Welcome to my Data Analytics Project Portfolio!")

# SESSION STATE
if "books_data" not in st.session_state:
    st.session_state["books_data"] = None

if "dataset" not in st.session_state:
    st.session_state["dataset"] = None

# SIDEBAR
st.sidebar.title("Navigation")

task = st.sidebar.radio(
    "Select a Task",
    [
        "Home",
        "Task 1 - Web Scraping",
        "Task 2 - Exploratory Data Analysis",
        "Task 3 - Data Visualization",
        "Task 4 - Sentiment Analysis"
    ],
    key="navigation"
)

# HOME
if task == "Home":

    st.header("Data Analytics Projects")

    st.write(
        "This website contains all four tasks "
        "completed during my Data Analytics Internship."
    )

    st.subheader("Explore Our Projects")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🌐 Task 1 - Web Scraping",
            use_container_width=True
        ):
            st.session_state["navigation"] = "Task 1 - Web Scraping"
            st.rerun()

        if st.button(
            "📈 Task 2 - Exploratory Data Analysis",
            use_container_width=True
        ):
            st.session_state["navigation"] = "Task 2 - Exploratory Data Analysis"
            st.rerun()

    with col2:

        if st.button(
            "📊 Task 3 - Data Visualization",
            use_container_width=True
        ):
            st.session_state["navigation"] = "Task 3 - Data Visualization"
            st.rerun()

        if st.button(
            "💬 Task 4 - Sentiment Analysis",
            use_container_width=True
        ):
            st.session_state["navigation"] = "Task 4 - Sentiment Analysis"
            st.rerun()


# TASK 1 - WEB SCRAPING
elif task == "Task 1 - Web Scraping":

    st.header("🌐 Web Scraping")

    st.write("Collect book information using Python.")

    pages = st.slider(
        "Number of pages to scrape",
        min_value=1,
        max_value=50,
        value=50
    )

    if st.button("Start Web Scraping"):

        books = []

        progress = st.progress(0)
        status = st.empty()

        try:
            for page in range(1, pages + 1):

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

                    rating = (
                        rating_element.get("class", ["", "Unknown"])[1]
                    )

                    book_url = urljoin(
                        url,
                        book.h3.a["href"]
                    )

                    books.append({
                        "Title": title,
                        "Price": price,
                        "Availability": availability,
                        "Rating": rating,
                        "URL": book_url
                    })

                progress.progress(page / pages)
                status.write(f"Scraping page {page} of {pages}")

            df = pd.DataFrame(books)

            st.session_state["books_data"] = df
            st.session_state["dataset"] = df

            st.success(
                f"Successfully scraped {len(df)} books!"
            )

        except requests.RequestException as e:
            st.error(f"Network error: {e}")

        except Exception as e:
            st.error(f"Scraping failed: {e}")

    if st.session_state["books_data"] is not None:

        df = st.session_state["books_data"]

        st.subheader("Scraped Book Data")

        st.dataframe(
            df,
            use_container_width=True
        )

        st.metric("Total Books", len(df))

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download CSV",
            csv,
            "books_data.csv",
            "text/csv"
        )


# TASK 2 - EDA
elif task == "Task 2 - Exploratory Data Analysis":

    st.header("📈 Exploratory Data Analysis")

    st.write("Upload a CSV file to analyze your dataset.")

    uploaded_file = st.file_uploader(
        "Upload CSV File (Optional)",
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

        st.dataframe(df.head(10))

        col1, col2, col3 = st.columns(3)

        col1.metric("Rows", df.shape[0])
        col2.metric("Columns", df.shape[1])

        col3.metric(
            "Missing Values",
            int(df.isnull().sum().sum())
        )

        st.subheader("Dataset Information")

        st.write(df.dtypes.astype(str))

        st.subheader("Statistical Summary")

        st.dataframe(
            df.describe(include="all")
        )

        st.subheader("Missing Values")

        st.dataframe(df.isnull().sum())

        st.subheader("Duplicate Rows")

        st.write(int(df.duplicated().sum()))

    else:
        st.info("Run Task 1 first or upload a CSV file.")


# TASK 3 - DATA VISUALIZATION
elif task == "Task 3 - Data Visualization":

    st.header("📊 Data Visualization")

    st.write("Create charts and graphs from your dataset.")

    uploaded_file = st.file_uploader(
        "Upload CSV File (Optional)",
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

            ax.hist(
                df[column].dropna(),
                bins=15
            )

            ax.set_xlabel(column)
            ax.set_ylabel("Frequency")
            ax.set_title(f"Distribution of {column}")

            st.pyplot(fig)

            plt.close(fig)

            st.subheader("Correlation Matrix")

            if len(numeric_columns) > 1:

                correlation = df[numeric_columns].corr()

                st.dataframe(correlation)

            else:
                st.info(
                    "At least two numeric columns are needed."
                )

        else:
            st.warning(
                "No numeric columns found in this dataset."
            )

    else:
        st.info("Run Task 1 first or upload a CSV file.")


# TASK 4 - SENTIMENT ANALYSIS
elif task == "Task 4 - Sentiment Analysis":

    st.header("💬 Sentiment Analysis")

    st.write(
        "Analyze text reviews and identify their sentiment."
    )

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

    review = st.text_area(
        "Enter your review here:"
    )

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


# FOOTER
st.sidebar.markdown("---")

st.sidebar.write("----")

st.sidebar.write("Develepod by Manasiga Murugesan")
```
