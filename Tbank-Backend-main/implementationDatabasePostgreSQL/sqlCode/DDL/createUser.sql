create table if not exists "User"
(
    "USER_ID" serial primary key,
    "USER_EMAIL" varchar(255) not null unique,
    "USER_PASSWORD" varchar(100) not null
);