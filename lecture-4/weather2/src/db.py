import sqlite3
from datetime import datetime

class WeatherDB:
    def __init__(self, db_name="weather_app.db"):
        self.db_name = db_name
        self.init_db()

    def _connect(self):
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """テーブル作成と初期設定"""
        with self._connect() as conn:
            cur = conn.cursor()
            # エリア情報を保存するテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS areas (
                    code TEXT PRIMARY KEY,
                    name TEXT
                )
            """)
            # 天気予報を保存するテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS forecasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area_code TEXT,
                    date TEXT,
                    weather TEXT,
                    wind TEXT,
                    created_at DATETIME,
                    UNIQUE(area_code, date),
                    FOREIGN KEY (area_code) REFERENCES areas(code)
                )
            """)
            conn.commit()

    def save_areas(self, area_dict):
        """エリア情報をDBに一括格納 (INSERT OR REPLACE)"""
        with self._connect() as conn:
            cur = conn.cursor()
            data = [(code, name) for code, name in area_dict.items()]
            cur.executemany("INSERT OR REPLACE INTO areas VALUES (?, ?)", data)
            conn.commit()

    def save_forecast(self, area_code, date, weather, wind):
        """予報データをDBに格納。重複時は最新データで上書き"""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO forecasts (area_code, date, weather, wind, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (area_code, date, weather, wind, datetime.now().isoformat()))
            conn.commit()

    def get_forecasts_by_area(self, area_code):
        """特定地域の保存済みデータをすべて取得（日付順）"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM forecasts WHERE area_code = ? ORDER BY date ASC", (area_code,))
            return cur.fetchall()

    def get_forecast_by_date(self, area_code, date_str):
        """特定の日付(YYYY-MM-DD)のデータをDBから検索"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # 日付文字列の前方一致で検索
            cur.execute("""
                SELECT * FROM forecasts 
                WHERE area_code = ? AND date LIKE ? 
                LIMIT 1
            """, (area_code, f"{date_str}%"))
            return cur.fetchone()