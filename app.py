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
# SIDEBAR
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
# GOOGLE BOOKS DATA COLLECTION
# =====================================================

def collect_books(max_books=100):

    books = []

    search_terms = [
        "subject:fiction",
        "subject:business",
        "subject:technology",
        "subject:science",
        "subject:education",
        "subject:history",
        "subject:computer",
        "subject:romance",
        "subject:biography",
        "subject:fantasy"
    ]

    seen_books = set()

    for term in search_terms:

        start_index = 0

        while len(books) < max_books:

            url = "https://www.googleapis.com/books/v1/volumes"

            params = {
                "q": term,
                "maxResults": 40,
                "startIndex": start_index,
                "orderBy": "relevance"
            }

            try:

                response = requests.get(
                    url,
                    params=params,
                    timeout=20
                )

                if response.status_code != 200:
                    break

                data = response.json()

                items = data.get("items", [])

                if not items:
                    break

                for item in items:

                    book_id = item.get("id", "")

                    if book_id in seen_books:
                        continue

                    info = item.get("volumeInfo", {})
                    sale = item.get("saleInfo", {})

                    title = info.get(
                        "title",
                        "Unknown Title"
                    )

                    authors = info.get("authors", [])

                    author = (
                        ", ".join(authors)
                        if authors
                        else "Not Available"
                    )

                    categories = info.get("categories", [])

                    category = (
                        ", ".join(categories)
                        if categories
                        else "General"
                    )

                    # PRICE INFORMATION

                    price_info = sale.get("listPrice", {})

                    if not price_info:
                        price_info = sale.get("retailPrice", {})

                    price = price_info.get("amount")
                    currency = price_info.get("currencyCode", "")

                    if price is not None:
                        price = float(price)
                    else:
                        price = None

                    # RATING

                    rating = info.get("averageRating")

                    if rating is not None:
                        rating = float(rating)

                    # DESCRIPTION

                    description = info.get(
                        "description",
                        "Description not available."
                    )

                    # IMAGE

                    image_links = info.get("imageLinks", {})

                    image = image_links.get(
                        "thumbnail",
                        ""
                    )

                    # BOOK LINK

                    book_url = info.get(
                        "infoLink",
                        ""
                    )

                    # AVAILABILITY

                    availability = sale.get(
                        "saleability",
                        "Not Available"
                    )

                    books.append({

                        "Book ID": book_id,
                        "Title": title,
                        "Author": author,
                        "Price": price,
                        "Currency": currency,
                        "Rating": rating,
                        "Category": category,
                        "Availability": availability,
                        "Description": description,
                        "URL": book_url,
                        "Image": image

                    })

                    seen_books.add(book_id)

                    if len(books) >= max_books:
                        break

                start_index += 40

                if start_index >= 200:
                    break

            except requests.RequestException:
                break

        if len(books) >= max_books:
            break

    df = pd.DataFrame(books)

    if not df.empty:

        df = df.drop_duplicates(
            subset=["Title", "Author"]
        )

        df = df.reset_index(drop=True)

    return df


# =====================================================
# PRICE FORMAT
# =====================================================

def format_price(price, currency):

    if pd.isna(price):
        return "Price Not Available"

    currency = str(currency).strip()

    if not currency:
        currency = "Currency Not Available"

    try:
        return f"{currency} {float(price):,.2f}"
    except (ValueError, TypeError):
        return "Price Not Available"


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

        with st.spinner("Collecting books from Google Books..."):

            result = collect_books(number_of_books)

            if result.empty:

                st.warning(
                    "No books were returned. Please try again later."
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
            type=["csv"]
        )

        if uploaded_file is not None:

            try:

                uploaded_df = pd.read_csv(uploaded_file)

                st.session_state.books = uploaded_df
                st.session_state.selected_book = None

                st.success("CSV uploaded successfully!")

            except Exception as e:

                st.error(f"Unable to read CSV: {e}")

    books = st.session_state.books

    # =================================================
    # EXPLORE BOOKS
    # =================================================

    st.markdown("---")
    st.markdown("## 📖 Explore Books")

    if not books.empty:

        st.write(f"Total Books: **{len(books)}**")

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

            filtered = filtered.sort_values(
                by="Price",
                ascending=False,
                na_position="last"
            )

        st.caption("Books are arranged by price where price information is available.")

        for index, book in filtered.iterrows():

            title = book.get("Title", "Unknown Title")

            author = book.get(
                "Author",
                "Not Available"
            )

            price = book.get("Price")

            currency = book.get("Currency", "")

            rating = book.get("Rating", "Not Available")

            st.markdown(
                '<div class="book-card">',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns([4, 1])

            with col1:

                st.markdown(f"### 📘 {title}")

                st.write(f"✍️ Author: {author}")

                st.write(
                    f"💰 Price: {format_price(price, currency)}"
                )

                st.write(f"⭐ Rating: {rating}")

            with col2:

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

        # =================================================
        # BOOK DETAILS
        # =================================================

        selected = st.session_state.selected_book

        if selected is not None and selected in books.index:

            book = books.loc[selected]

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

            st.write(
                f"**Price:** {format_price(book.get('Price'), book.get('Currency', ''))}"
            )

            st.write(
                f"**Rating:** {book.get('Rating', 'Not Available')}"
            )

            st.write(
                f"**Category:** {book.get('Category', 'Not Available')}"
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
            "Understand the structure and quality of book data."
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

        st.info("Collect books to explore the dataset.")

    # =================================================
    # DATA VISUALIZATION
    # =================================================

    st.markdown("---")
    st.markdown("## 📊 Data Visualization")

    if not books.empty:

        # PRICE DISTRIBUTION BY CURRENCY

        if "Price" in books.columns:

            price_data = books.copy()

            price_data["Price"] = pd.to_numeric(
                price_data["Price"],
                errors="coerce"
            )

            if "Currency" not in price_data.columns:
                price_data["Currency"] = "Unknown"

            price_data = price_data.dropna(
                subset=["Price"]
            )

            if not price_data.empty:

                st.markdown("### Price Distribution by Currency")

                currencies = price_data["Currency"].fillna(
                    "Unknown"
                ).unique()

                for currency in currencies[:4]:

                    currency_data = price_data[
                        price_data["Currency"].fillna(
                            "Unknown"
                        ) == currency
                    ]

                    if currency_data.empty:
                        continue

                    fig, ax = plt.subplots(figsize=(9, 3))

                    ax.hist(
                        currency_data["Price"],
                        bins=12,
                        edgecolor="white"
                    )

                    ax.set_title(
                        f"Book Price Distribution - {currency}"
                    )

                    ax.set_xlabel(f"Price ({currency})")
                    ax.set_ylabel("Number of Books")

                    st.pyplot(fig)
                    plt.close(fig)

        # RATING DISTRIBUTION

        if "Rating" in books.columns:

            rating_data = pd.to_numeric(
                books["Rating"],
                errors="coerce"
            ).dropna()

            if not rating_data.empty:

                fig, ax = plt.subplots(figsize=(9, 4))

                rating_data.value_counts().sort_index().plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title("Book Rating Distribution")
                ax.set_xlabel("Rating")
                ax.set_ylabel("Number of Books")

                st.pyplot(fig)
                plt.close(fig)

        # CATEGORY ANALYSIS

        if "Category" in books.columns:

            category_data = books[
                "Category"
            ].value_counts().head(10)

            if not category_data.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                category_data.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title("Top Book Categories")
                ax.set_xlabel("Category")
                ax.set_ylabel("Number of Books")

                plt.xticks(
                    rotation=35,
                    ha="right"
                )

                st.pyplot(fig)
                plt.close(fig)

    else:

        st.info("Collect books to view visualizations.")

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
            lambda text: TextBlob(
                text
            ).sentiment.polarity if text.strip() else 0
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

        ax.set_title("Book Description Sentiment")
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

        if "Price" in books.columns:

            prices = pd.to_numeric(
                books["Price"],
                errors="coerce"
            )

        else:

            prices = pd.Series(
                index=books.index,
                dtype=float
            )

        if "Rating" in books.columns:

            ratings = pd.to_numeric(
                books["Rating"],
                errors="coerce"
            )

        else:

            ratings = pd.Series(
                index=books.index,
                dtype=float
            )

        available_prices = prices.dropna()

        average_rating = ratings.mean()

        books_with_price = len(available_prices)

        if "Availability" in books.columns:

            available_books = int(
                books["Availability"].astype(str).str.upper().eq(
                    "FOR_SALE"
                ).sum()
            )

        else:

            available_books = 0

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

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Books With Price</p>
                    <h2>{books_with_price}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c3:

            rating_text = (
                f"{average_rating:.1f}"
                if pd.notna(average_rating)
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

        with c4:

            st.markdown(
                f"""
                <div class="metric-card">
                    <p>Available For Sale</p>
                    <h2>{available_books}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("## 📈 Dashboard Analytics")

        # PRICE CHARTS

        if not available_prices.empty:

            price_df = books.copy()

            price_df["Price"] = pd.to_numeric(
                price_df["Price"],
                errors="coerce"
            )

            if "Currency" not in price_df.columns:
                price_df["Currency"] = "Unknown"

            st.markdown("### Price Distribution by Currency")

            currencies = price_df["Currency"].fillna(
                "Unknown"
            ).unique()

            for currency in currencies[:4]:

                currency_data = price_df[
                    price_df["Currency"].fillna(
                        "Unknown"
                    ) == currency
                ]["Price"].dropna()

                if currency_data.empty:
                    continue

                fig, ax = plt.subplots(figsize=(9, 3))

                ax.hist(
                    currency_data,
                    bins=12,
                    edgecolor="white"
                )

                ax.set_title(f"Price Distribution - {currency}")
                ax.set_xlabel(f"Price ({currency})")
                ax.set_ylabel("Books")

                st.pyplot(fig)
                plt.close(fig)

        # RATING CHART

        if not ratings.dropna().empty:

            fig, ax = plt.subplots(figsize=(9, 4))

            ratings.dropna().value_counts().sort_index().plot(
                kind="bar",
                ax=ax
            )

            ax.set_title("Rating Distribution")
            ax.set_xlabel("Rating")
            ax.set_ylabel("Books")

            st.pyplot(fig)
            plt.close(fig)

        # CATEGORY CHART

        if "Category" in books.columns:

            category_data = books[
                "Category"
            ].value_counts().head(10)

            if not category_data.empty:

                fig, ax = plt.subplots(figsize=(9, 5))

                category_data.plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_title("Top Book Categories")
                ax.set_xlabel("Category")
                ax.set_ylabel("Books")

                plt.xticks(
                    rotation=35,
                    ha="right"
                )

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
