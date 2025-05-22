import sqlite3

class Database:
    def __init__(self):
        """Veritabanı bağlantısını kur ve tabloyu oluştur."""
        self.conn = sqlite3.connect("security_scores.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lat REAL,
                lon REAL,
                score INTEGER
            )
        """)
        self.conn.commit()

    def save_score(self, user_id, lat, lon, score):
        """Kullanıcının verdiği güvenlik puanını kaydet."""
        self.cursor.execute("INSERT INTO scores (user_id, lat, lon, score) VALUES (?, ?, ?, ?)",
                            (user_id, lat, lon, score))
        self.conn.commit()

    def get_scores(self):
        """Tüm konumların ortalama puanlarını getir."""
        self.cursor.execute("SELECT lat, lon, AVG(score) FROM scores GROUP BY lat, lon")
        return self.cursor.fetchall()

    def get_user_scores(self, user_id):
        """Belirli bir kullanıcının verdiği puanları getir."""
        self.cursor.execute("SELECT lat, lon, score FROM scores WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()
    

    def get_average_score(self, lat, lon):
        """Belirli bir konumun ortalama puanını döndürür."""
        self.cursor.execute("SELECT AVG(score) FROM scores WHERE lat=? AND lon=?", (lat, lon))
        result = self.cursor.fetchone()
        if result and result[0] is not None:
            return float(result[0])
        return 0


