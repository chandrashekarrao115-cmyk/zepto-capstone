
import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
GBP_TO_INR = 105.50
DATABASE = "zepto_books.db"


def scrape_books():
    all_books = []

    for page in range(1, 6):
        url = BASE_URL.format(page)

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        books = soup.select("article.product_pod")

        for book in books:
            title = book.h3.a["title"]

            price = book.select_one(
                ".price_color"
            ).get_text(strip=True)

            availability = book.select_one(
                ".availability"
            ).get_text(" ", strip=True)

            rating = book.select_one(
                "p.star-rating"
            )["class"][1]

            book_href = book.h3.a["href"]

            detail_url = (
                "https://books.toscrape.com/catalogue/"
                + book_href.replace("../", "")
            )

            detail_response = requests.get(
                detail_url,
                timeout=30
            )

            detail_soup = BeautifulSoup(
                detail_response.text,
                "html.parser"
            )

            breadcrumb = detail_soup.select(
                "ul.breadcrumb li"
            )

            if len(breadcrumb) >= 3:
                category = breadcrumb[2].get_text(
                    strip=True
                )
            else:
                category = "Unknown"

            all_books.append({
                "title": title,
                "price": price,
                "star_rating": rating,
                "availability": availability,
                "category": category
            })

        time.sleep(0.5)

    return pd.DataFrame(all_books)


def clean_data(raw_df):
    df = raw_df.copy()

    # Handle the £/Â£ encoding issue encountered
    # during scraping.
    df["price_gbp"] = (
        df["price"]
        .str.replace("Â£", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.strip()
        .astype(float)
    )

    rating_map = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5
    }

    df["rating"] = df["star_rating"].map(rating_map)

    df["in_stock"] = df[
        "availability"
    ].str.contains(
        "In stock",
        case=False,
        na=False
    )

    df["price_inr"] = (
        df["price_gbp"] * GBP_TO_INR
    )

    # Drop rows where essential fields failed
    # to parse.
    df = df.dropna(
        subset=[
            "title",
            "price_gbp",
            "rating",
            "category"
        ]
    ).copy()

    return df[
        [
            "title",
            "price_gbp",
            "price_inr",
            "rating",
            "in_stock",
            "category"
        ]
    ]


if __name__ == "__main__":
    raw_df = scrape_books()
    df = clean_data(raw_df)

    print("Books scraped:", len(raw_df))
    print("Books after cleaning:", len(df))

    df.to_csv(
        "cleaned_books.csv",
        index=False
    )

    print("Cleaned dataset saved.")
