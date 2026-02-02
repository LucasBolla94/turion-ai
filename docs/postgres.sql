-- PostgreSQL schema (run as the turion DB user)

create table if not exists memory_items (
  id uuid primary key,
  user_id text not null,
  role text not null,
  text text not null,
  tags text[] default '{}',
  created_at timestamptz default now()
);

create index if not exists memory_items_user_id_created_at
  on memory_items (user_id, created_at desc);

create table if not exists user_profiles (
  user_id text primary key,
  persona text,
  preferences text,
  style text,
  language text,
  updated_at timestamptz default now()
);
