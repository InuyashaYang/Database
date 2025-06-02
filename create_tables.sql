CREATE DATABASE `stock_market_db`;
USE `stock_market_db`;

-- 用户表
CREATE TABLE `t_user`(
    `user_id`     VARCHAR(100) NOT NULL COMMENT '用户ID',
    `balance`     DECIMAL(15, 2) NOT NULL COMMENT '账户余额',
    `strategy`    VARCHAR(255) NULL DEFAULT NULL COMMENT '交易策略',
    `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`user_id`) USING BTREE
) ENGINE = InnoDB COMMENT = '用户表';

-- 股票表
CREATE TABLE `t_stock`(
    `stock_code`    VARCHAR(50) NOT NULL COMMENT '股票代码',
    `initial_price` DECIMAL(10, 2) NOT NULL COMMENT '初始价格',
    `volatility`    DECIMAL(5, 4) NOT NULL COMMENT '波动率',
    `create_time`   TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`   TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`stock_code`) USING BTREE
) ENGINE = InnoDB COMMENT = '股票表';

-- 用户持仓表
CREATE TABLE `t_user_holding`(
    `id`          INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`     VARCHAR(100) NOT NULL COMMENT '用户ID',
    `stock_code`  VARCHAR(50) NOT NULL COMMENT '股票代码',
    `quantity`    INT(11) NOT NULL COMMENT '持有数量',
    `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`) USING BTREE,
    CONSTRAINT `fk_user_holding_user` FOREIGN KEY (`user_id`)
        REFERENCES `t_user` (`user_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_holding_stock` FOREIGN KEY (`stock_code`)
        REFERENCES `t_stock` (`stock_code`) ON DELETE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 1 COMMENT = '用户持仓表';

-- 股票价格历史表
CREATE TABLE `t_stock_price`(
    `id`          INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stock_code`  VARCHAR(50) NOT NULL COMMENT '股票代码',
    `price`       DECIMAL(10, 2) NOT NULL COMMENT '价格',
    `timestamp`   TIMESTAMP NOT NULL COMMENT '时间戳',
    `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`) USING BTREE,
    CONSTRAINT `fk_stock_price_stock` FOREIGN KEY (`stock_code`)
        REFERENCES `t_stock` (`stock_code`) ON DELETE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 1 COMMENT = '股票价格历史表';

-- 资产历史表
CREATE TABLE `t_asset_history`(
    `id`          INT(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`     VARCHAR(100) NOT NULL COMMENT '用户ID',
    `asset_value` DECIMAL(15, 2) NOT NULL COMMENT '资产价值',
    `timestamp`   TIMESTAMP NOT NULL COMMENT '时间戳',
    `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`) USING BTREE,
    CONSTRAINT `fk_asset_history_user` FOREIGN KEY (`user_id`)
        REFERENCES `t_user` (`user_id`) ON DELETE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 1 COMMENT = '资产历史表';
