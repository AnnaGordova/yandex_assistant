create table if not exists "CartItem"
(
    "CART_ITEM_ID" serial primary key,
    "USER_ID" integer not null,
    "PRODUCT_ID" integer not null,
    "QUANTITY" integer not null,
    foreign key ("USER_ID") references "User"("USER_ID"),
    foreign key ("PRODUCT_ID") references "Product"("PRODUCT_ID"),
    unique ("USER_ID", "PRODUCT_ID")
);