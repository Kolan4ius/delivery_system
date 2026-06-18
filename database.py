import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from tinydb import TinyDB, Query

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str, db_type: str = 'sqlite'):
        self.db_path = db_path
        self.db_type = db_type
        self.conn = None
        
        if db_type == 'sqlite':
            self._init_sqlite()
        elif db_type == 'tinydb':
            self._init_tinydb()
        else:
            raise ValueError(f"Не поддерживаемый тип БД: {db_type}")
    
    def _init_sqlite(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables_sqlite()
        logger.info(f"SQLite БД создана: {self.db_path}")
    
    def _create_tables_sqlite(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
    
    def _init_tinydb(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = TinyDB(self.db_path)
        logger.info(f"TinyDB БД создана: {self.db_path}")
    
    def close(self):
        if self.db_type == 'sqlite' and self.conn:
            self.conn.close()
    
    def create_customer(self, name: str, phone: str, address: str) -> int:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)',
                (name, phone, address)
            )
            self.conn.commit()
            return cursor.lastrowid
        else:
            table = self.conn.table('customers')
            return table.insert({'name': name, 'phone': phone, 'address': address})
    
    def get_customers(self) -> List[Dict]:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM customers ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
        else:
            table = self.conn.table('customers')
            return [{'id': doc.doc_id, **doc} for doc in table.all()]
    
    def get_customer(self, customer_id: int) -> Optional[Dict]:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            table = self.conn.table('customers')
            doc = table.get(doc_id=customer_id)
            return {'id': customer_id, **doc} if doc else None
    
    def update_customer(self, customer_id: int, name: str, phone: str, address: str) -> bool:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE customers SET name=?, phone=?, address=? WHERE id=?',
                (name, phone, address, customer_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        else:
            table = self.conn.table('customers')
            return table.update(
                {'name': name, 'phone': phone, 'address': address},
                doc_ids=[customer_id]
            ) > 0
    
    def delete_customer(self, customer_id: int) -> bool:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM orders WHERE customer_id = ?', (customer_id,))
            if cursor.fetchone()[0] > 0:
                raise ValueError("Нельзя удалить клиента с заказами!")
            
            cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        else:
            orders_table = self.conn.table('orders')
            if orders_table.search(Query().customer_id == customer_id):
                raise ValueError("Нельзя удалить клиента с заказами!")
            
            table = self.conn.table('customers')
            return table.remove(doc_ids=[customer_id]) > 0
    
    def create_order(self, customer_id: int, order_date: str, status: str, items: List[Dict]) -> int:
        total = sum(item['quantity'] * item['price'] for item in items)
        
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO orders (customer_id, order_date, status, total) VALUES (?, ?, ?, ?)',
                (customer_id, order_date, status, total)
            )
            order_id = cursor.lastrowid
            
            for item in items:
                cursor.execute(
                    'INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)',
                    (order_id, item['product_name'], item['quantity'], item['price'])
                )
            
            self.conn.commit()
            return order_id
        else:
            table = self.conn.table('orders')
            return table.insert({
                'customer_id': customer_id,
                'order_date': order_date,
                'status': status,
                'total': total,
                'items': items
            })
    
    def get_orders(self, status: str = None, date_from: str = None, date_to: str = None) -> List[Dict]:
        if self.db_type == 'sqlite':
            query = '''
                SELECT o.*, c.name as customer_name 
                FROM orders o 
                JOIN customers c ON o.customer_id = c.id
                WHERE 1=1
            '''
            params = []
            
            if status:
                query += ' AND o.status = ?'
                params.append(status)
            if date_from:
                query += ' AND o.order_date >= ?'
                params.append(date_from)
            if date_to:
                query += ' AND o.order_date <= ?'
                params.append(date_to)
            
            query += ' ORDER BY o.order_date DESC'
            
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            orders = [dict(row) for row in cursor.fetchall()]
            
            for order in orders:
                cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order['id'],))
                order['items'] = [dict(row) for row in cursor.fetchall()]
            
            return orders
        else:
            table = self.conn.table('orders')
            orders = [{'id': doc.doc_id, **doc} for doc in table.all()]
            
            if status:
                orders = [o for o in orders if o['status'] == status]
            if date_from:
                orders = [o for o in orders if o['order_date'] >= date_from]
            if date_to:
                orders = [o for o in orders if o['order_date'] <= date_to]
            
            customers_table = self.conn.table('customers')
            for order in orders:
                customer = customers_table.get(doc_id=order['customer_id'])
                order['customer_name'] = customer['name'] if customer else 'Неизвестно'
            
            return sorted(orders, key=lambda x: x['order_date'], reverse=True)
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT o.*, c.name as customer_name 
                FROM orders o 
                JOIN customers c ON o.customer_id = c.id 
                WHERE o.id = ?
            ''', (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            order = dict(row)
            cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
            order['items'] = [dict(row) for row in cursor.fetchall()]
            return order
        else:
            table = self.conn.table('orders')
            doc = table.get(doc_id=order_id)
            if not doc:
                return None
            
            order = {'id': order_id, **doc}
            customers_table = self.conn.table('customers')
            customer = customers_table.get(doc_id=order['customer_id'])
            order['customer_name'] = customer['name'] if customer else 'Неизвестно'
            return order
    
    def update_order(self, order_id: int, customer_id: int, order_date: str, 
                     status: str, items: List[Dict]) -> bool:
        total = sum(item['quantity'] * item['price'] for item in items)
        
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE orders SET customer_id=?, order_date=?, status=?, total=? WHERE id=?',
                (customer_id, order_date, status, total, order_id)
            )
            
            cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
            for item in items:
                cursor.execute(
                    'INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)',
                    (order_id, item['product_name'], item['quantity'], item['price'])
                )
            
            self.conn.commit()
            return cursor.rowcount > 0
        else:
            table = self.conn.table('orders')
            return table.update(
                {'customer_id': customer_id, 'order_date': order_date, 
                 'status': status, 'total': total, 'items': items},
                doc_ids=[order_id]
            ) > 0
    
    def delete_order(self, order_id: int) -> bool:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
            cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        else:
            table = self.conn.table('orders')
            return table.remove(doc_ids=[order_id]) > 0
    
    def get_order_stats(self) -> Dict[str, int]:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('SELECT status, COUNT(*) as count FROM orders GROUP BY status')
            stats = {row['status']: row['count'] for row in cursor.fetchall()}
            
            for s in ['новый', 'в доставке', 'выполнен', 'отменён']:
                if s not in stats:
                    stats[s] = 0
            return stats
        else:
            table = self.conn.table('orders')
            orders = table.all()
            stats = {'новый': 0, 'в доставке': 0, 'выполнен': 0, 'отменён': 0}
            for order in orders:
                if order['status'] in stats:
                    stats[order['status']] += 1
            return stats
    
    def get_top_customers(self, limit: int = 3) -> List[Dict]:
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT c.id, c.name, c.phone, c.address, 
                       COALESCE(SUM(o.total), 0) as total_spent,
                       COUNT(o.id) as order_count
                FROM customers c
                LEFT JOIN orders o ON c.id = o.customer_id
                WHERE o.status != 'отменён' OR o.status IS NULL
                GROUP BY c.id
                ORDER BY total_spent DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        else:
            customers = self.conn.table('customers').all()
            orders = self.conn.table('orders').all()
            orders = [o for o in orders if o['status'] != 'отменён']
            
            stats = {}
            for c in customers:
                stats[c.doc_id] = {
                    'id': c.doc_id,
                    'name': c['name'],
                    'phone': c['phone'],
                    'address': c['address'],
                    'total_spent': 0,
                    'order_count': 0
                }
            
            for o in orders:
                if o['customer_id'] in stats:
                    stats[o['customer_id']]['total_spent'] += o['total']
                    stats[o['customer_id']]['order_count'] += 1
            
            return sorted(stats.values(), key=lambda x: x['total_spent'], reverse=True)[:limit]
    
    def get_revenue(self, period: str = 'day') -> float:
        today = datetime.now().strftime('%Y-%m-%d')
        
        from datetime import timedelta
        if period == 'day':
            date_from = today
        elif period == 'week':
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        elif period == 'month':
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            raise ValueError(f"Неизвестный период: {period}")
        
        if self.db_type == 'sqlite':
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as revenue
                FROM orders
                WHERE status != 'отменён' AND order_date >= ?
            ''', (date_from,))
            return cursor.fetchone()[0]
        else:
            table = self.conn.table('orders')
            orders = table.all()
            return sum(o['total'] for o in orders 
                      if o['status'] != 'отменён' and o['order_date'] >= date_from)