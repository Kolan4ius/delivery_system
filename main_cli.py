import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging

from database import Database
from data_export import DataExporter
from logger_config import setup_logging

class DeliveryCLI:
    def __init__(self, db_path='data/delivery.db', db_type='sqlite'):
        self.db = Database(db_path, db_type)
        self.exporter = DataExporter()
        self.logger = logging.getLogger(__name__)
    
    def run(self, args):
        if args.command == 'report':
            self.show_report(args.period)
        elif args.command == 'export':
            self.export_orders(args.file)
        elif args.command == 'import':
            self.import_orders(args.file)
        elif args.command == 'list':
            self.list_orders(args.status, args.date_from, args.date_to)
        else:
            print(f"Неизвестная команда: {args.command}")
            sys.exit(1)
    
    def show_report(self, period='day'):
        print("\n" + "="*50)
        print("ОТЧЁТ ПО ЗАКАЗАМ")
        print("="*50)
        
        stats = self.db.get_order_stats()
        print("\nСтатистика по статусам:")
        for status, count in stats.items():
            print(f"  {status}: {count}")
        
        top = self.db.get_top_customers(3)
        print("\nТоп-3 клиента по сумме заказов:")
        for i, customer in enumerate(top, 1):
            print(f"  {i}. {customer['name']} - {customer['total_spent']:.2f} руб. ({customer['order_count']} заказов)")
        
        revenue = self.db.get_revenue(period)
        period_names = {'day': 'день', 'week': 'неделю', 'month': 'месяц'}
        print(f"\nОбщая выручка за {period_names.get(period, period)}: {revenue:.2f} руб.")
        print("="*50 + "\n")
    
    def export_orders(self, filepath):
        orders = self.db.get_orders()
        if not orders:
            print("Нет заказов для экспорта")
            return
        
        if filepath.endswith('.json'):
            success = self.exporter.export_to_json(orders, filepath)
        elif filepath.endswith('.xml'):
            success = self.exporter.export_to_xml(orders, filepath)
        else:
            print("Используйте .json или .xml")
            return
        
        if success:
            print(f"Экспортировано {len(orders)} заказов в {filepath}")
        else:
            print("Ошибка экспорта")
    
    def import_orders(self, filepath):
        try:
            if filepath.endswith('.json'):
                orders = self.exporter.import_from_json(filepath)
            elif filepath.endswith('.xml'):
                orders = self.exporter.import_from_xml(filepath)
            else:
                print("Используйте .json или .xml")
                return
            
            imported = 0
            for order_data in orders:
                try:
                    customer = self.db.get_customer(order_data['customer_id'])
                    if not customer:
                        print(f"Клиент {order_data['customer_id']} не найден, пропускаем")
                        continue
                    
                    self.db.create_order(
                        order_data['customer_id'],
                        order_data['order_date'],
                        order_data['status'],
                        order_data['items']
                    )
                    imported += 1
                except Exception as e:
                    print(f"Ошибка импорта заказа: {e}")
            
            print(f"Импортировано {imported} заказов из {filepath}")
        except Exception as e:
            print(f"Ошибка импорта: {e}")
    
    def list_orders(self, status=None, date_from=None, date_to=None):
        orders = self.db.get_orders(status, date_from, date_to)
        
        if not orders:
            print("Заказов нет")
            return
        
        print(f"\nНайдено заказов: {len(orders)}")
        print("-" * 80)
        print(f"{'ID':<5} {'Дата':<12} {'Клиент':<20} {'Статус':<15} {'Сумма':<10}")
        print("-" * 80)
        
        for order in orders:
            print(f"{order['id']:<5} {order['order_date']:<12} {order['customer_name'][:20]:<20} "
                  f"{order['status']:<15} {order['total']:<10.2f}")
        print("-" * 80 + "\n")

def main():
    setup_logging('logs/delivery.log')
    
    parser = argparse.ArgumentParser(description='Доставка - система управления')
    parser.add_argument('--db', default='data/delivery.db', help='Путь к БД')
    parser.add_argument('--db-type', choices=['sqlite', 'tinydb'], default='sqlite')
    
    subparsers = parser.add_subparsers(dest='command')
    
    report_parser = subparsers.add_parser('report', help='Отчёт')
    report_parser.add_argument('--period', choices=['day', 'week', 'month'], default='day')
    
    export_parser = subparsers.add_parser('export', help='Экспорт')
    export_parser.add_argument('--file', required=True)
    
    import_parser = subparsers.add_parser('import', help='Импорт')
    import_parser.add_argument('--file', required=True)
    
    list_parser = subparsers.add_parser('list', help='Список заказов')
    list_parser.add_argument('--status', choices=['новый', 'в доставке', 'выполнен', 'отменён'])
    list_parser.add_argument('--date-from', help='Дата с (ГГГГ-ММ-ДД)')
    list_parser.add_argument('--date-to', help='Дата по (ГГГГ-ММ-ДД)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = DeliveryCLI(args.db, args.db_type)
    try:
        cli.run(args)
    finally:
        cli.db.close()

if __name__ == '__main__':
    main()