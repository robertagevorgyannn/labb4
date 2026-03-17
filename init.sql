"""
    
Этот SQL-скрипт автоматически выполняется контейнером postgres при первом его запуске. 
Он создает структуру таблицы и наполняет её тестовыми данными, чтобы наша программа сразу могла с ней работать

"""
--создание таблицы телефонной книги
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--добавление тестовых данных
INSERT INTO contacts (last_name, first_name, middle_name, phone_number, note) VALUES
('Иванов', 'Иван', 'Иванович', '+7 (999) 123-45-67', 'Друг');

--создание индексов для быстрого поиска
CREATE INDEX idx_phone_number ON contacts(phone_number);
CREATE INDEX idx_last_name ON contacts(last_name);

--функция для автоматического обновления времени
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

--триггер для обновления времени при изменении
CREATE TRIGGER update_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
