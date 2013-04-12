/*drop table if exists users;
create table users (
id integer primary key autoincrement,
name string not null,
password string not null,
level integer not null,
exp integer not null
);*/

drop table if exists skills;
create table skills (
id integer primary key autoincrement,
user_id integer not null,
name string not null
);

drop table if exists activities;
create table activities (
id integer primary key autoincrement,
skill_id integer not null,
name string not null,
sessions string not null,
difficulty integer not null
);

drop table if exists logs;
create table logs (
id integer primary key autoincrement,
activity_id integer not null,
date string not null,
time integer not null,
exp integer not null
);