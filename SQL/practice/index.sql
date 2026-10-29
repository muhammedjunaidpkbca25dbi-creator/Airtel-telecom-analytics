CREATE INDEX IF NOT EXISTS ix_orders_customer
       ON shop_orders (customer_id);