
# Data Pipeline

## Overview

This module implements an end-to-end data engineering pipeline using the public Books to Scrape website.

The pipeline performs:

1. Web scraping
2. Data cleaning
3. GBP to INR conversion
4. Relational database creation
5. SQLite data loading
6. SQL querying
7. Pandas analysis
8. SQL JOIN versus pandas merge comparison

## Data Source

The data source is:

https://books.toscrape.com/

The first five catalogue pages were scraped.

The final dataset contains 100 books across 29 categories.

## Scraped Fields

The scraper collects:

- `title`
- `price`
- `star_rating`
- `availability`
- `category`

## Cleaning

### Price

The currency symbol was removed from the scraped price and converted to a floating-point value in the `price_gbp` column.

### Rating

The textual ratings were converted to integers:

- One → 1
- Two → 2
- Three → 3
- Four → 4
- Five → 5

### Availability

Availability text containing "In stock" was converted to a Boolean `in_stock` field.

### Currency Conversion

The project-required fixed conversion rate was used:

**1 GBP = 105.50 INR**

Therefore:

```text
price_inr = price_gbp × 105.50
