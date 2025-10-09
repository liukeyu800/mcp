#!/usr/bin/env python3
"""初始化测试数据库"""

import sqlite3
import os

def init_test_database():
    """初始化测试数据库"""
    db_path = "memory.db"
    
    # 创建新的数据库连接
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"正在初始化数据库: {db_path}")
    
    # 删除现有表（如果存在）
    tables_to_drop = ['order_items', 'orders', 'products', 'users']
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print("已清空现有表")
    
    # 创建用户表
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建产品表
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(50),
            stock INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建订单表
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # 创建订单项表
    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # 插入示例用户数据
    users_data = [
        ('alice', 'alice@example.com', 25),
        ('bob', 'bob@example.com', 30),
        ('charlie', 'charlie@example.com', 35),
        ('diana', 'diana@example.com', 28),
        ('eve', 'eve@example.com', 32)
    ]
    
    cursor.executemany("""
        INSERT INTO users (username, email, age) VALUES (?, ?, ?)
    """, users_data)
    
    # 插入示例产品数据
    products_data = [
        ('笔记本电脑', 5999.99, '电子产品', 10),
        ('智能手机', 2999.99, '电子产品', 25),
        ('咖啡杯', 29.99, '家居用品', 100),
        ('书籍', 49.99, '图书', 50),
        ('耳机', 199.99, '电子产品', 30)
    ]
    
    cursor.executemany("""
        INSERT INTO products (name, price, category, stock) VALUES (?, ?, ?, ?)
    """, products_data)
    
    # 插入示例订单数据
    orders_data = [
        (1, 5999.99, 'completed'),
        (2, 2999.99, 'pending'),
        (3, 79.98, 'completed'),
        (1, 249.98, 'shipped'),
        (4, 49.99, 'pending')
    ]
    
    cursor.executemany("""
        INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, ?)
    """, orders_data)
    
    # 插入示例订单项数据
    order_items_data = [
        (1, 1, 1, 5999.99),  # 订单1: 笔记本电脑
        (2, 2, 1, 2999.99),  # 订单2: 智能手机
        (3, 3, 2, 29.99),    # 订单3: 咖啡杯 x2
        (3, 4, 1, 49.99),    # 订单3: 书籍
        (4, 5, 1, 199.99),   # 订单4: 耳机
        (4, 4, 1, 49.99),    # 订单4: 书籍
        (5, 4, 1, 49.99)     # 订单5: 书籍
    ]
    
    cursor.executemany("""
        INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)
    """, order_items_data)
    
    # 提交事务
    conn.commit()
    
    # 验证数据
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"创建的表: {[table[0] for table in tables]}")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"用户数量: {user_count}")
    
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    print(f"产品数量: {product_count}")
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    order_count = cursor.fetchone()[0]
    print(f"订单数量: {order_count}")
    
    # 关闭连接
    conn.close()
    
    print(f"数据库初始化完成: {db_path}")
    print("可以开始测试数据库客户端了！")

if __name__ == "__main__":
    init_test_database()