#!/usr/bin/env python3
"""
нтерфейс для управления телефонной книгой (PostgreSQL версия)
"""

import psycopg2
from psycopg2 import sql
import sys
from tabulate import tabulate

#настройки подключения к базе данных
DB_CONFIG = {
    'dbname': 'phonebook',
    'user': 'admin',
    'password': 'admin123',
    'host': 'localhost',
    'port': '5432'
}

class PhoneBook:
    """Класс для работы с телефонной книгой"""
    
    def __init__(self):
        """Инициализация и подключение к БД"""
        self.conn = None
        self.connect()
    
    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = True
            print("✓ Подключено к базе данных PostgreSQL")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
            print("\nПроверьте:")
            print("1. Запущен ли PostgreSQL: docker ps | grep postgres")
            print("2. Порт 5432: sudo lsof -i :5432")
            print("3. Параметры подключения в DB_CONFIG")
            sys.exit(1)
    
    def view_contacts(self):
        """Просмотр всех контактов"""
        print("\n--- Список контактов ---")
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, last_name, first_name, middle_name, 
                           phone_number, note 
                    FROM contacts 
                    ORDER BY id
                """)
                contacts = cur.fetchall()
            
            if not contacts:
                print("📭 Телефонная книга пуста")
                return
            
            #подготовка данных для таблицы
            table_data = []
            for contact in contacts:
                id, last, first, middle, phone, note = contact
                fio = f"{last} {first}"
                if middle:
                    fio += f" {middle}"
                
                table_data.append([
                    id,
                    fio,
                    phone,
                    note or '-'
                ])
            
            print(tabulate(table_data, 
                          headers=['ID', 'ФИО', 'Телефон', 'Заметка'],
                          tablefmt='grid'))
            print(f"\nВсего контактов: {len(contacts)}")
            
        except Exception as e:
            print(f"✗ Ошибка при получении списка: {e}")
    
    def add_contact(self):
        """Добавление нового контакта"""
        print("\n--- Добавление нового контакта ---")
        
        # Ввод данных с проверкой
        last_name = input("Фамилия: ").strip()
        while not last_name:
            print("❌ Фамилия обязательна!")
            last_name = input("Фамилия: ").strip()
        
        first_name = input("Имя: ").strip()
        while not first_name:
            print("❌ Имя обязательно!")
            first_name = input("Имя: ").strip()
        
        middle_name = input("Отчество (Enter - пропустить): ").strip()
        if middle_name == "":
            middle_name = None
        
        phone = input("Телефон: ").strip()
        while not phone:
            print("❌ Телефон обязателен!")
            phone = input("Телефон: ").strip()
        
        note = input("Заметка (Enter - пропустить): ").strip()
        if note == "":
            note = None
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO contacts 
                    (last_name, first_name, middle_name, phone_number, note)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (last_name, first_name, middle_name, phone, note))
                
                new_id = cur.fetchone()[0]
                print(f"✓ Контакт успешно добавлен с ID: {new_id}")
                
        except psycopg2.errors.UniqueViolation:
            print("✗ Ошибка: Контакт с таким номером телефона уже существует")
        except Exception as e:
            print(f"✗ Ошибка при добавлении: {e}")
    
    def edit_contact(self):
        """Редактирование контакта"""
        self.view_contacts()
        
        try:
            contact_id = input("\nВведите ID контакта для редактирования: ").strip()
            
            if not contact_id.isdigit():
                print("✗ ID должен быть числом")
                return
            
            # Проверяем существование контакта
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
                contact = cur.fetchone()
                
                if not contact:
                    print("✗ Контакт не найден")
                    return
                
                # Получаем имена колонок
                col_names = [desc[0] for desc in cur.description]
                contact_dict = dict(zip(col_names, contact))
            
            print("\nТекущие данные контакта:")
            print(f"Фамилия: {contact_dict['last_name']}")
            print(f"Имя: {contact_dict['first_name']}")
            print(f"Отчество: {contact_dict['middle_name'] or '-'}")
            print(f"Телефон: {contact_dict['phone_number']}")
            print(f"Заметка: {contact_dict['note'] or '-'}")
            
            print("\nВведите новые данные (Enter - оставить без изменений):")
            
            updates = []
            values = []
            
            new_last = input(f"Фамилия [{contact_dict['last_name']}]: ").strip()
            if new_last:
                updates.append("last_name = %s")
                values.append(new_last)
            
            new_first = input(f"Имя [{contact_dict['first_name']}]: ").strip()
            if new_first:
                updates.append("first_name = %s")
                values.append(new_first)
            
            new_middle = input(f"Отчество [{contact_dict['middle_name'] or ''}]: ").strip()
            if new_middle:
                updates.append("middle_name = %s")
                values.append(new_middle)
            elif new_middle == "" and contact_dict['middle_name'] is not None:
                #хотим удалить отчество
                updates.append("middle_name = %s")
                values.append(None)
            
            new_phone = input(f"Телефон [{contact_dict['phone_number']}]: ").strip()
            if new_phone:
                updates.append("phone_number = %s")
                values.append(new_phone)
            
            new_note = input(f"Заметка [{contact_dict['note'] or ''}]: ").strip()
            if new_note:
                updates.append("note = %s")
                values.append(new_note)
            elif new_note == "" and contact_dict['note'] is not None:
                # Хотим удалить заметку
                updates.append("note = %s")
                values.append(None)
            
            if updates:
                values.append(contact_id)
                query = sql.SQL("UPDATE contacts SET {} WHERE id = %s").format(
                    sql.SQL(', ').join(map(sql.SQL, updates))
                )
                
                with self.conn.cursor() as cur:
                    cur.execute(query, values)
                print("✓ Контакт успешно обновлен")
            else:
                print("Нет изменений")
                    
        except psycopg2.errors.UniqueViolation:
            print("✗ Ошибка: Контакт с таким номером телефона уже существует")
        except Exception as e:
            print(f"✗ Ошибка при редактировании: {e}")
    
    def delete_contact(self):
        """Удаление контакта"""
        self.view_contacts()
        
        try:
            contact_id = input("\nВведите ID контакта для удаления: ").strip()
            
            if not contact_id.isdigit():
                print("✗ ID должен быть числом")
                return
            
            #подтверждение удаления
            confirm = input(f"Вы уверены, что хотите удалить контакт {contact_id}? (да/нет): ").lower()
            if confirm != 'да':
                print("Удаление отменено")
                return
            
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM contacts WHERE id = %s RETURNING id", (contact_id,))
                deleted = cur.fetchone()
                
                if deleted:
                    print(f"✓ Контакт с ID {contact_id} успешно удален")
                else:
                    print("✗ Контакт не найден")
            
        except Exception as e:
            print(f"✗ Ошибка при удалении: {e}")
    
    def search_contacts(self):
        """Поиск контактов"""
        search_term = input("\nВведите текст для поиска: ").strip()
        
        if not search_term:
            print("Поисковый запрос не может быть пустым")
            return
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, last_name, first_name, middle_name, 
                           phone_number, note 
                    FROM contacts 
                    WHERE 
                        last_name ILIKE %s OR
                        first_name ILIKE %s OR
                        middle_name ILIKE %s OR
                        phone_number ILIKE %s OR
                        note ILIKE %s
                    ORDER BY id
                """, (f'%{search_term}%',) * 5)
                
                results = cur.fetchall()
            
            if not results:
                print(f"Ничего не найдено по запросу '{search_term}'")
                return
            
            print(f"\n🔍 Найдено контактов: {len(results)}")
            
            #подготовка данных для таблицы
            table_data = []
            for contact in results:
                id, last, first, middle, phone, note = contact
                fio = f"{last} {first}"
                if middle:
                    fio += f" {middle}"
                
                table_data.append([
                    id,
                    fio,
                    phone,
                    note or '-'
                ])
            
            print(tabulate(table_data, 
                          headers=['ID', 'ФИО', 'Телефон', 'Заметка'],
                          tablefmt='grid'))
                    
        except Exception as e:
            print(f"✗ Ошибка при поиске: {e}")
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            print("Соединение с базой данных закрыто")
    
    def menu(self):
        """Главное меню программы"""
        while True:
            print("\n" + "="*60)
            print("📞 ТЕЛЕФОННАЯ КНИГА (PostgreSQL)")
            print("="*60)
            print("1. 📋 Просмотреть все контакты")
            print("2. ➕ Добавить новый контакт")
            print("3. ✏️ Редактировать контакт")
            print("4. 🗑️ Удалить контакт")
            print("5. 🔍 Поиск контактов")
            print("0. 🚪 Выход из программы")
            print("-"*60)
            
            choice = input("Выберите действие (0-5): ").strip()
            
            if choice == '1':
                self.view_contacts()
            elif choice == '2':
                self.add_contact()
            elif choice == '3':
                self.edit_contact()
            elif choice == '4':
                self.delete_contact()
            elif choice == '5':
                self.search_contacts()
            elif choice == '0':
                print("\nДо свидания! 👋")
                break
            else:
                print("❌ Неверный выбор. Пожалуйста, введите число от 0 до 5.")
                
                #пауза, чтобы пользователь прочитал сообщение
                input("Нажмите Enter, чтобы продолжить...")

def main():
    """Основная функция"""
    print("="*60)
    print("Запуск телефонной книги...")
    print("="*60)
    
    phonebook = PhoneBook()
    
    try:
        phonebook.menu()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\nНепредвиденная ошибка: {e}")
    finally:
        phonebook.close()

if __name__ == "__main__":
    main()
