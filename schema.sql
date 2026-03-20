-- Ecommerce Database Schema
-- This file is used by the chatbot to provide context to the LLM

Tables:
- categories(id, name, description)
- products(id, name, price, stock_quantity, category_id, created_at)
- customers(id, first_name, last_name, email, phone, address, created_at)
- transactions(id, customer_id, product_id, quantity, total_amount, transaction_date)

Foreign keys:
- products.category_id -> categories.id
- transactions.customer_id -> customers.id
- transactions.product_id -> products.id