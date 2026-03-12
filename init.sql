-- 1. Create Categories Table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- 2. Create Products Table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Customers Table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create Transactions Table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    total_amount DECIMAL(10, 2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- 1. Categories 
INSERT INTO categories (name, description) VALUES 
('Electronics', 'Gadgets, computers and hardware'),
('Home & Kitchen', 'Appliances and home decor'),
('Books', 'Physical and digital books'),
('Clothing', 'Apparel and accessories');

-- 2. Products 
INSERT INTO products (name, price, stock_quantity, category_id) VALUES 
('MacBook Air M2', 1199.99, 15, 1),
('iPhone 15 Pro', 999.00, 25, 1),
('AirPods Pro', 249.00, 50, 1),
('Mechanical Keyboard', 89.50, 40, 1),
('Coffee Maker', 45.00, 20, 2),
('Air Fryer XXL', 180.00, 12, 2),
('Clean Code Book', 35.00, 100, 3),
('Postgres for Beginners', 29.90, 80, 3),
('Cotton T-Shirt', 19.99, 200, 4),
('Denim Jacket', 75.00, 30, 4);

-- 3. Customers 
INSERT INTO customers (first_name, last_name, email, phone) VALUES 
('John', 'Doe', 'john.doe@email.com', '+351912345678'),
('Jane', 'Smith', 'jane.smith@email.com', '+351919876543'),
('Alice', 'Johnson', 'alice.j@email.com', NULL),
('Bob', 'Wilson', 'bob.wilson@email.com', '+351961234567'),
('Charlie', 'Brown', 'charlie.b@email.com', '+351930000111');

-- 4. Transactions 
INSERT INTO transactions (customer_id, product_id, quantity, total_amount) VALUES 
(1, 1, 1, 1199.99), 
(1, 4, 1, 89.50),   
(2, 2, 1, 999.00),  
(2, 3, 2, 498.00),  
(3, 7, 1, 35.00),  
(4, 5, 1, 45.00),   
(5, 9, 3, 59.97),   
(1, 8, 1, 29.90);   