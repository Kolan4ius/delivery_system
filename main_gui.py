import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
import logging

from database import Database
from data_export import DataExporter
from logger_config import setup_logging

class DeliveryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Быстрая доставка - управление заказами")
        self.root.geometry("900x600")
        
        self.db = Database('data/delivery.db', 'sqlite')
        self.exporter = DataExporter()
        self.logger = logging.getLogger(__name__)
        
        self.create_widgets()
        self.refresh_orders()
    
    def create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(pady=5, padx=5, fill=tk.X)
        
        ttk.Label(top_frame, text="Фильтр по статусу:").pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar()
        status_combo = ttk.Combobox(top_frame, textvariable=self.status_var, 
                                    values=['все', 'новый', 'в доставке', 'выполнен', 'отменён'],
                                    width=15)
        status_combo.pack(side=tk.LEFT, padx=5)
        status_combo.set('все')
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_orders())
        
        ttk.Label(top_frame, text="Дата с:").pack(side=tk.LEFT, padx=5)
        self.date_from = ttk.Entry(top_frame, width=12)
        self.date_from.pack(side=tk.LEFT, padx=5)
        self.date_from.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        ttk.Label(top_frame, text="по:").pack(side=tk.LEFT, padx=5)
        self.date_to = ttk.Entry(top_frame, width=12)
        self.date_to.pack(side=tk.LEFT, padx=5)
        self.date_to.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        ttk.Button(top_frame, text="Применить", command=self.refresh_orders).pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="Очистить", command=self.clear_filters).pack(side=tk.LEFT)
        
        action_frame = ttk.Frame(self.root)
        action_frame.pack(pady=5, padx=5, fill=tk.X)
        
        ttk.Button(action_frame, text="Добавить заказ", command=self.add_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Редактировать", command=self.edit_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Удалить", command=self.delete_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Показать отчёт", command=self.show_report).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(action_frame, text="Экспорт:").pack(side=tk.LEFT, padx=(20,5))
        self.export_format = ttk.Combobox(action_frame, values=['JSON', 'XML'], width=8)
        self.export_format.pack(side=tk.LEFT, padx=5)
        self.export_format.set('JSON')
        ttk.Button(action_frame, text="Экспорт", command=self.export_data).pack(side=tk.LEFT, padx=5)
        
        self.tree = ttk.Treeview(self.root, columns=('id', 'date', 'customer', 'status', 'total'), show='headings')
        
        self.tree.heading('id', text='ID')
        self.tree.heading('date', text='Дата')
        self.tree.heading('customer', text='Клиент')
        self.tree.heading('status', text='Статус')
        self.tree.heading('total', text='Сумма')
        
        self.tree.column('id', width=50)
        self.tree.column('date', width=100)
        self.tree.column('customer', width=200)
        self.tree.column('status', width=120)
        self.tree.column('total', width=100)
        
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        self.tree.bind('<Double-Button-1>', lambda e: self.edit_order())
    
    def clear_filters(self):
        self.status_var.set('все')
        self.date_from.delete(0, tk.END)
        self.date_from.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_to.delete(0, tk.END)
        self.date_to.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.refresh_orders()
    
    def refresh_orders(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        status = self.status_var.get()
        if status == 'все':
            status = None
        
        date_from = self.date_from.get() if self.date_from.get() else None
        date_to = self.date_to.get() if self.date_to.get() else None
        
        orders = self.db.get_orders(status, date_from, date_to)
        
        for order in orders:
            self.tree.insert('', tk.END, values=(
                order['id'],
                order['order_date'],
                order['customer_name'],
                order['status'],
                f"{order['total']:.2f}"
            ))
    
    def get_selected_order_id(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ")
            return None
        return self.tree.item(selection[0])['values'][0]
    
    def add_order(self):
        self.open_order_form()
    
    def edit_order(self):
        order_id = self.get_selected_order_id()
        if order_id:
            self.open_order_form(order_id)
    
    def delete_order(self):
        order_id = self.get_selected_order_id()
        if not order_id:
            return
        
        if messagebox.askyesno("Подтверждение", "Удалить заказ?"):
            try:
                self.db.delete_order(order_id)
                self.refresh_orders()
                messagebox.showinfo("Успех", "Заказ удалён")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def open_order_form(self, order_id=None):
        form = Toplevel(self.root)
        form.title("Редактирование заказа" if order_id else "Новый заказ")
        form.geometry("500x500")
        form.grab_set()
        
        order_data = None
        if order_id:
            order_data = self.db.get_order(order_id)
        
        ttk.Label(form, text="Клиент:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        customer_var = tk.StringVar()
        customer_combo = ttk.Combobox(form, textvariable=customer_var, width=40)
        customer_combo.grid(row=0, column=1, padx=5, pady=5)
        
        customers = self.db.get_customers()
        customer_names = [f"{c['id']}: {c['name']}" for c in customers]
        customer_combo['values'] = customer_names
        
        if order_data:
            customer_combo.set(f"{order_data['customer_id']}: {order_data['customer_name']}")
        
        ttk.Label(form, text="Дата заказа:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        date_var = tk.StringVar()
        date_entry = ttk.Entry(form, textvariable=date_var, width=30)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        date_var.set(order_data['order_date'] if order_data else datetime.now().strftime('%Y-%m-%d'))
        
        ttk.Label(form, text="Статус:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(form, textvariable=status_var, 
                                   values=['новый', 'в доставке', 'выполнен', 'отменён'], width=30)
        status_combo.grid(row=2, column=1, padx=5, pady=5)
        status_var.set(order_data['status'] if order_data else 'новый')
        
        ttk.Label(form, text="Товары:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.NW)
        
        items_frame = ttk.Frame(form)
        items_frame.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        items_list = []
        if order_data:
            for item in order_data['items']:
                items_list.append([item['product_name'], item['quantity'], item['price']])
        
        if not items_list:
            items_list.append(['', 1, 0.0])
        
        item_entries = []
        
        def add_item_row():
            row = len(item_entries)
            name_entry = ttk.Entry(items_frame, width=20)
            name_entry.grid(row=row, column=0, padx=2, pady=2)
            
            qty_entry = ttk.Entry(items_frame, width=8)
            qty_entry.grid(row=row, column=1, padx=2, pady=2)
            qty_entry.insert(0, '1')
            
            price_entry = ttk.Entry(items_frame, width=10)
            price_entry.grid(row=row, column=2, padx=2, pady=2)
            price_entry.insert(0, '0.0')
            
            del_btn = ttk.Button(items_frame, text="X", width=3, 
                               command=lambda: remove_item_row(row))
            del_btn.grid(row=row, column=3, padx=2, pady=2)
            
            item_entries.append((name_entry, qty_entry, price_entry, del_btn))
        
        def remove_item_row(row):
            if len(item_entries) <= 1:
                messagebox.showwarning("Внимание", "Должен быть хотя бы один товар")
                return
            for entry in item_entries[row]:
                entry.destroy()
            item_entries.pop(row)
            for i, entries in enumerate(item_entries):
                for j, entry in enumerate(entries):
                    if j < 3:
                        entry.grid(row=i, column=j, padx=2, pady=2)
                    else:
                        entry.grid(row=i, column=j, padx=2, pady=2)
        
        for item in items_list:
            row = len(item_entries)
            name_entry = ttk.Entry(items_frame, width=20)
            name_entry.grid(row=row, column=0, padx=2, pady=2)
            name_entry.insert(0, item[0])
            
            qty_entry = ttk.Entry(items_frame, width=8)
            qty_entry.grid(row=row, column=1, padx=2, pady=2)
            qty_entry.insert(0, str(item[1]))
            
            price_entry = ttk.Entry(items_frame, width=10)
            price_entry.grid(row=row, column=2, padx=2, pady=2)
            price_entry.insert(0, str(item[2]))
            
            del_btn = ttk.Button(items_frame, text="X", width=3,
                               command=lambda r=row: remove_item_row(r))
            del_btn.grid(row=row, column=3, padx=2, pady=2)
            
            item_entries.append((name_entry, qty_entry, price_entry, del_btn))
        
        ttk.Button(items_frame, text="+ Добавить товар", command=add_item_row).grid(
            row=len(item_entries), column=0, columnspan=4, pady=5)
        
        def save_order():
            try:
                customer_text = customer_var.get()
                if not customer_text:
                    messagebox.showwarning("Внимание", "Выберите клиента")
                    return
                customer_id = int(customer_text.split(':')[0])
                
                items = []
                for name_entry, qty_entry, price_entry, _ in item_entries:
                    name = name_entry.get().strip()
                    if not name:
                        continue
                    try:
                        qty = int(qty_entry.get())
                        price = float(price_entry.get())
                        if qty <= 0 or price < 0:
                            raise ValueError
                        items.append({
                            'product_name': name,
                            'quantity': qty,
                            'price': price
                        })
                    except ValueError:
                        messagebox.showerror("Ошибка", "Некорректные данные товара")
                        return
                
                if not items:
                    messagebox.showwarning("Внимание", "Добавьте хотя бы один товар")
                    return
                
                if order_id:
                    self.db.update_order(order_id, customer_id, date_var.get(), 
                                       status_var.get(), items)
                    messagebox.showinfo("Успех", "Заказ обновлён")
                else:
                    self.db.create_order(customer_id, date_var.get(), 
                                       status_var.get(), items)
                    messagebox.showinfo("Успех", "Заказ создан")
                
                form.destroy()
                self.refresh_orders()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
        
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Сохранить", command=save_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=form.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_report(self):
        report_window = Toplevel(self.root)
        report_window.title("Отчёт по заказам")
        report_window.geometry("500x400")
        
        stats = self.db.get_order_stats()
        ttk.Label(report_window, text="Статистика по статусам:", font=('Arial', 12, 'bold')).pack(pady=10)
        
        for status, count in stats.items():
            ttk.Label(report_window, text=f"{status}: {count}").pack()
        
        ttk.Label(report_window, text="\nТоп-3 клиента по сумме заказов:", font=('Arial', 12, 'bold')).pack(pady=10)
        
        top = self.db.get_top_customers(3)
        for i, customer in enumerate(top, 1):
            ttk.Label(report_window, 
                     text=f"{i}. {customer['name']} - {customer['total_spent']:.2f} руб. ({customer['order_count']} заказов)").pack()
        
        ttk.Label(report_window, text="\nВыручка за период:", font=('Arial', 12, 'bold')).pack(pady=10)
        
        periods_frame = ttk.Frame(report_window)
        periods_frame.pack()
        
        def show_period_revenue(period):
            revenue = self.db.get_revenue(period)
            period_names = {'day': 'День', 'week': 'Неделя', 'month': 'Месяц'}
            messagebox.showinfo("Выручка", f"Выручка за {period_names[period]}: {revenue:.2f} руб.")
        
        ttk.Button(periods_frame, text="За день", command=lambda: show_period_revenue('day')).pack(side=tk.LEFT, padx=5)
        ttk.Button(periods_frame, text="За неделю", command=lambda: show_period_revenue('week')).pack(side=tk.LEFT, padx=5)
        ttk.Button(periods_frame, text="За месяц", command=lambda: show_period_revenue('month')).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(report_window, text="Закрыть", command=report_window.destroy).pack(pady=20)
    
    def export_data(self):
        format_type = self.export_format.get().lower()
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} files", f"*.{format_type}")]
        )
        if not filename:
            return
        
        orders = self.db.get_orders()
        if not orders:
            messagebox.showwarning("Внимание", "Нет заказов для экспорта")
            return
        
        if format_type == 'json':
            success = self.exporter.export_to_json(orders, filename)
        else:
            success = self.exporter.export_to_xml(orders, filename)
        
        if success:
            messagebox.showinfo("Успех", f"Экспортировано {len(orders)} заказов")
        else:
            messagebox.showerror("Ошибка", "Ошибка экспорта")
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

def main():
    setup_logging('logs/delivery.log')
    root = tk.Tk()
    app = DeliveryGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()