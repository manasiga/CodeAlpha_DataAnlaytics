import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from textblob import TextBlob

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BookLens",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "books" not in st.session_state:
    st.session_state.books = pd.DataFrame()

if "selected_book" not in st.session_state:
    st.session_state.selected_book = None


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #090d1c, #11152b, #19132f);
    color: white;
}

[data-testid="stSidebar"] {
    background: #101329;
    border-right: 1px solid #302957;
}

h1, h2, h3 {
    color: white !important;
}

p, label, span {
    color: #d4d5e8;
}

.hero {
    padding: 40px;
    border-radius: 22px;
    background: linear-gradient(120deg, #30205f, #171d40, #43236b);
    border: 1px solid #59418c;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 40px;
}

.book-card {
    background: #171a34;
    border: 1px solid #34345c;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 12px;
}

.metric-card {
    background: linear-gradient(135deg, #24204a, #191b38);
    border: 1px solid #51417c;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

.metric-card h2 {
    color: #c9a7ff !important;
}

.stButton > button {
    background: linear-gradient(90deg, #7545c8, #a05be7);
    color: white;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #9d70ec;
    color: white;
}

[data-testid="stMetric"] {
    background: #1b1d39;
    border: 1px solid #423766;
    padding: 15px;
    border-radius: 12px;
}

hr {
    border-color: #393453;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown("## 📚 BookLens")
    st.caption("Discover • Explore • Analyze")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Home", "📊 Dashboard"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Book Data Analytics Platform")


# =====================================================
# GOOGLE BOOKS PRICE LOOKUP
# =====================================================

def get_google_price(title, author):

    try:

        query = f'intitle:"{title}"'

        if author and author != "Not Available":
            query += f' inauthor:"{author.split(",")[0]}"'

        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={
                "q": query,
                "maxResults": 5,
                "printType": "books"
            },
            headers={
                "User-Agent": "BookLens Educational Project"
            },
            timeout=8
        )

        if response.status_code != 200:
            return None, "", ""

        items = response.json().get("items", [])

        best_match = None
        best_score = 0

        for item in items:

            info = item.get("volumeInfo", {})
            google_title = info.get("title", "")

            title_score = SequenceMatcher(
                None,
                title.lower().strip(),
                google_title.lower().strip()
            ).ratio()

            if title_score > best_score:
                best_score = title_score
                best_match = item

        if best_match is None or best_score < 0.85:
            return None, "", ""

        sale = best_match.get("saleInfo", {})

        retail = sale.get("retailPrice", {})

        if (
            sale.get("saleability") == "FOR_SALE"
            and retail.get("amount") is not None
        ):

            return (
                retail["amount"],
                retail.get("currencyCode", ""),
                sale.get("buyLink", "")
            )

        return None, "", ""

    except requests.RequestException:
        return None, "", ""

    except (ValueError, TypeError):
        return None, "", ""


# =====================================================
# COLLECT BOOKS
# =====================================================

def collect_books(max_books=2000):

    books = []
    seen = set()

    categories = [
        "fiction",
        "science",
        "technology",
        "business",
        "history",
        "fantasy",
        "romance",
        "education",
        "biography",
        "computer science",
        "art",
        "literature",
        "philosophy",
        "psychology",
        "medicine",
        "engineering",
        "mathematics",
        "mystery",
        "adventure",
        "children",
        "poetry",
        "economics",
        "travel",
        "environment",
        "programming",
        "music",
        "politics",
        "sports",
        "cooking",
        "health"
    ]

    session = requests.Session()

    session.headers.update({
        "User-Agent": "BookLens/1.0 Educational Project"
    })

    progress = st.progress(0)
    status = st.empty()

    for category_index, category in enumerate(categories):

        if len(books) >= max_books:
            break

        for page_number in range(1, 11):

            if len(books) >= max_books:
                break

            status.info(
                f"Collecting {category.title()} books: "
                f"{len(books)} / {max_books}"
            )

            try:

                response = session.get(
                    "https://openlibrary.org/search.json",
                    params={
                        "q": category,
                        "page": page_number,
                        "limit": 100,
                        "fields": (
                            "key,title,author_name,first_publish_year,"
                            "subject,cover_i,ratings_average,"
                            "ratings_count,edition_count"
                        )
                    },
                    timeout=30
                )

                if response.status_code == 429:
                    time.sleep(3)
                    continue

                response.raise_for_status()

                items = response.json().get("docs", [])

                if not items:
                    break

                for item in items:

                    book_id = item.get("key")

                    if not book_id or book_id in seen:
                        continue

                    title = item.get(
                        "title",
                        "Unknown Title"
                    )

                    authors = item.get("author_name", [])

                    author = (
                        ", ".join(authors[:3])
                        if authors
                        else "Not Available"
                    )

                    year = item.get(
                        "first_publish_year"
                    )

                    rating = item.get(
                        "ratings_average"
                    )

                    subjects = item.get("subject", [])

                    category_name = (
                        ", ".join(subjects[:3])
                        if subjects
                        else category.title()
                    )

                    cover_id = item.get("cover_i")

                    image_url = (
                        f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                        if cover_id
                        else ""
                    )

                    description = (
                        f"{title} by {author}. "
                        f"Category: {category_name}. "
                        f"First published: {year or 'Not Available'}."
                    )

                    books.append({

                        "Book ID": book_id,
                        "Title": title,
                        "Author": author,
                        "Price": None,
                        "Currency": "",
                        "Price Type": "",
                        "Actual Price": None,
                        "Estimated Price": None,
                        "Rating": rating,
                        "Category": category_name,
                        "Publication Year": year,
                        "Availability": "Catalogued",
                        "Description": description,
                        "URL": "https://openlibrary.org" + book_id,
                        "Buy Link": "",
                        "Image": image_url

                    })

                    seen.add(book_id)

                    if len(books) >= max_books:
                        break

                time.sleep(0.15)

            except requests.RequestException:
                time.sleep(2)
                break

        progress.progress(
            min((category_index + 1) / len(categories), 1.0)
        )

    progress.empty()
    status.empty()

    df = pd.DataFrame(books)

    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=["Title", "Author"]
    ).reset_index(drop=True)

    return df


# =====================================================
# PRICE ENRICHMENT
# =====================================================

def update_book_prices(df):

    if df.empty:
        return df

    df = df.copy()

    progress = st.progress(0)
    status = st.empty()

    total = len(df)

    def lookup(row):

        return get_google_price(
            str(row["Title"]),
            str(row["Author"])
        )

    # Google Books requests are performed concurrently.
    # If a price is unavailable, use a clearly labelled estimate.

    with ThreadPoolExecutor(max_workers=5) as executor:

        futures = {
            executor.submit(lookup, row): index
            for index, row in df.iterrows()
        }

        completed = 0

        for future in as_completed(futures):

            index = futures[future]

            try:
                actual_price, currency, buy_link = future.result()
            except Exception:
                actual_price, currency, buy_link = None, "", ""

            if actual_price is not None:

                df.at[index, "Price"] = actual_price
                df.at[index, "Currency"] = currency
                df.at[index, "Price Type"] = "Actual"
                df.at[index, "Actual Price"] = actual_price
                df.at[index, "Estimated Price"] = None
                df.at[index, "Buy Link"] = buy_link

            else:

                # Estimate based on a fixed sample assumption.
                # This is NOT a real market price.

                estimated_price = 300.00

                df.at[index, "Price"] = estimated_price
                df.at[index, "Currency"] = "INR"
                df.at[index, "Price Type"] = "Estimated"
                df.at[index, "Actual Price"] = None
                df.at[index, "Estimated Price"] = estimated_price

            completed += 1

            if completed % 10 == 0 or completed == total:

                progress.progress(completed / total)

                status.info(
                    f"Checking prices: {completed} / {total}"
                )

    progress.empty()
    status.empty()

    return df


# =====================================================
# PRICE FORMAT
# =====================================================

def format_price(price, currency):

    try:

        if price is None or pd.isna(price):
            return "Price Not Available"

        return f"{currency} {float(price):,.2f}"

    except (ValueError, TypeError):
        return "Price Not Available"


# =====================================================
# CHART HELPER
# =====================================================

def show_histogram(data, title, xlabel, ylabel):

    if len(data) == 0:
        return

    fig, ax = plt.subplots(figsize=(9, 4))

    ax.hist(
        data,
        bins=10,
        edgecolor="white"
    )

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    st.pyplot(fig)
    plt.close(fig)


# =====================================================
# HOME PAGE
# =====================================================

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">
        <h1>📚 Welcome to BookLens</h1>
        <p>Discover Books. Explore Data. Understand Insights.</p>
        <p>
        A smart platform for collecting, analyzing
        and visualizing book data.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # BOOK COLLECTION

    st.markdown("## 🌐 Book Collection")

    st.write(
        "Collect books from different categories around the world."
    )

    col1, col2 = st.columns([2, 1])

    with col1:

        number_of_books = st.selectbox(
            "Select Number of Books",
            [100, 200, 500, 1000, 1500, 2000],
            index=5
        )

    with col2:

        st.write("")
        st.write("")

        collect_button = st.button(
            "🔍 Collect Books",
            use_container_width=True
        )

    if collect_button:

        with st.spinner("Collecting books..."):

            result = collect_books(number_of_books)

            if result.empty:

                st.error(
                    "Book collection failed. "
                    "Please check your internet connection "
                    "or Open Library API availability."
                )

            else:

                st.success(
                    f"{len(result)} books collected. "
                    "Now checking actual prices..."
                )

                result = update_book_prices(result)

                st.session_state.books = result
                st.session_state.selected_book = None

                actual_count = (
                    result["Price Type"] == "Actual"
                ).sum()

                estimated_count = (
                    result["Price Type"] == "Estimated"
                ).sum()

                st.success(
                    f"Collection completed! "
                    f"{len(result)} books | "
                    f"{actual_count} actual prices | "
                    f"{estimated_count} estimated prices."
                )

                if len(result) < number_of_books:

                    st.warning(
                        f"Requested {number_of_books} books, "
                        f"but only {len(result)} unique books "
                        "were returned by the API."
                    )

    # CSV UPLOAD

    with st.expander("📁 Upload Your Own Book CSV"):

        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"]
        )

        if uploaded_file is not None:

            try:

                uploaded_df = pd.read_csv(uploaded_file)

                st.session_state.books = uploaded_df
                st.session_state.selected_book = None

                st.success("CSV uploaded successfully!")

            except Exception as error:

                st.error(f"CSV error: {error}")

    books = st.session_state.books

    # EXPLORE BOOKS

    st.markdown("---")
    st.markdown("## 📖 Explore Books")

    if not books.empty:

        st.metric(
            "Total Books",
            len(books)
        )

        search = st.text_input(
            "🔎 Search by Book Title or Author"
        )

        filtered = books.copy()

        if search:

            title_match = filtered["Title"].astype(str).str.contains(
                search,
                case=False,
                na=False
            )

            author_match = filtered["Author"].astype(str).str.contains(
                search,
                case=False,
                na=False
            )

            filtered = filtered[
                title_match | author_match
            ]

        st.caption(
            f"Showing {len(filtered)} books"
        )

        for index, book in filtered.iterrows():

            st.markdown(
                '<div class="book-card">',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns([4, 1])

            with c1:

                st.markdown(
                    f"### 📘 {book.get('Title', 'Unknown Title')}"
                )

                st.write(
                    f"✍️ Author: {book.get('Author', 'Not Available')}"
                )

                st.write(
                    "💰 Price: "
                    + format_price(
                        book.get("Price"),
                        book.get("Currency", "")
                    )
                )

                st.write(
                    f"🏷️ Price Type: {book.get('Price Type', 'Not Available')}"
                )

                st.write(
                    f"⭐ Rating: {book.get('Rating', 'Not Available')}"
                )

            with c2:

                st.write("")

                if st.button(
                    "View Details",
                    key=f"details_{index}"
                ):

                    st.session_state.selected_book = index

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

        # BOOK DETAILS

        selected = st.session_state.selected_book

        if selected is not None and selected in books.index:

            book = books.loc[selected]

            st.markdown("---")
            st.markdown("## 📚 Book Details")

            image_url = book.get("Image", "")

            if isinstance(image_url, str) and image_url:

                st.image(
                    image_url,
                    width=180
                )

            st.markdown(
                f"### {book.get('Title', 'Unknown Title')}"
            )

            st.write(
                f"**Author:** {book.get('Author', 'Not Available')}"
            )

            st.write(
                f"**Price:** {format_price(book.get('Price'), book.get('Currency', ''))}"
            )

            st.write(
                f"**Price Type:** {book.get('Price Type', 'Not Available')}"
            )

            st.write(
                f"**Actual Price:** {format_price(book.get('Actual Price'), book.get('Currency', ''))}"
            )

            st.write(
                f"**Estimated Price:** {format_price(book.get('Estimated Price'), 'INR')}"
            )

            st.write(
                f"**Rating:** {book.get('Rating', 'Not Available')}"
            )

            st.write(
                f"**Category:** {book.get('Category', 'Not Available')}"
            )

            st.write(
                f"**Publication Year:** {book.get('Publication Year', 'Not Available')}"
            )

            st.write(
                f"**Availability:** {book.get('Availability', 'Not Available')}"
            )

            st.markdown("### Description")

            st.write(
                book.get(
                    "Description",
                    "Description not available."
                )
            )

            book_url = book.get("URL", "")

            if isinstance(book_url, str) and book_url:

                st.link_button(
                    "View Book Information",
                    book_url
                )

            buy_link = book.get("Buy Link", "")

            if isinstance(buy_link, str) and buy_link:

                st.link_button(
                    "Buy This Book",
                    buy_link
                )

    else:

        st.info(
            "Click Collect Books to start collecting book data."
        )

    # CSV DOWNLOAD

    if not books.empty:

        st.markdown("---")
        st.markdown("## 📥 Export Book Data")

        st.download_button(
            "⬇️ Download Books CSV",
            data=books.to_csv(index=False).encode("utf-8"),
            file_name="booklens_books.csv",
            mime="text/csv"
        )

    # EDA

    st.markdown("---")
    st.markdown("## 🔍 Exploratory Data Analysis")

    if not books.empty:

        st.dataframe(
            books,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Data Quality")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Missing Values",
            int(books.isnull().sum().sum())
        )

        c2.metric(
            "Duplicate Rows",
            int(books.duplicated().sum())
        )

        c3.metric(
            "Unique Books",
            len(books.drop_duplicates(
                subset=["Title", "Author"]
            ))
        )

        numeric_columns = books.select_dtypes(
            include="number"
        )

        if not numeric_columns.empty:

            st.markdown("### Statistical Summary")

            st.dataframe(
                numeric_columns.describe(),
                use_container_width=True
            )

    else:

        st.info("Collect books to perform EDA.")

    # DATA VISUALIZATION

    st.markdown("---")
    st.markdown("## 📊 Data Visualization")

    if not books.empty:

        if "Rating" in books.columns:

            ratings = pd.to_numeric(
                books["Rating"],
                errors="coerce"
            ).dropna()

            show_histogram(
                ratings,
                "Book Rating Distribution",
                "Rating",
                "Number of Books"
            )

        if "Category" in books.columns:

            categories = (
                books["Category"]
                .fillna("Unknown")
                .value_counts()
                .head(10)
            )

            if not categories.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                categories.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title("Top Book Categories")
                ax.set_xlabel("Category")
                ax.set_ylabel("Number of Books")

                plt.xticks(rotation=35, ha="right")

                st.pyplot(fig)
                plt.close(fig)

        if "Price Type" in books.columns:

            price_types = books["Price Type"].value_counts()

            fig, ax = plt.subplots(figsize=(8, 4))

            price_types.plot(
                kind="bar",
                ax=ax
            )

            ax.set_title("Actual vs Estimated Prices")
            ax.set_ylabel("Number of Books")

            st.pyplot(fig)
            plt.close(fig)

        if "Publication Year" in books.columns:

            years = pd.to_numeric(
                books["Publication Year"],
                errors="coerce"
            ).dropna()

            show_histogram(
                years,
                "Publication Year Distribution",
                "Year",
                "Number of Books"
            )

    else:

        st.info("Collect books to view visualizations.")

    # SENTIMENT ANALYSIS

    st.markdown("---")
    st.markdown("## 💬 Sentiment Analysis")

    if not books.empty and "Description" in books.columns:

        descriptions = (
            books["Description"]
            .fillna("")
            .astype(str)
        )

        scores = descriptions.apply(
            lambda value: (
                TextBlob(value).sentiment.polarity
                if value.strip()
                else 0
            )
        )

        labels = scores.apply(
            lambda value:
            "Positive" if value > 0
            else "Negative" if value < 0
            else "Neutral"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Positive",
            int((labels == "Positive").sum())
        )

        c2.metric(
            "Neutral",
            int((labels == "Neutral").sum())
        )

        c3.metric(
            "Negative",
            int((labels == "Negative").sum())
        )

        fig, ax = plt.subplots(figsize=(8, 4))

        labels.value_counts().plot(
            kind="bar",
            ax=ax
        )

        ax.set_title("Book Description Sentiment")
        ax.set_ylabel("Number of Books")

        st.pyplot(fig)
        plt.close(fig)

        sentiment_df = pd.DataFrame({
            "Title": books["Title"],
            "Sentiment Score": scores,
            "Sentiment": labels
        })

        st.dataframe(
            sentiment_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Description data is required for sentiment analysis."
        )


# =====================================================
# DASHBOARD
# =====================================================

elif page == "📊 Dashboard":

    st.markdown("""
    <div class="hero">
        <h1>📊 BookLens Dashboard</h1>
        <p>Book Data Analytics Overview</p>
    </div>
    """, unsafe_allow_html=True)

    books = st.session_state.books

    if books.empty:

        st.warning(
            "No data available. Go to Home and collect books first."
        )

    else:

        ratings = pd.to_numeric(
            books.get("Rating", pd.Series(dtype=float)),
            errors="coerce"
        ).dropna()

        prices = pd.to_numeric(
            books.get("Price", pd.Series(dtype=float)),
            errors="coerce"
        ).dropna()

        actual_count = (
            int((books["Price Type"] == "Actual").sum())
            if "Price Type" in books.columns
            else 0
        )

        estimated_count = (
            int((books["Price Type"] == "Estimated").sum())
            if "Price Type" in books.columns
            else 0
        )

        average_rating = (
            ratings.mean()
            if not ratings.empty
            else None
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total Books",
            len(books)
        )

        c2.metric(
            "Books With Ratings",
            len(ratings)
        )

        c3.metric(
            "Average Rating",
            f"{average_rating:.2f}"
            if average_rating is not None
            else "N/A"
        )

        c4.metric(
            "Books With Price",
            len(prices)
        )

        st.markdown("---")
        st.markdown("## 💰 Price Overview")

        p1, p2 = st.columns(2)

        p1.metric(
            "Actual Price Books",
            actual_count
        )

        p2.metric(
            "Estimated Price Books",
            estimated_count
        )

        if "Price Type" in books.columns:

            fig, ax = plt.subplots(figsize=(8, 4))

            books["Price Type"].value_counts().plot(
                kind="bar",
                ax=ax
            )

            ax.set_title("Actual vs Estimated Prices")
            ax.set_ylabel("Books")

            st.pyplot(fig)
            plt.close(fig)

        st.markdown("---")
        st.markdown("## 📈 Book Analytics")

        if not ratings.empty:

            show_histogram(
                ratings,
                "Rating Distribution",
                "Rating",
                "Number of Books"
            )

        if "Category" in books.columns:

            category_data = (
                books["Category"]
                .fillna("Unknown")
                .value_counts()
                .head(10)
            )

            if not category_data.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                category_data.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title("Top Book Categories")
                ax.set_ylabel("Books")

                plt.xticks(rotation=35, ha="right")

                st.pyplot(fig)
                plt.close(fig)

        if "Publication Year" in books.columns:

            years = pd.to_numeric(
                books["Publication Year"],
                errors="coerce"
            ).dropna()

            show_histogram(
                years,
                "Publication Year Distribution",
                "Year",
                "Books"
            )

        st.markdown("---")
        st.markdown("## 📚 Complete Book Dataset")

        st.dataframe(
            books,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Dashboard Data",
            data=books.to_csv(index=False).encode("utf-8"),
            file_name="booklens_dashboard.csv",
            mime="text/csv"
        )
