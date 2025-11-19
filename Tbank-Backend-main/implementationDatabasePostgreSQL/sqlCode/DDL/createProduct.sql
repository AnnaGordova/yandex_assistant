create table if not exists "Product"
(
    "PRODUCT_ID" serial primary key,
    "PRODUCT_NAME" text not null,
    "PRODUCT_LINK" text not null,
    "PRODUCT_DESCRIPTION" text,
    "PRODUCT_PRICE" float not null,
    "PRODUCT_PICTURE" text,
    "PRODUCT_RATING" float,
    "PRODUCT_AMOUNT_OF_REVIEWS" integer,
    "PRODUCT_SIZE" varchar(255)
);