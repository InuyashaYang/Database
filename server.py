import sys
import random
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QComboBox, QCheckBox, QRadioButton, QHBoxLayout,
                             QMessageBox, QLabel, QLineEdit, QDialog, QFormLayout)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.figure as mpl_fig
import mysql.connector
from decimal import Decimal

class User:
    def __init__(self, user_id, initial_balance):
        """初始化用户。"""
        self.user_id = user_id
        self.balance = Decimal(str(initial_balance))  # 初始资金，转换为 Decimal
        self.holdings = {}  # 使用字典存储持仓，key为股票代码，value为持仓数量
        self.strategy = None  # 初始化策略为None
        self.asset_history = [(0, Decimal(str(initial_balance)))] # (timestamp, asset_value)
        self.max_history_length = 10000  # 限制 asset_history 的长度

    def update_asset_history(self, timestamp, stock_prices):
        """更新资产历史记录。"""
        try:
            asset_value = self.balance  # 确保 balance 是 Decimal
            for stock_code, holdings in self.holdings.items():
                asset_value += Decimal(str(holdings)) * Decimal(str(stock_prices.get(stock_code, 0.0)))  # 确保 holdings 和 stock_prices 是 Decimal
            self.asset_history.append((timestamp, asset_value))

            # 限制 asset_history 的长度
            if len(self.asset_history) > self.max_history_length:
                self.asset_history = self.asset_history[-self.max_history_length:]

        except Exception as e:
            print(f"Error updating asset history for user {self.user_id}: {e}")

# 策略接口
class TradingStrategy:
    def execute(self, user, simulator):
        """执行交易策略"""
        raise NotImplementedError("Subclasses must implement execute method")

# 移动平均线交叉策略
class MovingAverageCrossoverStrategy(TradingStrategy):
    def __init__(self, short_window, long_window):
        self.short_window = short_window
        self.long_window = long_window

    def calculate_moving_average(self, prices, window):
        """计算移动平均线。"""
        if len(prices) < window:
            return None
        return sum(prices[-window:]) / window

    def execute(self, user, simulator):
        """根据移动平均交叉策略交易股票。"""
        for stock_code, stock_data in simulator.stocks.items():
            quantity = 5  # 交易数量
            holdings = user.holdings.get(stock_code, 0)
            prices = stock_data['prices']
            price = stock_data['price']

            short_ma = self.calculate_moving_average(prices, self.short_window)
            long_ma = self.calculate_moving_average(prices, self.long_window)

            if short_ma is not None and long_ma is not None:
                if short_ma > long_ma and holdings == 0: # 金叉，且没有持仓
                    simulator.buy_stock(user, stock_code, quantity)
                elif short_ma < long_ma and holdings > 0: # 死叉，且有持仓
                    simulator.sell_stock(user, stock_code, quantity) # 卖出指定数量
                else:
                    pass
            else:
                pass

# 随机交易策略
class RandomTradingStrategy:
    def execute(self, user, simulator):
        """随机交易策略"""
        for stock_code in simulator.stocks.keys():
            action = random.choice(['buy', 'sell', 'hold'])
            quantity = random.randint(1, 5)

            if action == 'buy':
                simulator.buy_stock(user, stock_code, quantity)
            elif action == 'sell':
                simulator.sell_stock(user, stock_code, quantity)
            else:
                pass

# 趋势跟踪策略
class TrendFollowingStrategy:
    def __init__(self, window):
        self.window = window

    def execute(self, user, simulator):
        """趋势跟踪策略：如果当前价格高于过去一段时间的平均价格，则买入；否则卖出。"""
        for stock_code, stock_data in simulator.stocks.items():
            quantity = 5
            holdings = user.holdings.get(stock_code, 0)
            prices = stock_data['prices']
            price = stock_data['price']

            if len(prices) < self.window:
                continue

            average_price = sum(prices[-self.window:]) / self.window

            if price > average_price and holdings == 0:
                simulator.buy_stock(user, stock_code, quantity)
            elif price < average_price and holdings > 0:
                simulator.sell_stock(user, stock_code, quantity)
            else:
                pass

# 反向投资策略
class MeanReversionStrategy:
    def __init__(self, window):
        self.window = window

    def execute(self, user, simulator):
        """均值回归策略：如果当前价格低于过去一段时间的平均价格，则买入；否则卖出。"""
        for stock_code, stock_data in simulator.stocks.items():
            quantity = 5
            holdings = user.holdings.get(stock_code, 0)
            prices = stock_data['prices']
            price = stock_data['price']

            if len(prices) < self.window:
                continue

            average_price = sum(prices[-self.window:]) / self.window

            if price < average_price and holdings == 0:
                simulator.buy_stock(user, stock_code, quantity)
            elif price > average_price and holdings > 0:
                simulator.sell_stock(user, stock_code, quantity)
            else:
                pass

class StockMarketSimulator:
    def __init__(self, stocks, num_trend_followers=5, num_random_traders=5, trade_probability=0.1, initial_balance=10000.0, short_window=5, long_window=20, trend_window=10):
        """
        初始化股票市场模拟器，现在支持股票池。
        """

        # 数据库连接信息
        self.db_host = "localhost"
        self.db_user = "root"
        self.db_password = "Cyborg72"
        self.db_name = "stock_market_db"
        self.mydb = None  # 初始化数据库连接
        self.mycursor = None

        try:
            self.mydb = mysql.connector.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name  # 直接连接到数据库
            )
            self.mydb.autocommit = False  # 关闭自动提交
            self.mycursor = self.mydb.cursor()
            print("成功连接到MySQL数据库！")
        except mysql.connector.Error as err:
            print(f"连接数据库失败: {err}")
            sys.exit(1)  # 退出程序

        # 初始化缓冲区
        self.sql_buffer = []
        self.buffer_size = 100  # 缓冲区大小

        self.stocks = {}
        self.users = []  # 创建模拟用户列表
        self.trade_probability = trade_probability
        self.bankrupt_user = None  # 存储破产用户的ID，初始为None
        self.player = User("Player", initial_balance) # 创建玩家角色
        #self.users.append(self.player) # 将玩家添加到用户列表中 # 玩家信息从数据库加载，这里不添加

        self.short_window = short_window
        self.long_window = long_window
        self.trend_window = trend_window
        self.total_trades = 0 # 记录总交易次数

        # 从数据库加载股票信息
        self.load_stocks_from_db(stocks)

        # 从数据库加载用户信息
        self.load_users_from_db(initial_balance)

        # 创建趋势跟踪交易者
        for i in range(num_trend_followers):
            user_id = f"TrendFollower_{i}"
            if not self.is_user_in_db(user_id) and not any(user.user_id == user_id for user in self.users):
                user = User(user_id, initial_balance)
                user.strategy = TrendFollowingStrategy(window=self.trend_window)
                self.add_user_to_db(user.user_id, initial_balance, "TrendFollowing") # 确保添加到数据库
                self.users.append(user)

        # 创建随机交易者
        for i in range(num_random_traders):
            user_id = f"RandomTrader_{i}"
            if not self.is_user_in_db(user_id) and not any(user.user_id == user_id for user in self.users):
                user = User(user_id, initial_balance)
                user.strategy = RandomTradingStrategy()
                self.add_user_to_db(user.user_id, initial_balance, "Random") # 确保添加到数据库
                self.users.append(user)

        # 玩家使用均值回归策略
        #if not self.is_user_in_db(self.player.user_id) and not any(user.user_id == self.player.user_id for user in self.users):
        #    self.player.strategy = MeanReversionStrategy(window=self.trend_window)
        #    self.add_user_to_db(self.player.user_id, initial_balance, "MeanReversion") # 玩家信息从数据库加载，这里不需要重复添加

    def clear_database(self):
        """清空数据库。"""
        try:
            # 删除所有表
            self.mycursor.execute("DROP TABLE IF EXISTS asset_history")
            self.mycursor.execute("DROP TABLE IF EXISTS stock_prices")
            self.mycursor.execute("DROP TABLE IF EXISTS user_holdings")
            self.mycursor.execute("DROP TABLE IF EXISTS stocks")
            self.mycursor.execute("DROP TABLE IF EXISTS users")
            self.mydb.commit()

            # 创建表
            self.create_tables()

            print("数据库已清空并重新创建表。")
        except mysql.connector.Error as err:
            print(f"清空数据库失败: {err}")
            sys.exit(1)

    def create_tables(self):
        """创建数据库表。"""
        try:
            # 创建 users 表
            self.mycursor.execute("""
                CREATE TABLE users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    balance DECIMAL(15, 2) NOT NULL,
                    strategy VARCHAR(255)
                )
            """)

            # 创建 stocks 表
            self.mycursor.execute("""
                CREATE TABLE stocks (
                    stock_code VARCHAR(255) PRIMARY KEY,
                    initial_price DECIMAL(10, 2) NOT NULL,
                    volatility DECIMAL(5, 4) NOT NULL,
                    current_price DECIMAL(10, 2) NOT NULL
                )
            """)

            # 创建 user_holdings 表
            self.mycursor.execute("""
                CREATE TABLE user_holdings (
                    user_id VARCHAR(255) NOT NULL,
                    stock_code VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL,
                    PRIMARY KEY (user_id, stock_code),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

            # 创建 stock_prices 表
            self.mycursor.execute("""
                CREATE TABLE stock_prices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stock_code VARCHAR(255) NOT NULL,
                    timestamp INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
                )
            """)

            # 创建 asset_history 表
            self.mycursor.execute("""
                CREATE TABLE asset_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    timestamp INT NOT NULL,
                    asset_value DECIMAL(15, 2) NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            self.mydb.commit()
            print("数据库表创建成功。")
        except mysql.connector.Error as err:
            print(f"创建数据库表失败: {err}")
            sys.exit(1)

    def is_user_in_db(self, user_id):
        """检查用户是否已存在于数据库中。"""
        try:
            sql = "SELECT user_id FROM users WHERE user_id = %s"
            val = (user_id,)
            self.mycursor.execute(sql, val)
            result = self.mycursor.fetchone()
            return result is not None
        except mysql.connector.Error as err:
            print(f"检查用户是否存在失败: {err}")
            return False


    def load_stocks_from_db(self, stocks):
        """从数据库加载股票信息。"""
        try:
            self.mycursor.execute("SELECT stock_code, initial_price, volatility, current_price FROM stocks")
            stock_records = self.mycursor.fetchall()
            for stock_code, initial_price, volatility, current_price in stock_records:
                self.stocks[stock_code] = {
                    'price': Decimal(str(current_price)),
                    'volatility': Decimal(str(volatility)),
                    'prices': [Decimal(str(current_price))]
                }

            # 如果数据库为空，则初始化股票信息
            if not self.stocks:
                for stock_code, (initial_price, volatility) in stocks.items():
                    self.add_stock_to_db(stock_code, initial_price, volatility)
                    self.stocks[stock_code] = {
                        'price': Decimal(str(initial_price)),
                        'volatility': Decimal(str(volatility)),
                        'prices': [Decimal(str(initial_price))]
                    }
        except mysql.connector.Error as err:
            print(f"加载股票信息失败: {err}")
    def load_users_from_db(self, initial_balance):
        """从数据库加载用户信息。"""
        try:
            self.mycursor.execute("SELECT user_id, balance, strategy FROM users")
            user_records = self.mycursor.fetchall()
            for user_id, balance, strategy in user_records:
                user = User(user_id, balance)
                user.strategy = self.create_strategy(strategy)  # 创建策略对象
                self.users.append(user)

                # 加载用户持仓信息
                self.load_user_holdings_from_db(user)

                # 找到 Player 用户
                if user_id == "Player":
                    self.player = user

            # 如果数据库为空，则创建默认用户
            if not self.users:
                self.player.strategy = MeanReversionStrategy(window=self.trend_window)
                self.add_user_to_db(self.player.user_id, initial_balance, "MeanReversion")
                self.users.append(self.player) # 确保添加到用户列表

        except mysql.connector.Error as err:
            print(f"加载用户信息失败: {err}")

    def load_user_holdings_from_db(self, user):
        """从数据库加载用户持仓信息。"""
        try:
            self.mycursor.execute("SELECT stock_code, quantity FROM user_holdings WHERE user_id = %s", (user.user_id,))
            holding_records = self.mycursor.fetchall()
            for stock_code, quantity in holding_records:
                user.holdings[stock_code] = quantity
        except mysql.connector.Error as err:
            print(f"加载用户持仓信息失败: {err}")

    def add_stock_to_db(self, stock_code, initial_price, volatility):
        """将股票信息添加到数据库。"""
        try:
            sql = "INSERT INTO stocks (stock_code, initial_price, volatility, current_price) VALUES (%s, %s, %s, %s)"
            val = (stock_code, initial_price, volatility, initial_price)
            self.sql_buffer.append((sql, val))
            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"添加股票信息到数据库失败: {err}")

    def add_user_to_db(self, user_id, initial_balance, strategy):
        """将用户信息添加到数据库。"""
        try:
            sql = "INSERT INTO users (user_id, balance, strategy) VALUES (%s, %s, %s)"
            val = (user_id, initial_balance, strategy)
            self.sql_buffer.append((sql, val))
            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"添加用户信息到数据库失败: {err}")

    def create_strategy(self, strategy_name):
        """根据策略名称创建策略对象。"""
        if strategy_name == "MeanReversion":
            return MeanReversionStrategy(window=self.trend_window)
        elif strategy_name == "TrendFollowing":
            return TrendFollowingStrategy(window=self.trend_window)
        elif strategy_name == "Random":
            return RandomTradingStrategy()
        else:
            return None

    def add_stock(self, stock_code, initial_price, volatility):
        """添加新的股票到股票池。"""
        if stock_code in self.stocks:
            raise ValueError(f"Stock {stock_code} already exists.")

        self.add_stock_to_db(stock_code, initial_price, volatility) # 添加到数据库
        self.stocks[stock_code] = {
            'price': Decimal(str(initial_price)),
            'volatility': Decimal(str(volatility)),
            'prices': [Decimal(str(initial_price))]
        }

    def remove_stock(self, stock_code):
        """从股票池中移除股票。"""
        if stock_code not in self.stocks:
            raise ValueError(f"Stock {stock_code} does not exist.")

        # 获取要移除的股票的当前价格
        stock_price = self.stocks[stock_code]['price']

        # 遍历所有用户，将持有的该股票的价值返还给用户
        for user in self.users:
            if stock_code in user.holdings:
                holdings = user.holdings[stock_code]
                revenue = float(stock_price) * float(holdings)
                user.balance += revenue
                del user.holdings[stock_code]  # 清除持仓
                self.update_user_holdings_in_db(user) # 更新数据库

        del self.stocks[stock_code] # 从股票池中删除股票

        # 从数据库中删除股票
        try:
            sql = "DELETE FROM stocks WHERE stock_code = %s"
            val = (stock_code,)
            self.sql_buffer.append((sql, val))
            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"从数据库删除股票失败: {err}")

    def add_user(self, user_id, initial_balance, strategy_name="MeanReversion"):
        """添加新的用户到模拟器。"""
        user = User(user_id, initial_balance)
        if strategy_name == "MeanReversion":
            user.strategy = MeanReversionStrategy(window=self.trend_window)
        elif strategy_name == "TrendFollowing":
            user.strategy = TrendFollowingStrategy(window=self.trend_window)
        elif strategy_name == "Random":
            user.strategy = RandomTradingStrategy()
        else:
            user.strategy = None  # 默认无策略

        self.add_user_to_db(user_id, initial_balance, strategy_name) # 添加到数据库
        self.users.append(user)
        return user

    def remove_user(self, user_id):
        """从模拟器中移除用户。"""
        user_to_remove = None
        for user in self.users:
            if user.user_id == user_id:
                user_to_remove = user
                break

        if user_to_remove:
            self.users.remove(user_to_remove)

            # 从数据库中删除用户
            try:
                sql = "DELETE FROM users WHERE user_id = %s"
                val = (user_id,)
                self.sql_buffer.append((sql, val))
                self.execute_buffered()
            except mysql.connector.Error as err:
                print(f"从数据库删除用户失败: {err}")

        else:
            raise ValueError(f"User {user_id} does not exist.")

    def update_user_holdings_in_db(self, user):
        """更新用户持仓信息到数据库。"""
        try:
            # 获取用户当前在数据库中的持仓
            sql = "SELECT stock_code, quantity FROM user_holdings WHERE user_id = %s"
            val = (user.user_id,)
            self.mycursor.execute(sql, val)
            existing_holdings = {stock_code: quantity for stock_code, quantity in self.mycursor.fetchall()}

            # 找出需要更新或插入的持仓
            for stock_code, quantity in user.holdings.items():
                if stock_code in existing_holdings:
                    # 如果持仓已经存在，并且数量不同，则更新
                    if quantity != existing_holdings[stock_code]:
                        sql = "UPDATE user_holdings SET quantity = %s WHERE user_id = %s AND stock_code = %s"
                        val = (quantity, user.user_id, stock_code)
                        self.sql_buffer.append((sql, val))
                else:
                    # 如果持仓不存在，则插入
                    sql = "INSERT INTO user_holdings (user_id, stock_code, quantity) VALUES (%s, %s, %s)"
                    val = (user.user_id, stock_code, quantity)
                    self.sql_buffer.append((sql, val))

            # 找出需要删除的持仓
            for stock_code in existing_holdings:
                if stock_code not in user.holdings:
                    sql = "DELETE FROM user_holdings WHERE user_id = %s AND stock_code = %s"
                    val = (user.user_id, stock_code)
                    self.sql_buffer.append((sql, val))

            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"更新用户持仓信息失败: {err}")

    def simulate_trade(self, user):
        """模拟单个用户的交易，现在可以交易股票池中的所有股票。"""
        try:
            if user.strategy:
                user.strategy.execute(user, self)
            else:
                print(f"用户 {user.user_id} 没有策略。")
        except Exception as e:
            print(f"模拟用户 {user.user_id} 的交易时出错: {e}")

    def buy_stock(self, user, stock_code, quantity):
        """模拟买入股票。"""
        try:
            stock_data = self.stocks[stock_code]
            cost = stock_data['price'] * Decimal(str(quantity))
            if user.balance >= cost:
                user.balance -= cost
                # 确保 quantity 是整数
                quantity = int(quantity)
                current_holdings = user.holdings.get(stock_code, 0)
                user.holdings[stock_code] = current_holdings + quantity

                price_change = Decimal(str(random.uniform(0, float(stock_data['volatility'])))) * stock_data['price']
                stock_data['price'] += price_change
                stock_data['prices'].append(stock_data['price'])  # 记录价格

                # 更新数据库
                self.update_stock_price_in_db(stock_code, stock_data['price'])
                self.update_user_holdings_in_db(user)
                self.update_user_balance_in_db(user)

            else:
                print(f"用户 {user.user_id} 余额不足，无法购买 {stock_code}。")
        except Exception as e:
            print(f"购买股票 {stock_code} 时出错: {e}")

    def sell_stock(self, user, stock_code, quantity):
        """模拟卖出股票。"""
        try:
            stock_data = self.stocks[stock_code]
            quantity = int(quantity)
            current_holdings = user.holdings.get(stock_code, 0)

            if current_holdings >= quantity:
                user.holdings[stock_code] -= quantity
                revenue = stock_data['price'] * Decimal(str(quantity))
                user.balance += revenue
                price_change = Decimal(str(random.uniform(0, float(stock_data['volatility'])))) * stock_data['price']
                stock_data['price'] -= price_change
                stock_data['prices'].append(stock_data['price'])  # 记录价格

                # 更新数据库
                self.update_stock_price_in_db(stock_code, stock_data['price'])
                self.update_user_holdings_in_db(user)
                self.update_user_balance_in_db(user)

            else:
                print(f"用户 {user.user_id} 持有 {stock_code} 的数量不足，无法卖出。")
        except Exception as e:
            print(f"卖出股票 {stock_code} 时出错: {e}")

    def update_stock_price_in_db(self, stock_code, price):
        """更新股票价格到数据库。"""
        try:
            sql = "UPDATE stocks SET current_price = %s WHERE stock_code = %s"
            val = (float(price), stock_code)
            self.sql_buffer.append((sql, val))
            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"更新股票价格失败: {err}")

    def update_user_balance_in_db(self, user):
        """更新用户余额到数据库。"""
        try:
            sql = "UPDATE users SET balance = %s WHERE user_id = %s"
            val = (float(user.balance), user.user_id)
            self.sql_buffer.append((sql, val))
            self.execute_buffered()
        except mysql.connector.Error as err:
            print(f"更新用户余额失败: {err}")

    def run_simulation(self, num_trades=100):
        """运行模拟。"""
        asset_history_data = []
        stock_price_data = []

        for i in range(num_trades):
            if self.bankrupt_user is not None:
                print(f"User {self.bankrupt_user.user_id} went bankrupt. Stopping simulation.")
                break

            # 模拟所有用户的交易
            for user in self.users:
                if random.random() < self.trade_probability:
                    self.simulate_trade(user)
                    if user.balance <= 0:
                        self.bankrupt_user = user  # 记录破产用户
                        print(f"User {user.user_id} went bankrupt!")
                        break # 退出内层循环

            # 更新所有用户的资产历史
            try:
                stock_prices = {stock_code: float(data['price']) for stock_code, data in self.stocks.items()}
                for user in self.users:
                    user.update_asset_history(self.total_trades + i + 1, stock_prices)
                    asset_history_data.append((user.user_id, self.total_trades + i + 1, float(user.asset_history[-1][1])))

                # 如果没有交易发生，也要记录价格，保持时间戳的连续性
                for stock_code, stock_data in self.stocks.items():
                    stock_data['prices'].append(stock_data['price'])
                    stock_price_data.append((stock_code, self.total_trades + i + 1, float(stock_data['price'])))

            except Exception as e:
                print(f"Error in run_simulation loop: {e}")

        self.total_trades += num_trades # 更新总交易次数

        # 批量插入资产历史和股票价格
        self.insert_asset_history_to_db(asset_history_data)
        self.insert_stock_price_to_db(stock_price_data)
        self.execute_buffered(force=True)  # 强制提交剩余的SQL语句

    def insert_stock_price_to_db(self, data):
        """批量将股票价格插入数据库。"""
        try:
            sql = "INSERT INTO stock_prices (stock_code, timestamp, price) VALUES (%s, %s, %s)"
            self.mycursor.executemany(sql, data)
            self.mydb.commit()
        except mysql.connector.Error as err:
            print(f"插入股票价格失败: {err}")

    def insert_asset_history_to_db(self, data):
        """批量将用户资产历史插入数据库。"""
        try:
            sql = "INSERT INTO asset_history (user_id, timestamp, asset_value) VALUES (%s, %s, %s)"
            self.mycursor.executemany(sql, data)
            self.mydb.commit()
        except mysql.connector.Error as err:
            print(f"插入资产历史失败: {err}")

    def execute_buffered(self, force=False):
        """执行缓冲区中的SQL语句。"""
        if len(self.sql_buffer) >= self.buffer_size or force:
            try:
                for sql, val in self.sql_buffer:
                    self.mycursor.execute(sql, val)
                self.mydb.commit()
                self.sql_buffer.clear()
            except mysql.connector.Error as err:
                print(f"执行缓冲SQL失败: {err}")

    def plot_price_history(self, ax, stock_codes=None):
        """绘制价格历史到指定的Axes对象。"""
        try:
            ax.clear()  # 清除之前的绘图
            if stock_codes is None:
                stock_codes = self.stocks.keys()

            for stock_code in stock_codes:
                ax.plot([float(p) for p in self.stocks[stock_code]['prices']], label=stock_code)

            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Price")
            ax.set_title("Stock Price Simulation")
            ax.legend()
            ax.figure.canvas.draw()  # 强制重绘
        except Exception as e:
            print(f"Error plotting price history: {e}")

    def plot_asset_history(self, ax, user_ids=None):
        """绘制所有用户的资产历史到指定的Axes对象。"""
        try:
            ax.clear()  # 清除之前的绘图
            if user_ids is None:
                user_ids = [user.user_id for user in self.users]

            max_timestamp = 0

            for user in self.users:
                if user.user_id in user_ids:
                    #  使用总交易次数作为偏移量
                    timestamps = [entry[0] for entry in user.asset_history]
                    asset_values = [entry[1] for entry in user.asset_history]
                    ax.plot(timestamps, asset_values, label=user.user_id)
                    if timestamps:
                        max_timestamp = max(max_timestamp, max(timestamps))

            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Asset Value")
            ax.set_title("Asset History of Users")
            ax.legend()
            ax.set_xlim(0, max_timestamp)  # 设置 x 轴范围
            ax.figure.canvas.draw()  # 强制重绘
        except Exception as e:
            print(f"Error plotting asset history: {e}")

    def close_db_connection(self):
        """关闭数据库连接。"""
        try:
            # 确保所有缓冲的SQL语句都已执行
            self.execute_buffered(force=True)
            if self.mydb and self.mydb.is_connected():
                self.mycursor.close()
                self.mydb.close()
                print("数据库连接已关闭。")
        except mysql.connector.Error as err:
            print(f"关闭数据库连接失败: {err}")


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(200, 200, 300, 150)

        layout = QFormLayout()

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        layout.addRow(self.username_label, self.username_input)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)  # 密码模式
        layout.addRow(self.password_label, self.password_input)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.accept)  # 点击登录时关闭对话框
        layout.addRow(self.login_button)

        self.setLayout(layout)

    def get_credentials(self):
        """返回用户名和密码。"""
        return self.username_input.text(), self.password_input.text()

class MainWindow(QWidget):
    def __init__(self, simulator):
        super().__init__()
        self.simulator = simulator
        self.setWindowTitle("Stock Market Simulator")
        self.setGeometry(100, 100, 1200, 800)

        self.tabs = QTabWidget()
        self.admin_tab = QWidget()
        self.trader_tab = QWidget()

        self.tabs.addTab(self.admin_tab, "Admin")
        self.tabs.addTab(self.trader_tab, "Trader")

        self.init_admin_tab()
        self.init_trader_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # 默认隐藏所有标签页
        self.tabs.setTabEnabled(0, False)  # Admin Tab
        self.tabs.setTabEnabled(1, False)  # Trader Tab

    def init_admin_tab(self):
        """初始化管理员标签页。"""
        layout = QVBoxLayout()

        # 股票价格图表
        self.admin_stock_figure = mpl_fig.Figure(figsize=(5, 4), dpi=100)
        self.admin_stock_canvas = FigureCanvas(self.admin_stock_figure)
        self.admin_stock_ax = self.admin_stock_figure.add_subplot(111)
        layout.addWidget(self.admin_stock_canvas)

        # 用户资产图表
        self.admin_asset_figure = mpl_fig.Figure(figsize=(5, 4), dpi=100)
        self.admin_asset_canvas = FigureCanvas(self.admin_asset_figure)
        self.admin_asset_ax = self.admin_asset_figure.add_subplot(111)
        layout.addWidget(self.admin_asset_canvas)

        # 时间步输入框
        hbox = QHBoxLayout()
        self.admin_time_step_label = QLabel("Time Steps:")
        self.admin_time_step_input = QLineEdit("1")  # 默认值1
        hbox.addWidget(self.admin_time_step_label)
        hbox.addWidget(self.admin_time_step_input)
        layout.addLayout(hbox)

        # 运行按钮
        self.admin_time_step_button = QPushButton("Run Simulation Steps")
        self.admin_time_step_button.clicked.connect(self.run_admin_simulation_steps)
        layout.addWidget(self.admin_time_step_button)

        # 添加股票的输入框和按钮
        stock_hbox = QHBoxLayout()
        self.add_stock_code_label = QLabel("Stock Code:")
        self.add_stock_code_input = QLineEdit()
        self.add_stock_price_label = QLabel("Initial Price:")
        self.add_stock_price_input = QLineEdit()
        self.add_stock_volatility_label = QLabel("Volatility:")
        self.add_stock_volatility_input = QLineEdit()
        self.add_stock_button = QPushButton("Add Stock")
        self.add_stock_button.clicked.connect(self.add_stock)

        stock_hbox.addWidget(self.add_stock_code_label)
        stock_hbox.addWidget(self.add_stock_code_input)
        stock_hbox.addWidget(self.add_stock_price_label)
        stock_hbox.addWidget(self.add_stock_price_input)
        stock_hbox.addWidget(self.add_stock_volatility_label)
        stock_hbox.addWidget(self.add_stock_volatility_input)
        stock_hbox.addWidget(self.add_stock_button)
        layout.addLayout(stock_hbox)

        # 删除股票的输入框和按钮
        remove_stock_hbox = QHBoxLayout()
        self.remove_stock_code_label = QLabel("Stock Code to Remove:")
        self.remove_stock_code_combo = QComboBox()  # 使用 QComboBox
        self.remove_stock_button = QPushButton("Remove Stock")
        self.remove_stock_button.clicked.connect(self.remove_stock)
        remove_stock_hbox.addWidget(self.remove_stock_code_label)
        remove_stock_hbox.addWidget(self.remove_stock_code_combo)
        remove_stock_hbox.addWidget(self.remove_stock_button)
        layout.addLayout(remove_stock_hbox)

        # 添加用户的输入框和按钮
        user_hbox = QHBoxLayout()
        self.add_user_id_label = QLabel("User ID:")
        self.add_user_id_input = QLineEdit()
        self.add_user_balance_label = QLabel("Initial Balance:")
        self.add_user_balance_input = QLineEdit()
        self.add_user_strategy_label = QLabel("Strategy:")
        self.add_user_strategy_combo = QComboBox()  # 添加策略选择
        self.add_user_strategy_combo.addItems(["MeanReversion", "TrendFollowing", "Random"])
        self.add_user_button = QPushButton("Add User")
        self.add_user_button.clicked.connect(self.add_user)

        user_hbox.addWidget(self.add_user_id_label)
        user_hbox.addWidget(self.add_user_id_input)
        user_hbox.addWidget(self.add_user_balance_label)
        user_hbox.addWidget(self.add_user_balance_input)
        user_hbox.addWidget(self.add_user_strategy_label)
        user_hbox.addWidget(self.add_user_strategy_combo)
        user_hbox.addWidget(self.add_user_button)
        layout.addLayout(user_hbox)

        # 删除用户的输入框和按钮
        remove_user_hbox = QHBoxLayout()
        self.remove_user_id_label = QLabel("User ID to Remove:")
        self.remove_user_id_combo = QComboBox()  # 使用 QComboBox
        self.remove_user_button = QPushButton("Remove User")
        self.remove_user_button.clicked.connect(self.remove_user)
        remove_user_hbox.addWidget(self.remove_user_id_label)
        remove_user_hbox.addWidget(self.remove_user_id_combo)
        remove_user_hbox.addWidget(self.remove_user_button)
        layout.addLayout(remove_user_hbox)

        # 股票信息表格
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(4)
        self.stock_table.setHorizontalHeaderLabels(["Code", "Price", "Volatility", "Holders"])
        layout.addWidget(self.stock_table)

        # 用户信息表格
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["ID", "Balance", "Strategy"])
        layout.addWidget(self.user_table)

        # 刷新按钮
        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_button)

        self.admin_tab.setLayout(layout)

    def init_trader_tab(self):
        """初始化交易员标签页。"""
        layout = QVBoxLayout()

        # 股票价格图表
        self.trader_stock_figure = mpl_fig.Figure(figsize=(5, 4), dpi=100)
        self.trader_stock_canvas = FigureCanvas(self.trader_stock_figure)
        self.trader_stock_ax = self.trader_stock_figure.add_subplot(111)
        layout.addWidget(self.trader_stock_canvas)

        # 资产信息
        self.asset_label = QLabel("Asset: N/A")
        layout.addWidget(self.asset_label)

        # 股票选择
        hbox = QHBoxLayout()
        self.stock_label = QLabel("Stock:")
        self.stock_combo = QComboBox()
        hbox.addWidget(self.stock_label)
        hbox.addWidget(self.stock_combo)
        layout.addLayout(hbox)

        # 交易数量
        hbox = QHBoxLayout()
        self.quantity_label = QLabel("Quantity:")
        self.quantity_input = QLineEdit("1")  # 默认值1
        hbox.addWidget(self.quantity_label)
        hbox.addWidget(self.quantity_input)
        layout.addLayout(hbox)

        # 买入和卖出按钮
        hbox = QHBoxLayout()
        self.buy_button = QPushButton("Buy")
        self.buy_button.clicked.connect(self.buy_stock)
        self.sell_button = QPushButton("Sell")
        self.sell_button.clicked.connect(self.sell_stock)
        hbox.addWidget(self.buy_button)
        hbox.addWidget(self.sell_button)
        layout.addLayout(hbox)

        # 交易信息表格
        self.trade_table = QTableWidget()
        self.trade_table.setColumnCount(3)
        self.trade_table.setHorizontalHeaderLabels(["Stock", "Quantity", "Action"])
        layout.addWidget(self.trade_table)

        self.trader_tab.setLayout(layout)

    def run_admin_simulation_steps(self):
        """运行管理员界面的模拟步骤。"""
        try:
            num_steps = self.validate_int_input(self.admin_time_step_input.text(), "Number of time steps")
            if num_steps is not None:
                self.simulator.run_simulation(num_steps)
                self.refresh_data()
                self.update_admin_plots()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error running simulation: {str(e)}")

    def add_stock(self):
        """添加股票到模拟器。"""
        try:
            code = self.add_stock_code_input.text().strip()
            price = self.validate_float_input(self.add_stock_price_input.text(), "Initial price")
            volatility = self.validate_float_input(self.add_stock_volatility_input.text(), "Volatility")

            if not code:
                QMessageBox.warning(self, "Error", "Stock code cannot be empty.")
                return

            if price is None or volatility is None:
                return

            self.simulator.add_stock(code, price, volatility)
            self.refresh_data()
            self.update_admin_plots()
            QMessageBox.information(self, "Success", f"Stock {code} added successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error adding stock: {str(e)}")

    def remove_stock(self):
        """从模拟器中移除股票。"""
        try:
            code = self.remove_stock_code_combo.currentText()
            self.simulator.remove_stock(code)
            self.refresh_data()
            self.update_admin_plots()
            QMessageBox.information(self, "Success", f"Stock {code} removed successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error removing stock: {str(e)}")

    def add_user(self):
        """添加用户到模拟器。"""
        try:
            user_id = self.add_user_id_input.text().strip()
            balance = self.validate_float_input(self.add_user_balance_input.text(), "Initial balance")
            strategy = self.add_user_strategy_combo.currentText()

            if not user_id:
                QMessageBox.warning(self, "Error", "User ID cannot be empty.")
                return

            if balance is None:
                return

            self.simulator.add_user(user_id, balance, strategy)
            self.refresh_data()
            self.update_admin_plots()
            QMessageBox.information(self, "Success", f"User {user_id} added successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error adding user: {str(e)}")

    def remove_user(self):
        """从模拟器中移除用户。"""
        try:
            user_id = self.remove_user_id_combo.currentText()
            self.simulator.remove_user(user_id)
            self.refresh_data()
            self.update_admin_plots()
            QMessageBox.information(self, "Success", f"User {user_id} removed successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error removing user: {str(e)}")

    def buy_stock(self):
        """购买股票。"""
        try:
            stock_code = self.stock_combo.currentText()
            quantity = self.validate_int_input(self.quantity_input.text(), "Quantity")

            if quantity is None:
                return

            self.simulator.buy_stock(self.simulator.player, stock_code, quantity)
            self.refresh_data()
            self.update_trader_plots()
            QMessageBox.information(self, "Success", f"Bought {quantity} shares of {stock_code}.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error buying stock: {str(e)}")

    def sell_stock(self):
        """卖出股票。"""
        try:
            stock_code = self.stock_combo.currentText()
            quantity = self.validate_int_input(self.quantity_input.text(), "Quantity")

            if quantity is None:
                return

            self.simulator.sell_stock(self.simulator.player, stock_code, quantity)
            self.refresh_data()
            self.update_trader_plots()
            QMessageBox.information(self, "Success", f"Sold {quantity} shares of {stock_code}.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error selling stock: {str(e)}")

    def validate_int_input(self, text, field_name):
        """验证整数输入。"""
        try:
            value = int(text)
            return value
        except ValueError:
            QMessageBox.warning(self, "Error", f"Invalid input for {field_name}. Please enter an integer.")
            return None

    def validate_float_input(self, text, field_name):
        """验证浮点数输入。"""
        try:
            value = float(text)
            return value
        except ValueError:
            QMessageBox.warning(self, "Error", f"Invalid input for {field_name}. Please enter a number.")
            return None

    def refresh_data(self):
        """刷新所有表格和下拉菜单的数据。"""
        self.update_stock_table()
        self.update_user_table()
        self.update_stock_combo()
        self.update_user_combo()
        self.update_trader_plots()
        self.update_admin_plots()

    def update_stock_table(self):
        """更新股票信息表格。"""
        self.stock_table.setRowCount(0)
        for code, data in self.simulator.stocks.items():
            row_position = self.stock_table.rowCount()
            self.stock_table.insertRow(row_position)
            self.stock_table.setItem(row_position, 0, QTableWidgetItem(code))
            self.stock_table.setItem(row_position, 1, QTableWidgetItem(str(data['price'])))
            self.stock_table.setItem(row_position, 2, QTableWidgetItem(str(data['volatility'])))
            holders = sum([1 for user in self.simulator.users if code in user.holdings])
            self.stock_table.setItem(row_position, 3, QTableWidgetItem(str(holders)))

    def update_user_table(self):
        """更新用户信息表格。"""
        self.user_table.setRowCount(0)
        for user in self.simulator.users:
            row_position = self.user_table.rowCount()
            self.user_table.insertRow(row_position)
            self.user_table.setItem(row_position, 0, QTableWidgetItem(user.user_id))
            self.user_table.setItem(row_position, 1, QTableWidgetItem(str(user.balance)))
            self.user_table.setItem(row_position, 2, QTableWidgetItem(user.strategy.__class__.__name__ if user.strategy else "None"))

    def update_stock_combo(self):
        """更新股票下拉菜单。"""
        self.stock_combo.clear()
        self.remove_stock_code_combo.clear()
        stock_codes = list(self.simulator.stocks.keys())
        self.stock_combo.addItems(stock_codes)
        self.remove_stock_code_combo.addItems(stock_codes)

    def update_user_combo(self):
        """更新用户下拉菜单。"""
        self.remove_user_id_combo.clear()
        user_ids = [user.user_id for user in self.simulator.users]
        self.remove_user_id_combo.addItems(user_ids)

    def update_trader_plots(self):
        """更新交易员界面的图表。"""
        self.simulator.plot_price_history(self.trader_stock_ax, stock_codes=self.simulator.stocks.keys())
        asset_value = self.simulator.player.balance
        for stock_code, holdings in self.simulator.player.holdings.items():
            asset_value += holdings * self.simulator.stocks[stock_code]['price']
        self.asset_label.setText(f"Asset: {asset_value:.2f}")
        self.trader_stock_canvas.draw()

    def update_admin_plots(self):
        """更新管理员界面的图表。"""
        self.simulator.plot_price_history(self.admin_stock_ax, stock_codes=self.simulator.stocks.keys())
        self.simulator.plot_asset_history(self.admin_asset_ax, user_ids=[user.user_id for user in self.simulator.users])
        self.admin_stock_canvas.draw()
        self.admin_asset_canvas.draw()

    def show_login_dialog(self):
        """显示登录对话框。"""
        dialog = LoginDialog()
        result = dialog.exec_()  # 显示对话框并等待用户操作

        if result == QDialog.Accepted:
            username, password = dialog.get_credentials()
            # 在这里添加你的身份验证逻辑
            if username == "admin" and password == "password":
                QMessageBox.information(self, "Login", "Login successful!")
                self.tabs.setTabEnabled(0, True)  # Admin Tab
                self.tabs.setTabEnabled(1, True)  # Trader Tab
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Login", "Invalid credentials.")

    def closeEvent(self, event):
        """关闭窗口事件处理函数。"""
        self.simulator.close_db_connection()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 初始股票池
    initial_stocks = {
        "AAPL": (150.0, 0.02),  # 苹果公司，初始价格150美元，波动率0.02
        "GOOG": (270.0, 0.015), # 谷歌公司，初始价格270美元，波动率0.015
        "MSFT": (300.0, 0.025)   # 微软公司，初始价格300美元，波动率0.025
    }

    # 创建模拟器
    simulator = StockMarketSimulator(stocks=initial_stocks, num_trend_followers=5, num_random_traders=5)

    # 创建主窗口
    window = MainWindow(simulator)
    window.show()

    # 显示登录对话框
    window.show_login_dialog()

    sys.exit(app.exec_())
