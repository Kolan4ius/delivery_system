import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DataExporter:
    
    @staticmethod
    def export_to_json(orders: List[Dict], filepath: str) -> bool:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(orders, f, ensure_ascii=False, indent=2)
            logger.info(f"Экспортировано {len(orders)} заказов в JSON: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False
    
    @staticmethod
    def import_from_json(filepath: str) -> List[Dict]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("Данные должны быть списком заказов")
            
            for order in data:
                required = ['customer_id', 'order_date', 'status', 'items']
                if not all(k in order for k in required):
                    raise ValueError(f"Неверная структура заказа: {order}")
                if order['status'] not in ['новый', 'в доставке', 'выполнен', 'отменён']:
                    raise ValueError(f"Неверный статус: {order['status']}")
            
            logger.info(f"Импортировано {len(data)} заказов из JSON: {filepath}")
            return data
        except Exception as e:
            logger.error(f"Ошибка импорта из JSON: {e}")
            raise
    
    @staticmethod
    def export_to_xml(orders: List[Dict], filepath: str) -> bool:
        try:
            root = ET.Element("orders")
            
            for order in orders:
                order_elem = ET.SubElement(root, "order")
                
                ET.SubElement(order_elem, "id").text = str(order.get('id', ''))
                ET.SubElement(order_elem, "customer_id").text = str(order.get('customer_id', ''))
                ET.SubElement(order_elem, "customer_name").text = order.get('customer_name', '')
                ET.SubElement(order_elem, "order_date").text = order.get('order_date', '')
                ET.SubElement(order_elem, "status").text = order.get('status', '')
                ET.SubElement(order_elem, "total").text = str(order.get('total', 0))
                
                items_elem = ET.SubElement(order_elem, "items")
                for item in order.get('items', []):
                    item_elem = ET.SubElement(items_elem, "item")
                    ET.SubElement(item_elem, "product_name").text = item.get('product_name', '')
                    ET.SubElement(item_elem, "quantity").text = str(item.get('quantity', 0))
                    ET.SubElement(item_elem, "price").text = str(item.get('price', 0))
            
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            logger.info(f"Экспортировано {len(orders)} заказов в XML: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта в XML: {e}")
            return False
    
    @staticmethod
    def import_from_xml(filepath: str) -> List[Dict]:
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            orders = []
            for order_elem in root.findall('order'):
                order = {
                    'id': int(order_elem.find('id').text) if order_elem.find('id') is not None and order_elem.find('id').text else None,
                    'customer_id': int(order_elem.find('customer_id').text) if order_elem.find('customer_id') is not None else 0,
                    'customer_name': order_elem.find('customer_name').text if order_elem.find('customer_name') is not None else '',
                    'order_date': order_elem.find('order_date').text if order_elem.find('order_date') is not None else '',
                    'status': order_elem.find('status').text if order_elem.find('status') is not None else 'новый',
                    'total': float(order_elem.find('total').text) if order_elem.find('total') is not None else 0,
                    'items': []
                }
                
                items_elem = order_elem.find('items')
                if items_elem is not None:
                    for item_elem in items_elem.findall('item'):
                        item = {
                            'product_name': item_elem.find('product_name').text if item_elem.find('product_name') is not None else '',
                            'quantity': int(item_elem.find('quantity').text) if item_elem.find('quantity') is not None else 0,
                            'price': float(item_elem.find('price').text) if item_elem.find('price') is not None else 0
                        }
                        order['items'].append(item)
                
                orders.append(order)
            
            logger.info(f"Импортировано {len(orders)} заказов из XML: {filepath}")
            return orders
        except Exception as e:
            logger.error(f"Ошибка импорта из XML: {e}")
            raise