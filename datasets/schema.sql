-- Supabase table for datasets/catalog.csv
-- Run in the Supabase SQL editor, then use Table Editor > catalog > Import data from CSV.

create table if not exists catalog (
  room_type             text    not null,
  slot                  text    not null,
  tier                  text    not null,           -- budget | mid | premium | all
  item_id               bigint  not null,
  name                  text    not null,
  category              text,
  product_type          text,
  description           text,
  price_usd             numeric(10,2) not null check (price_usd > 0),
  price_sar             numeric(10,2) not null check (price_sar > 0),
  width_cm              numeric(7,1)  not null check (width_cm > 0),
  depth_cm              numeric(7,1)  not null check (depth_cm > 0),
  height_cm             numeric(7,1)  not null check (height_cm > 0),
  height_imputed        boolean not null default false,  -- true = category/type median, not measured
  style_tag             text    not null check (style_tag in ('modern', 'cozy', 'minimal', 'classic')),
  style_source          text    not null check (style_source in ('keywords', 'default')),
                                                    -- keywords = matched colour/material words; default = no match
  size_from_description boolean not null default false,
  size_note             text,
  other_colors          boolean not null default false,
  link                  text,
  primary key (room_type, item_id)                  -- the same item can appear in 2 rooms (bookcases)
);

create index if not exists catalog_room_slot_idx on catalog (room_type, slot);

-- The website only reads this table, so allow public read and no writes.
alter table catalog enable row level security;
create policy "catalog is publicly readable" on catalog for select using (true);
