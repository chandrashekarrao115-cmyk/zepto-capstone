

-- Query 1: SELECT + WHERE
SELECT
    title,
    price_gbp,
    rating
FROM books
WHERE price_gbp > 40;


-- Query 2: ORDER BY + LIMIT
SELECT
    title,
    price_gbp,
    price_inr
FROM books
ORDER BY price_gbp DESC
LIMIT 10;


-- Query 3: DISTINCT
SELECT DISTINCT
    category_name
FROM categories
ORDER BY category_name;


-- Query 4: BETWEEN
SELECT
    title,
    price_gbp,
    price_inr,
    rating
FROM books
WHERE price_gbp BETWEEN 20 AND 40
ORDER BY price_gbp;


-- Query 5: JOIN
SELECT
    b.book_id,
    b.title,
    b.price_gbp,
    b.price_inr,
    b.rating,
    b.in_stock,
    c.category_name
FROM books AS b
JOIN categories AS c
    ON b.category_id = c.category_id
ORDER BY b.rating DESC, b.price_gbp DESC
LIMIT 10;


-- Query 6: IN + JOIN
SELECT
    b.title,
    b.price_gbp,
    b.rating,
    c.category_name
FROM books AS b
JOIN categories AS c
    ON b.category_id = c.category_id
WHERE c.category_name IN ('Poetry', 'Mystery', 'History')
ORDER BY b.price_gbp DESC;
