import sqlite3

class Database:
    def __init__(self):
        """Veritabanı bağlantısını kur ve tabloyu oluştur."""
        # Aynı users.db dosyasını kullan
        self.conn = sqlite3.connect("users.db")
        self.cursor = self.conn.cursor()
        
        # Security scores tablosunu users.db içinde oluştur
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lat REAL,
                lon REAL,
                score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        self.conn.commit()

    def save_score(self, user_id, lat, lon, score):
        """Kullanıcının verdiği güvenlik puanını kaydet."""
        self.cursor.execute("""
            INSERT INTO security_scores (user_id, lat, lon, score) 
            VALUES (?, ?, ?, ?)
        """, (user_id, lat, lon, score))
        self.conn.commit()
        print(f"✅ Puan kaydedildi: User {user_id}, Score {score}")

    def get_scores(self):
        """Tüm konumların ortalama puanlarını getir."""
        self.cursor.execute("""
            SELECT lat, lon, AVG(score) 
            FROM security_scores 
            GROUP BY lat, lon
        """)
        return self.cursor.fetchall()

    def get_user_scores(self, user_id):
        """Belirli bir kullanıcının verdiği puanları getir."""
        self.cursor.execute("""
            SELECT lat, lon, score, created_at 
            FROM security_scores 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_average_score(self, lat, lon):
        """Belirli bir konumun ortalama puanını döndürür."""
        self.cursor.execute("""
            SELECT AVG(score) 
            FROM security_scores 
            WHERE lat=? AND lon=?
        """, (lat, lon))
        result = self.cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0

    def get_location_details(self, lat, lon):
        """Konum detayları: toplam puan sayısı, ortalama vs."""
        self.cursor.execute("""
            SELECT COUNT(*) as total_ratings, AVG(score) as avg_score, 
                   MIN(score) as min_score, MAX(score) as max_score
            FROM security_scores 
            WHERE lat=? AND lon=?
        """, (lat, lon))
        return self.cursor.fetchone()
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        self.conn.close()