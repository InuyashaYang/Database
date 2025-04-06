
-- 创建 users 表
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    balance DECIMAL(15, 2) NOT NULL,
    strategy VARCHAR(255)
);

-- 创建 stocks 表
CREATE TABLE stocks (
    stock_code VARCHAR(255) PRIMARY KEY,
    initial_price DECIMAL(10, 2) NOT NULL,
    volatility DECIMAL(5, 4) NOT NULL,
    current_price DECIMAL(10, 2) NOT NULL
);

-- 创建 user_holdings 表
CREATE TABLE user_holdings (
    user_id VARCHAR(255) NOT NULL,
    stock_code VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    PRIMARY KEY (user_id, stock_code),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);

-- 创建 stock_prices 表
CREATE TABLE stock_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(255) NOT NULL,
    timestamp INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);

-- 创建 asset_history 表
CREATE TABLE asset_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    timestamp INT NOT NULL,
    asset_value DECIMAL(15, 2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
