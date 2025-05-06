from models import get_db

def add_test_lead():
    with get_db() as conn:
        conn.execute('''
            INSERT INTO leads (
                name, phone, category, address, website, status,
                employee_count, uses_mobile_devices, industry, city, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Test Business',
            '+17204887700',
            'Test',
            '123 Test St',
            'www.test.com',
            'Not Called',
            10,
            'Unknown',
            'Test',
            'Denver',
            'CO'
        ))
        conn.commit()
        print("Test lead added successfully!")

if __name__ == '__main__':
    add_test_lead() 