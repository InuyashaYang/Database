-- 清空数据库 (谨慎操作!)
DROP DATABASE IF EXISTS stock_market_db;
CREATE DATABASE stock_market_db;
USE stock_market_db;

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
    PRIMARY KEY (user_id, stock_code)
);

-- 添加 user_holdings 表的外键约束
ALTER TABLE user_holdings
ADD CONSTRAINT fk_user_holdings_user_id
FOREIGN KEY (user_id) REFERENCES users(user_id);

ALTER TABLE user_holdings
ADD CONSTRAINT fk_user_holdings_stock_code
FOREIGN KEY (stock_code) REFERENCES stocks(stock_code);

-- 创建 stock_prices 表
CREATE TABLE stock_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(255) NOT NULL,
    timestamp INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- 添加 stock_prices 表的外键约束
ALTER TABLE stock_prices
ADD CONSTRAINT fk_stock_prices_stock_code
FOREIGN KEY (stock_code) REFERENCES stocks(stock_code);

-- 创建 asset_history 表
CREATE TABLE asset_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    timestamp INT NOT NULL,
    asset_value DECIMAL(15, 2) NOT NULL
);

-- 添加 asset_history 表的外键约束
ALTER TABLE asset_history
ADD CONSTRAINT fk_asset_history_user_id
FOREIGN KEY (user_id) REFERENCES users(user_id);
