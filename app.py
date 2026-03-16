#!/usr/bin/env python3
"""
Веб-интерфейс телефонной книги (Flask + PostgreSQL)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import re

app = Flask(__name__)
app.secret_key = 'phonebook-secret-key-2024'

# Настройки подключения к БД
DB_CONFIG = {
    'dbname': 'phonebook',
    'user': 'admin',
    'password': 'admin123',
    'host': 'localhost',  # для запуска вне Docker
    # 'host': 'postgres', # для запуска в Docker
    'port': '5432'
}

def format_phone(phone):
    """Форматирует номер телефона в единый стиль"""
    if not phone:
        return phone
    
    # Удаляем все нецифровые символы
    digits = ''.join(filter(str.isdigit, phone))
    
    # Форматируем в зависимости от длины
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    elif len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    else:
        return phone

def validate_phone(phone):
    """Проверяет, что телефон содержит только допустимые символы"""
    #разрешены: цифры, +, -, пробелы, (, )
    pattern = r'^[0-9\+\-\s\(\)]+$'
    return re.match(pattern, phone) is not None

def validate_name(name):
    """Проверяет, что имя содержит только буквы, пробелы и дефисы"""
    if not name:
        return False
    return all(c.isalpha() or c.isspace() or c == '-' for c in name)

def get_db():
    """Подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return None

@app.route('/')
def index():
    """Главная страница - список контактов"""
    conn = get_db()
    if not conn:
        return "Ошибка подключения к БД", 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, last_name, first_name, middle_name, 
                       phone_number, note 
                FROM contacts 
                ORDER BY id
            """)
            contacts = cur.fetchall()
            
            #форматируем телефоны
            for contact in contacts:
                contact['phone_number'] = format_phone(contact['phone_number'])
                
        return render_template('index.html', contacts=contacts)
    except Exception as e:
        print(f"Ошибка: {e}")
        return f"Ошибка: {e}", 500
    finally:
        conn.close()

@app.route('/add', methods=['GET', 'POST'])
def add():
    """Добавление контакта"""
    if request.method == 'POST':
        #получаем данные из формы
        last_name = request.form['last_name'].strip()
        first_name = request.form['first_name'].strip()
        middle_name = request.form.get('middle_name', '').strip() or None
        phone = request.form['phone'].strip()
        note = request.form.get('note', '').strip() or None
        
        #проверка обязательных полей
        if not last_name or not first_name or not phone:
            flash('Фамилия, имя и телефон обязательны!', 'error')
            return redirect(url_for('add'))
        
        #проверка имени
        if not validate_name(last_name) or not validate_name(first_name):
            flash('Имя и фамилия могут содержать только буквы, пробелы и дефисы', 'error')
            return redirect(url_for('add'))
        
        #проверка телефона
        if not validate_phone(phone):
            flash('Телефон может содержать только цифры, пробелы, скобки, плюс и дефис', 'error')
            return redirect(url_for('add'))
        
        conn = get_db()
        if not conn:
            flash('Ошибка подключения к БД', 'error')
            return redirect(url_for('index'))
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO contacts 
                    (last_name, first_name, middle_name, phone_number, note)
                    VALUES (%s, %s, %s, %s, %s)
                """, (last_name, first_name, middle_name, phone, note))
                conn.commit()
                flash('Контакт успешно добавлен!', 'success')
        except psycopg2.errors.UniqueViolation:
            flash('Такой телефон уже существует!', 'error')
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Редактирование контакта"""
    conn = get_db()
    if not conn:
        flash('Ошибка подключения к БД', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        #обновление данных
        last_name = request.form['last_name'].strip()
        first_name = request.form['first_name'].strip()
        middle_name = request.form.get('middle_name', '').strip() or None
        phone = request.form['phone'].strip()
        note = request.form.get('note', '').strip() or None
        
        if not last_name or not first_name or not phone:
            flash('Фамилия, имя и телефон обязательны!', 'error')
            return redirect(url_for('edit', id=id))
        
        #проверка имени
        if not validate_name(last_name) or not validate_name(first_name):
            flash('Имя и фамилия могут содержать только буквы, пробелы и дефисы', 'error')
            return redirect(url_for('edit', id=id))
        
        #проверка телефона
        if not validate_phone(phone):
            flash('Телефон может содержать только цифры, пробелы, скобки, плюс и дефис', 'error')
            return redirect(url_for('edit', id=id))
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE contacts 
                    SET last_name=%s, first_name=%s, middle_name=%s,
                        phone_number=%s, note=%s
                    WHERE id=%s
                """, (last_name, first_name, middle_name, phone, note, id))
                conn.commit()
                flash('Контакт обновлен!', 'success')
        except psycopg2.errors.UniqueViolation:
            flash('Такой телефон уже существует!', 'error')
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('index'))
    
    #GET запрос - показываем форму с данными
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM contacts WHERE id=%s", (id,))
            contact = cur.fetchone()
            
        if not contact:
            flash('Контакт не найден', 'error')
            return redirect(url_for('index'))
        
        #форматируем телефон для отображения
        contact['phone_number'] = format_phone(contact['phone_number'])
        
        return render_template('edit.html', contact=contact)
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    """Удаление контакта"""
    conn = get_db()
    if not conn:
        flash('Ошибка подключения к БД', 'error')
        return redirect(url_for('index'))
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contacts WHERE id=%s RETURNING id", (id,))
            deleted = cur.fetchone()
            conn.commit()
            
            if deleted:
                flash('Контакт удален!', 'success')
            else:
                flash('Контакт не найден', 'error')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/search')
def search():
    """Поиск контактов"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('index'))
    
    conn = get_db()
    if not conn:
        flash('Ошибка подключения к БД', 'error')
        return redirect(url_for('index'))
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
            """, (f'%{query}%',) * 5)
            results = cur.fetchall()
            
            # Форматируем телефоны
            for contact in results:
                contact['phone_number'] = format_phone(contact['phone_number'])
        
        return render_template('index.html', contacts=results, search_query=query)
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/api/contacts', methods=['GET'])
def api_get_contacts():
    """API для получения списка контактов в формате JSON"""
    conn = get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM contacts ORDER BY id")
            contacts = cur.fetchall()
        return jsonify(contacts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
