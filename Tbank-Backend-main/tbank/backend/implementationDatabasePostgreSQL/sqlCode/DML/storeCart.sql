insert into "CartItem"("USER_ID", "PRODUCT_ID", "QUANTITY")
values ({{user_id}}, {{product_id}}, {{quantity}})
on conflict ("USER_ID", "PRODUCT_ID") 
do update set "QUANTITY" = "CartItem"."QUANTITY" + excluded."QUANTITY";