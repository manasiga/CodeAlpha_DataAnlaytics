import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import time
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
# CSS
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
h1,h2,h3 {color: white !important;}
p,label,span {color: #d4d5e8;}
.hero {
    padding: 40px;
    border-radius: 22px;
    background: linear-gradient(120deg,#30205f,#171d40,#43236b);
    border: 1px solid #59418c;
    margin-bottom: 25px;
}
.book-card {
    background: #171a34;
    border: 1px solid #34345c;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 12px;
}
.metric-card {
    background: linear-gradient(135deg,#24204a,#191b38);
    border: 1px solid #51417c;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}
.metric-card h2 {color: #c9a7ff !important;}
.stButton > button {
    background: linear-gradient(90deg,#7545c8,#a05be7);
    color: white;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}
[data-testid="stMetric"] {
    background: #1b1d39;
    border: 1px solid #423766;
    padding: 15px;
    border-radius: 12px;
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

# =====================================================
# GOOGLE BOOKS COLLECTION
# =====================================================

def collect_books(max_books=2000):

    books = []
    seen = set()

    categories = [
        "fiction", "science", "technology", "business",
        "history", "fantasy", "romance", "education",
        "biography", "computer science", "art",
        "literature", "philosophy", "psychology",
        "medicine", "engineering", "mathematics",
        "mystery", "adventure", "children",
        "poetry", "economics", "travel",
        "environment", "programming", "music",
        "politics", "sports", "cooking", "health"
    ]

    session = requests.Session()
    session.headers.update({
        "User-Agent": "BookLens Educational Project"
    })

    progress = st.progress(0)
    status = st.empty()

    total_categories = len(categories)

    for category_index, category in enumerate(categories):

        if len(books) >= max_books:
            break

        for page_number in range(2):

            if len(books) >= max_books:
                break

            status.info(
                f"Collecting {category.title()} books | "
                f"{len(books)} / {max_books}"
            )

            params = {
                "q": f"subject:{category}",
                "startIndex": page_number * 40,
                "maxResults": 40,
                "printType": "books"
            }

            try:
                response = session.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params=params,
                    timeout=25
                )

                if response.status_code == 429:
                    time.sleep(3)
                    continue

                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])

                if not items:
                    break

                for item in items:

                    volume_id = item.get("id")

                    if not volume_id or volume_id in seen:
                        continue

                    info = item.get("volumeInfo", {})
                    sale = item.get("saleInfo", {})

                    title = info.get("title", "Unknown Title")

                    authors = info.get("authors", [])
                    author = (
                        ", ".join(authors)
                        if authors else "Not Available"
                    )

                    description = info.get(
                        "description",
                        "Description not available."
                    )

                    published = info.get(
                        "publishedDate",
                        "Not Available"
                    )

                    rating = info.get(
                        "averageRating",
                        None
                    )

                    page_count = info.get("pageCount", None)

                    image_links = info.get("imageLinks", {})
                    image = image_links.get(
                        "thumbnail",
                        image_links.get("smallThumbnail", "")
                    )

                    categories_found = info.get("categories", [])
                    book_category = (
                        ", ".join(categories_found)
                        if categories_found else category.title()
                    )

                    # ACTUAL PRICE

                    actual_price = None
                    actual_currency = ""
                    price_type = "Estimated"
                    buy_link = ""

                    retail_price = sale.get("retailPrice", {})

                    if (
                        sale.get("saleability") == "FOR_SALE"
                        and retail_price.get("amount") is not None
                    ):
                        actual_price = retail_price.get("amount")
                        actual_currency = retail_price.get(
                            "currencyCode", ""
                        )
                        price_type = "Actual"

                    buy_link = sale.get(
                        "buyLink",
                        info.get("infoLink", "")
                    )

                    # ESTIMATED PRICE
                    # Estimate is not an actual market price.

                    if actual_price is None:

                        try:
                            pages = int(page_count or 200)

                            estimated_price = round(
                                max(150, 150 + pages * 0.75),
                                2
                            )

                        except (ValueError, TypeError):
                            estimated_price = 300.00

                        display_price = estimated_price
                        display_currency = "INR"

                    else:
                        display_price = actual_price
                        display_currency = actual_currency

                    books.append({
                        "Book ID": volume_id,
                        "Title": title,
                        "Author": author,
                        "Price": display_price,
                        "Currency": display_currency,
                        "Price Type": price_type,
                        "Actual Price": actual_price,
                        "Estimated Price": (
                            display_price
                            if price_type == "Estimated"
                            else None
                        ),
                        "Rating": rating,
                        "Category": book_category,
                        "Publication Year": published,
                        "Page Count": page_count,
                        "Availability": sale.get(
                            "saleability",
                            "Not Available"
                        ),
                        "Description": description,
                        "URL": info.get(
                            "infoLink",
                            f"https://books.google.com/books?id={volume_id}"
                        ),
                        "Buy Link": buy_link,
                        "Image": image
                    })

                    seen.add(volume_id)

                    if len(books) >= max_books:
                        break

                time.sleep(0.2)

            except requests.RequestException:
                time.sleep(1)
                continue

        progress.progress(
            min((category_index + 1) / total_categories, 1.0)
        )

    progress.empty()
    status.empty()

    df = pd.DataFrame(books)

    if not df.empty:
        df = df.drop_duplicates(
            subset=["Title", "Author"]
        ).reset_index(drop=True)

    return df

# =====================================================
# PRICE FORMAT
# =====================================================

def format_price(price, currency):

    try:
        if pd.isna(price):
            return "Price Not Available"

        return f"{currency} {float(price):,.2f}"

    except (ValueError, TypeError):
        return "Price Not Available"

# =====================================================
# HOME
# =====================================================

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">
        <h1>📚 Welcome to BookLens</h1>
        <p>Discover Books. Explore Data. Understand Insights.</p>
        <p>A smart platform for collecting, analyzing and visualizing book data.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🌐 Book Collection")

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

        with st.spinner("Collecting book data..."):

            result = collect_books(number_of_books)

            if result.empty:
                st.error(
                    "Books could not be collected. "
                    "Check your internet connection or API availability."
                )
            else:
                st.session_state.books = result
                st.session_state.selected_book = None

                st.success(
                    f"{len(result)} books collected successfully!"
                )

                if len(result) < number_of_books:
                    st.warning(
                        f"Requested {number_of_books} books, "
                        f"but the API returned {len(result)} unique books."
                    )

    # CSV UPLOAD

    with st.expander("📁 Upload Your Own CSV"):

        uploaded_file = st.file_uploader(
            "Upload book CSV",
            type=["csv"]
        )

        if uploaded_file is not None:

            try:
                uploaded_df = pd.read_csv(uploaded_file)
                st.session_state.books = uploaded_df
                st.session_state.selected_book = None
                st.success("CSV uploaded successfully!")

            except Exception as e:
                st.error(f"CSV error: {e}")

    books = st.session_state.books

    # BOOK SEARCH

    st.markdown("---")
    st.markdown("## 📖 Explore Books")

    if not books.empty:

        st.metric("Total Books", len(books))

        search = st.text_input(
            "🔎 Search by Book Title or Author"
        )

        filtered = books.copy()

        if search:

            title_match = filtered["Title"].astype(str).str.contains(
                search, case=False, na=False
            )

            author_match = filtered["Author"].astype(str).str.contains(
                search, case=False, na=False
            )

            filtered = filtered[title_match | author_match]

        st.caption(f"Showing {len(filtered)} books")

        for index, book in filtered.iterrows():

            with st.container():

                st.markdown(
                    '<div class="book-card">',
                    unsafe_allow_html=True
                )

                c1, c2 = st.columns([4, 1])

                with c1:

                    st.markdown(f"### 📘 {book.get('Title', '')}")

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

                st.markdown("</div>", unsafe_allow_html=True)

        # BOOK DETAILS

        selected = st.session_state.selected_book

        if selected is not None and selected in books.index:

            book = books.loc[selected]

            st.markdown("---")
            st.markdown("## 📚 Book Details")

            image_url = book.get("Image", "")

            if isinstance(image_url, str) and image_url:
                st.image(image_url, width=180)

            st.markdown(f"### {book.get('Title', '')}")

            st.write(f"**Author:** {book.get('Author', '')}")

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

            st.write(f"**Rating:** {book.get('Rating', 'Not Available')}")
            st.write(f"**Category:** {book.get('Category', 'Not Available')}")
            st.write(f"**Publication Year:** {book.get('Publication Year', 'Not Available')}")
            st.write(f"**Page Count:** {book.get('Page Count', 'Not Available')}")
            st.write(f"**Availability:** {book.get('Availability', 'Not Available')}")

            st.markdown("### Description")
            st.write(book.get("Description", "Not available"))

            if book.get("URL"):
                st.link_button("View Book Information", book["URL"])

            if book.get("Buy Link"):
                st.link_button("Buy This Book", book["Buy Link"])

    else:
        st.info("Click Collect Books to start collecting book data.")

    # DOWNLOAD

    if not books.empty:

        st.markdown("---")
        st.markdown("## 📥 Export Data")

        st.download_button(
            "⬇️ Download Books CSV",
            books.to_csv(index=False).encode("utf-8"),
            "booklens_books.csv",
            "text/csv"
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
            len(books.drop_duplicates(subset=["Title", "Author"]))
        )

        numeric = books.select_dtypes(include="number")

        if not numeric.empty:
            st.markdown("### Statistical Summary")
            st.dataframe(numeric.describe(), use_container_width=True)

    else:
        st.info("Collect books to perform EDA.")

    # VISUALIZATION

    st.markdown("---")
    st.markdown("## 📊 Data Visualization")

    if not books.empty:

        if "Rating" in books.columns:

            ratings = pd.to_numeric(
                books["Rating"], errors="coerce"
            ).dropna()

            if not ratings.empty:

                fig, ax = plt.subplots(figsize=(9, 4))
                ax.hist(ratings, bins=10, edgecolor="white")
                ax.set_title("Book Rating Distribution")
                ax.set_xlabel("Rating")
                ax.set_ylabel("Number of Books")
                st.pyplot(fig)
                plt.close(fig)

        if "Category" in books.columns:

            categories = books["Category"].fillna(
                "Unknown"
            ).value_counts().head(10)

            fig, ax = plt.subplots(figsize=(9, 5))
            categories.plot(kind="bar", ax=ax)
            ax.set_title("Top Book Categories")
            ax.set_xlabel("Category")
            ax.set_ylabel("Books")
            plt.xticks(rotation=35, ha="right")
            st.pyplot(fig)
            plt.close(fig)

        if "Price Type" in books.columns:

            price_counts = books["Price Type"].value_counts()

            fig, ax = plt.subplots(figsize=(7, 4))
            price_counts.plot(kind="bar", ax=ax)
            ax.set_title("Actual vs Estimated Prices")
            ax.set_ylabel("Number of Books")
            st.pyplot(fig)
            plt.close(fig)

        if "Publication Year" in books.columns:

            years = pd.to_numeric(
                books["Publication Year"],
                errors="coerce"
            ).dropna()

            if not years.empty:

                fig, ax = plt.subplots(figsize=(9, 4))
                ax.hist(years, bins=15, edgecolor="white")
                ax.set_title("Publication Year Distribution")
                ax.set_xlabel("Year")
                ax.set_ylabel("Books")
                st.pyplot(fig)
                plt.close(fig)

    else:
        st.info("Collect books to view charts.")

    # SENTIMENT ANALYSIS

    st.markdown("---")
    st.markdown("## 💬 Sentiment Analysis")

    if not books.empty and "Description" in books.columns:

        descriptions = books["Description"].fillna("").astype(str)

        scores = descriptions.apply(
            lambda x: TextBlob(x).sentiment.polarity if x.strip() else 0
        )

        labels = scores.apply(
            lambda x: "Positive" if x > 0
            else "Negative" if x < 0
            else "Neutral"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric("Positive", int((labels == "Positive").sum()))
        c2.metric("Neutral", int((labels == "Neutral").sum()))
        c3.metric("Negative", int((labels == "Negative").sum()))

        fig, ax = plt.subplots(figsize=(8, 4))
        labels.value_counts().plot(kind="bar", ax=ax)
        ax.set_title("Book Description Sentiment")
        ax.set_ylabel("Books")
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
        st.info("Description data is required for sentiment analysis.")

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

        st.warning("Go to Home and collect books first.")

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
            if "Price Type" in books.columns else 0
        )

        estimated_count = (
            int((books["Price Type"] == "Estimated").sum())
            if "Price Type" in books.columns else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Total Books", len(books))
        c2.metric("Books With Ratings", len(ratings))
        c3.metric(
            "Average Rating",
            f"{ratings.mean():.2f}" if not ratings.empty else "N/A"
        )
        c4.metric("Books With Price", len(prices))

        st.markdown("---")
        st.markdown("## 💰 Price Overview")

        p1, p2 = st.columns(2)

        p1.metric("Actual Price Books", actual_count)
        p2.metric("Estimated Price Books", estimated_count)

        if "Price Type" in books.columns:

            fig, ax = plt.subplots(figsize=(8, 4))
            books["Price Type"].value_counts().plot(kind="bar", ax=ax)
            ax.set_title("Actual vs Estimated Prices")
            ax.set_ylabel("Books")
            st.pyplot(fig)
            plt.close(fig)

        st.markdown("---")
        st.markdown("## 📈 Book Analytics")

        if not ratings.empty:

            fig, ax = plt.subplots(figsize=(9, 4))
            ax.hist(ratings, bins=10, edgecolor="white")
            ax.set_title("Rating Distribution")
            ax.set_xlabel("Rating")
            ax.set_ylabel("Books")
            st.pyplot(fig)
            plt.close(fig)

        if "Category" in books.columns:

            category_data = books["Category"].fillna(
                "Unknown"
            ).value_counts().head(10)

            fig, ax = plt.subplots(figsize=(9, 5))
            category_data.plot(kind="bar", ax=ax)
            ax.set_title("Top Book Categories")
            ax.set_ylabel("Books")
            plt.xticks(rotation=35, ha="right")
            st.pyplot(fig)
            plt.close(fig)

        st.markdown("---")
        st.markdown("## 📚 Complete Dataset")

        st.dataframe(
            books,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Dashboard Data",
            books.to_csv(index=False).encode("utf-8"),
            "booklens_dashboard.csv",
            "text/csv"
        )
