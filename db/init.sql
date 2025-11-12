CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE units (
  id SERIAL PRIMARY KEY,
  sn TEXT NOT NULL UNIQUE,
  model TEXT
);

CREATE TABLE sims (
  id SERIAL PRIMARY KEY,
  unit_id INT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  slot INT NOT NULL CHECK (slot BETWEEN 1 AND 8),
  imei TEXT,
  vendor TEXT,
  UNIQUE(unit_id, slot)
);

CREATE TABLE leases (
  id SERIAL PRIMARY KEY,
  unit_id INT NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
  customer_id INT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
  start_date DATE NOT NULL,
  due_date DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','returned','overdue')) DEFAULT 'active'
);

CREATE TABLE lease_extensions (
  id SERIAL PRIMARY KEY,
  lease_id INT NOT NULL REFERENCES leases(id) ON DELETE CASCADE,
  extended_due_date DATE NOT NULL,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE unit_notes (
  id SERIAL PRIMARY KEY,
  unit_id INT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  note_text TEXT NOT NULL,
  author TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_units_sn ON units(sn);
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_leases_unit ON leases(unit_id);
CREATE INDEX idx_leases_due ON leases(due_date);
