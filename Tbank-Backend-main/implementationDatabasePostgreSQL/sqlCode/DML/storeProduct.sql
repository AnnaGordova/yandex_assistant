insert into "Product"("PRODUCT_NAME", "PRODUCT_LINK", "PRODUCT_DESCRIPTION", 
"PRODUCT_PRICE", "PRODUCT_PICTURE", "PRODUCT_RATING", "PRODUCT_AMOUNT_OF_REVIEWS", "PRODUCT_SIZE") values
({{product_name}}, {{product_link}}, {{product_description}}, {{product_price}}, {{product_picture}}, {{product_rating}}, {{product_views}}, {{product_size}})
returning "PRODUCT_ID";
