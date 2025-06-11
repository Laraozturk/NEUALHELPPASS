import sqlite3
import uuid
from datetime import datetime

class SessionManager:
    def __init__(self):
        self.db_path = "users.db"
        self.init_session_table()
    
    def init_session_table(self):
        """Oturum tablosunu oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Session tablosu ekle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Session tablosu hazır")
    
    def create_session(self, user_id):
        """Yeni oturum oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Eski oturumları kapat
        cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
        
        # Yeni session token oluştur
        session_token = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token)
            VALUES (?, ?)
        ''', (user_id, session_token))
        
        conn.commit()
        conn.close()
        return session_token
    
    def get_active_user(self):
        """Aktif oturumu olan kullanıcıyı getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.id_number, u.password, u.birth_year, u.phone_number
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.is_active = 1
            ORDER BY s.created_at DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'id_number': result[1],
                'password': result[2],
                'birth_year': result[3],
                'phone_number': result[4]
            }
        return None
    
    def is_user_logged_in(self):
        """Aktif oturum var mı?"""
        return self.get_active_user() is not None
    
    def logout_all_sessions(self):
        """Tüm oturumları kapat"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE user_sessions SET is_active = 0')
        
        conn.commit()
        conn.close()
        print(" Tüm oturumlar kapatıldı")
