import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
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

# =====================================================
# SESSION STATE
# =====================================================

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
    color: #ffffff;
}

[data-testid="stSidebar"] {
    background: #101329;
    border-right: 1px solid #302957;
}

h1, h2, h3 {
    color: #ffffff !important;
}

p, label, span {
    color: #d4d5e8;
}

.hero {
    padding: 45px 35px;
    border-radius: 22px;
    background: linear-gradient(120deg, #30205f, #171d40, #43236b);
    border: 1px solid #59418c;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 42px;
    color: white;
}

.hero p {
    font-size: 17px;
    color: #e1dafa;
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
    font-size: 28px;
}

.metric-card p {
    color: #d8d5eb;
}

.stButton > button {
    background: linear-gradient(90deg, #7545c8, #a05be7);
    color: white;
    border: none;
    border-radius: 9px;
    padding: 9px 18px;
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
# SIDEBAR NAVIGATION
# =====================================================

with st.sidebar:

    st.markdown("## 📚 BookLens")
    st.caption("Explore Books Through Data")

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Home", "📊 Dashboard"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Discover • Explore • Analyze")


# =====================================================
# BOOK COLLECTION - OPEN LIBRARY API
# =====================================================

def collect_books(max_books=100):

    books = []
    seen_books = set()

    search_terms = [
        "fiction",
        "science",
        "technology",
        "business",
        "history",
        "fantasy",
        "romance",
        "education",
        "biography",
        "computer"
    ]

    headers = {
        "User-Agent": "BookLens/1.0 (Book Analytics Educational Project)"
    }

    for term in search_terms:

        if len(books) >= max_books:
            break

        remaining = max_books - len(books)

        params = {
            "q": term,
            "limit": min(100, remaining),
            "fields": (
                "key,title,author_name,first_publish_year,"
                "subject,cover_i,ratings_average,ratings_count,"
                "edition_count,has_fulltext"
            )
        }

        try:

            response = requests.get(
                "https://openlibrary.org/search.json",
                params=params,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            items = data.get("docs", [])

            for item in items:

                book_id = item.get("key", "")

                if not book_id or book_id in seen_books:
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

                subjects = item.get("subject", [])

                category = (
                    ", ".join(subjects[:3])
                    if subjects
                    else term.title()
                )

                year = item.get(
                    "first_publish_year",
                    "Not Available"
                )

                rating = item.get("ratings_average")

                cover_id = item.get("cover_i")

                image = (
                    f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                    if cover_id
                    else ""
                )

                description = (
                    f"{title} by {author}. "
                    f"First published in {year}. "
                    f"Category: {category}."
                )

                book_url = (
                    "https://openlibrary.org" + book_id
                )

                books.append({

                    "Book ID": book_id,
                    "Title": title,
                    "Author": author,
                    "Price": None,
                    "Currency": "",
                    "Rating": rating,
                    "Category": category,
                    "Publication Year": year,
                    "Availability": (
                        "Full Text Available"
                        if item.get("has_fulltext")
                        else "Catalogued"
                    ),
                    "Description": description,
                    "URL": book_url,
                    "Image": image

                })

                seen_books.add(book_id)

                if len(books) >= max_books:
                    break

        except requests.RequestException as e:

            st.warning(
                f"Unable to collect {term} books: {e}"
            )

        except (ValueError, TypeError) as e:

            st.warning(
                f"Unable to process {term} book data: {e}"
            )

    df = pd.DataFrame(books)

    if not df.empty:

        df = df.drop_duplicates(
            subset=["Title", "Author"]
        )

        df = df.reset_index(drop=True)

    return df


# =====================================================
# HELPER FUNCTION
# =====================================================

def safe_number(value):

    try:
        if pd.isna(value):
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


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
        and visualizing book data from different categories.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # =================================================
    # BOOK COLLECTION
    # =================================================

    st.markdown("## 🌐 Book Collection")

    st.write(
        "Discover and collect books from different categories "
        "around the world."
    )

    col1, col2 = st.columns([2, 1])

    with col1:

        number_of_books = st.selectbox(
            "Select number of books",
            [20, 50, 100, 200]
        )

    with col2:

        st.write("")
        st.write("")

        collect_button = st.button(
            "🔍 Collect Books",
            use_container_width=True
        )

    if collect_button:

        with st.spinner(
            "Collecting books from Open Library..."
        ):

            result = collect_books(number_of_books)

            if result.empty:

                st.error(
                    "Books could not be collected. "
                    "Please check your internet connection "
                    "and try again."
                )

            else:

                st.session_state.books = result
                st.session_state.selected_book = None

                st.success(
                    f"{len(result)} books collected successfully!"
                )

    # =================================================
    # CSV UPLOAD
    # =================================================

    with st.expander("📁 Upload Your Own Book CSV (Optional)"):

        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            key="book_upload"
        )

        if uploaded_file is not None:

            try:

                uploaded_df = pd.read_csv(uploaded_file)

                st.session_state.books = uploaded_df
                st.session_state.selected_book = None

                st.success(
                    "CSV uploaded successfully!"
                )

            except Exception as e:

                st.error(
                    f"Unable to read CSV: {e}"
                )

    books = st.session_state.books

    # =================================================
    # EXPLORE BOOKS
    # =================================================

    st.markdown("---")
    st.markdown("## 📖 Explore Books")

    if not books.empty:

        st.write(
            f"Total Books: **{len(books)}**"
        )

        search = st.text_input(
            "🔎 Search by book title or author"
        )

        filtered = books.copy()

        if search:

            title_match = filtered.get(
                "Title",
                pd.Series("", index=filtered.index)
            ).astype(str).str.contains(
                search,
                case=False,
                na=False
            )

            author_match = filtered.get(
                "Author",
                pd.Series("", index=filtered.index)
            ).astype(str).str.contains(
                search,
                case=False,
                na=False
            )

            filtered = filtered[
                title_match | author_match
            ]

        if "Price" in filtered.columns:

            filtered["Price"] = pd.to_numeric(
                filtered["Price"],
                errors="coerce"
            )

            filtered = filtered.sort_values(
                by="Price",
                ascending=False,
                na_position="last"
            )

        st.caption(
            "Explore books and open individual book details."
        )

        for index, book in filtered.iterrows():

            title = book.get(
                "Title",
                "Unknown Title"
            )

            author = book.get(
                "Author",
                "Not Available"
            )

            price = safe_number(
                book.get("Price")
            )

            currency = book.get(
                "Currency",
                ""
            )

            rating = book.get(
                "Rating",
                "Not Available"
            )

            st.markdown(
                '<div class="book-card">',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns([4, 1])

            with col1:

                st.markdown(
                    f"### 📘 {title}"
                )

                st.write(
                    f"✍️ Author: {author}"
                )

                if price is not None:

                    st.write(
                        f"💰 Price: {currency} {price:,.2f}"
                    )

                else:

                    st.write(
                        "💰 Price: Not Available"
                    )

                st.write(
                    f"⭐ Rating: {rating}"
                )

            with col2:

                st.write("")

                if st.button(
                    "View Details",
                    key=f"details_{index}"
                ):

                    st.session_state.selected_book = book.get(
                        "Book ID",
                        index
                    )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

        # =================================================
        # BOOK DETAILS
        # =================================================

        selected = st.session_state.selected_book

        if selected is not None:

            selected_rows = books[
                books.get(
                    "Book ID",
                    pd.Series(index=books.index, dtype=str)
                ).astype(str) == str(selected)
            ] if "Book ID" in books.columns else pd.DataFrame()

            if not selected_rows.empty:

                book = selected_rows.iloc[0]

                st.markdown("---")
                st.markdown("## 📚 Book Details")

                st.markdown(
                    f"### {book.get('Title', 'Unknown Title')}"
                )

                image = book.get("Image", "")

                if isinstance(image, str) and image:

                    st.image(
                        image,
                        width=180
                    )

                st.write(
                    f"**Author:** {book.get('Author', 'Not Available')}"
                )

                price = safe_number(
                    book.get("Price")
                )

                if price is not None:

                    st.write(
                        f"**Price:** {book.get('Currency', '')} {price:,.2f}"
                    )

                else:

                    st.write(
                        "**Price:** Not Available"
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

    else:

        st.info(
            "Click Collect Books to start collecting book data."
        )

    # =================================================
    # CSV DOWNLOAD
    # =================================================

    if not books.empty:

        st.markdown("---")
        st.markdown("## 📥 Export Book Data")

        csv_data = books.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Books CSV",
            data=csv_data,
            file_name="booklens_books.csv",
            mime="text/csv"
        )

    # =================================================
    # EXPLORATORY DATA ANALYSIS
    # =================================================

    st.markdown("---")
    st.markdown("## 🔍 Exploratory Data Analysis")

    if not books.empty:

        st.write(
            "Explore the structure and quality of collected book data."
        )

        st.dataframe(
            books,
            use_container_width=True,
            hide_index=True
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

        st.markdown("### Data Quality")

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Missing Values",
                int(books.isnull().sum().sum())
            )

        with c2:

            st.metric(
                "Duplicate Rows",
                int(books.duplicated().sum())
            )

    else:

        st.info(
            "Collect books to explore the dataset."
        )

    # =================================================
    # DATA VISUALIZATION
    # =================================================

    st.markdown("---")
    st.markdown("## 📊 Data Visualization")

    if not books.empty:

        # RATING DISTRIBUTION

        if "Rating" in books.columns:

            rating_data = pd.to_numeric(
                books["Rating"],
                errors="coerce"
            ).dropna()

            if not rating_data.empty:

                fig, ax = plt.subplots(figsize=(9, 4))

                ax.hist(
                    rating_data,
                    bins=10,
                    edgecolor="white"
                )

                ax.set_title(
                    "Book Rating Distribution"
                )

                ax.set_xlabel("Rating")
                ax.set_ylabel("Number of Books")

                st.pyplot(fig)
                plt.close(fig)

        # CATEGORY ANALYSIS

        if "Category" in books.columns:

            category_data = books[
                "Category"
            ].fillna("Unknown").value_counts().head(10)

            if not category_data.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                category_data.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title(
                    "Top Book Categories"
                )

                ax.set_xlabel("Category")
                ax.set_ylabel("Number of Books")

                plt.xticks(
                    rotation=35,
                    ha="right"
                )

                st.pyplot(fig)
                plt.close(fig)

        # PUBLICATION YEAR

        if "Publication Year" in books.columns:

            years = pd.to_numeric(
                books["Publication Year"],
                errors="coerce"
            ).dropna()

            if not years.empty:

                fig, ax = plt.subplots(figsize=(9, 4))

                ax.hist(
                    years,
                    bins=15,
                    edgecolor="white"
                )

                ax.set_title(
                    "Book Publication Year Distribution"
                )

                ax.set_xlabel("Publication Year")
                ax.set_ylabel("Number of Books")

                st.pyplot(fig)
                plt.close(fig)

    else:

        st.info(
            "Collect books to view visualizations."
        )

    # =================================================
    # SENTIMENT ANALYSIS
    # =================================================

    st.markdown("---")
    st.markdown("## 💬 Sentiment Analysis")

    if not books.empty and "Description" in books.columns:

        sentiment_text = books[
            "Description"
        ].fillna("").astype(str)

        sentiment_scores = sentiment_text.apply(
            lambda text:
            TextBlob(text).sentiment.polarity
            if text.strip()
            else 0
        )

        sentiment_labels = sentiment_scores.apply(
            lambda score:
            "Positive" if score > 0
            else "Negative" if score < 0
            else "Neutral"
        )

        sentiment_df = pd.DataFrame({

            "Title": books.get(
                "Title",
                pd.Series("Unknown", index=books.index)
            ),

            "Sentiment Score": sentiment_scores,

            "Sentiment": sentiment_labels

        })

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Positive",
            int((sentiment_labels == "Positive").sum())
        )

        c2.metric(
            "Neutral",
            int((sentiment_labels == "Neutral").sum())
        )

        c3.metric(
            "Negative",
            int((sentiment_labels == "Negative").sum())
        )

        fig, ax = plt.subplots(figsize=(8, 4))

        sentiment_labels.value_counts().plot(
            kind="bar",
            ax=ax
        )

        ax.set_title(
            "Book Description Sentiment"
        )

        ax.set_xlabel("Sentiment")
        ax.set_ylabel("Number of Books")

        st.pyplot(fig)
        plt.close(fig)

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
# DASHBOARD PAGE
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

        total_books = len(books)

        ratings = pd.to_numeric(
            books["Rating"],
            errors="coerce"
        ).dropna() if "Rating" in books.columns else pd.Series(dtype=float)

        average_rating = (
            ratings.mean()
            if not ratings.empty
            else None
        )

        if "Price" in books.columns:

            prices = pd.to_numeric(
                books["Price"],
                errors="coerce"
            ).dropna()

        else:

            prices = pd.Series(dtype=float)

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Total Books</p>
                    <h2>{total_books}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c2:

            rating_text = (
                f"{average_rating:.1f}"
                if average_rating is not None
                else "N/A"
            )

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Average Rating</p>
                    <h2>{rating_text}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c3:

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Books With Ratings</p>
                    <h2>{len(ratings)}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c4:

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Books With Price</p>
                    <h2>{len(prices)}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("## 📈 Dashboard Analytics")

        # RATING DISTRIBUTION

        if not ratings.empty:

            fig, ax = plt.subplots(figsize=(9, 4))

            ax.hist(
                ratings,
                bins=10,
                edgecolor="white"
            )

            ax.set_title(
                "Book Rating Distribution"
            )

            ax.set_xlabel("Rating")
            ax.set_ylabel("Books")

            st.pyplot(fig)
            plt.close(fig)

        # CATEGORY DISTRIBUTION

        if "Category" in books.columns:

            category_data = books[
                "Category"
            ].fillna("Unknown").value_counts().head(10)

            if not category_data.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                category_data.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title(
                    "Top Book Categories"
                )

                ax.set_xlabel("Category")
                ax.set_ylabel("Books")

                plt.xticks(
                    rotation=35,
                    ha="right"
                )

                st.pyplot(fig)
                plt.close(fig)

        # PUBLICATION YEAR

        if "Publication Year" in books.columns:

            years = pd.to_numeric(
                books["Publication Year"],
                errors="coerce"
            ).dropna()

            if not years.empty:

                fig, ax = plt.subplots(figsize=(9, 4))

                ax.hist(
                    years,
                    bins=15,
                    edgecolor="white"
                )

                ax.set_title(
                    "Publication Year Distribution"
                )

                ax.set_xlabel("Year")
                ax.set_ylabel("Books")

                st.pyplot(fig)
                plt.close(fig)

        # COMPLETE DATASET

        st.markdown("---")
        st.markdown("## 📚 Complete Book Dataset")

        st.dataframe(
            books,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Dashboard Data",
            data=books.to_csv(
                index=False
            ).encode("utf-8"),
            file_name="booklens_dashboard.csv",
            mime="text/csv"
        )
