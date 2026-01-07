import flet as ft
import requests
from datetime import datetime
import re
from db import WeatherDB # 作成したdb.pyを読み込み

class WeatherApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Weather Archive App"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#F0F2F5"
        self.page.padding = 0
        
        # データベース操作クラスの初期化
        self.db = WeatherDB()
        self.areas = {}
        
        self.setup_ui()
        self.load_areas()

    def setup_ui(self):
        """UIコンポーネントの初期化と配置"""
        
        # 1. ヘッダーセクション（グラデーション）
        header = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.WB_CLOUDY_ROUNDED, color="white", size=40),
                ft.Text("Weather Archive", size=32, weight="bold", color="white"),
                ft.Text("最新予報の取得と日付による履歴検索", size=14, color="white70"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#1A237E", "#3949AB"],
            ),
            padding=40, width=float("inf"),
        )

        # 2. 操作パネル（地域選択と日付入力検索）
        self.area_dropdown = ft.Dropdown(
            label="地域を選択", 
            on_change=self.on_area_changed, 
            expand=3, 
            bgcolor="white",
            border_radius=10
        )
        
        # 日付入力用のテキストフィールド
        self.date_input = ft.TextField(
            label="日付検索 (YYYY-MM-DD)",
            hint_text="例: 2024-05-20",
            expand=2,
            bgcolor="white",
            border_radius=10,
            disabled=True,
            on_submit=self.on_search_click # エンターキーでも検索可能
        )
        
        self.search_btn = ft.IconButton(
            icon=ft.Icons.SEARCH_ROUNDED,
            icon_color="#3949AB",
            on_click=self.on_search_click,
            disabled=True,
            tooltip="検索実行"
        )

        controls_card = ft.Card(
            content=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LOCATION_ON, color="#3949AB"),
                    self.area_dropdown,
                    self.date_input,
                    self.search_btn
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20
            ),
            elevation=4,
            margin=ft.margin.only(top=-30, left=20, right=20)
        )

        # 3. メイン表示エリア
        self.loading = ft.ProgressBar(visible=False, color="#3949AB")
        self.error_text = ft.Text("", color="red-700", size=12, weight="bold")
        self.weather_display = ft.Column(spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        # 全体レイアウトの構築
        self.page.add(
            ft.Column([
                header,
                controls_card,
                ft.Container(
                    content=ft.Column([
                        self.loading,
                        self.error_text,
                        self.weather_display
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20, expand=True
                )
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        )

    def load_areas(self):
        """起動時に地域リストを取得してDBに保存・Dropdownに反映"""
        self.loading.visible = True
        self.page.update()
        try:
            res = requests.get("http://www.jma.go.jp/bosai/common/const/area.json", timeout=10)
            res.raise_for_status()
            offices = res.json().get("offices", {})
            
            self.db.save_areas({code: info["name"] for code, info in offices.items()})
            self.areas = {code: info["name"] for code, info in offices.items()}
            
            self.area_dropdown.options = [
                ft.dropdown.Option(key=k, text=v) for k, v in sorted(self.areas.items(), key=lambda x: x[1])
            ]
            self.area_dropdown.disabled = False
        except Exception as e:
            self.error_text.value = f"地域データの取得に失敗しました: {e}"
        finally:
            self.loading.visible = False
            self.page.update()

    def on_area_changed(self, e):
        """地域が変更されたら入力を有効化し、最新情報を取得"""
        self.date_input.disabled = False
        self.search_btn.disabled = False
        self.sync_weather_data()

    def sync_weather_data(self):
        area_code = self.area_dropdown.value
        self.loading.visible = True
        self.error_text.value = ""
        self.page.update()

        try:
            res = requests.get(f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json", timeout=10)
            res.raise_for_status()
            forecast_json = res.json()[0]
            
            ts = forecast_json["timeSeries"][0]
            times = ts["timeDefines"]
            area_info = ts["areas"][0]
            weathers = area_info.get("weathers", [])
            winds = area_info.get("winds", [])

            for i in range(len(times)):
                self.db.save_forecast(
                    area_code, 
                    times[i], 
                    weathers[i] if i < len(weathers) else "データなし", 
                    winds[i] if i < len(winds) else "データなし"
                )
            
            self.display_latest(area_code)

        except Exception as e:
            self.error_text.value = f"天気情報の更新エラー: {e}"
        finally:
            self.loading.visible = False
            self.page.update()

    def display_latest(self, area_code):
        self.weather_display.controls.clear()
        records = self.db.get_forecasts_by_area(area_code)
        
        self.weather_display.controls.append(
            ft.Text(f"{self.areas[area_code]} の最新予報 (DB同期済み)", size=20, weight="bold", color="#1A237E")
        )
        
        cards_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=15)
        for rec in records:
            cards_row.controls.append(self.build_weather_card(rec))
        
        self.weather_display.controls.append(cards_row)

    def on_search_click(self, e):
        """検索ボタンが押された時の処理（日付検索）"""
        date_str = self.date_input.value.strip()
        area_code = self.area_dropdown.value
        self.error_text.value = ""

        # 日付形式 (YYYY-MM-DD) のバリデーション
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            self.error_text.value = "日付は YYYY-MM-DD 形式で入力してください (例: 2024-05-20)"
            self.page.update()
            return

        record = self.db.get_forecast_by_date(area_code, date_str)
        
        self.weather_display.controls.clear()
        self.weather_display.controls.append(
            ft.Text(f"📅 {date_str} の検索結果", size=22, weight="bold", color="#1A237E")
        )
        
        if record:
            self.weather_display.controls.append(self.build_weather_card(record, large=True))
        else:
            self.weather_display.controls.append(
                ft.Column([
                    ft.Icon(ft.Icons.SEARCH_OFF, size=50, color="grey"),
                    ft.Text(f"{date_str} のデータはDBに保存されていません。\n(先に地域を選択して最新データを取得してください)", color="grey", text_align="center"),
                ], horizontal_alignment="center")
            )
        
        self.weather_display.controls.append(
            ft.TextButton("最新の予報一覧に戻る", icon=ft.Icons.ARROW_BACK, on_click=lambda _: self.display_latest(area_code))
        )
        self.page.update()

    def build_weather_card(self, rec, large=False):
        try:
            dt = datetime.fromisoformat(rec["date"].replace("+09:00", ""))
            date_display = dt.strftime("%m/%d (%a)")
        except:
            date_display = rec["date"][:10]

        weather_text = rec["weather"]
        color = self.get_weather_color(weather_text)
        icon = self.get_weather_icon(weather_text)

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text(date_display, color="white", weight="bold"),
                    bgcolor=color,
                    padding=10, alignment=ft.alignment.center,
                    border_radius=ft.border_radius.only(top_left=12, top_right=12),
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(icon, size=40 if not large else 60),
                        ft.Text(weather_text, size=13, weight="bold", text_align="center", max_lines=2),
                        ft.Divider(color="#F0F0F0"),
                        ft.Text(f"風向き: {rec['wind']}", size=11, color="grey700", text_align="center"),
                    ], horizontal_alignment="center", spacing=10),
                    padding=15
                )
            ], spacing=0),
            width=200 if not large else 300,
            bgcolor="white",
            border_radius=12,
            shadow=ft.BoxShadow(blur_radius=8, color="#0000001A", offset=ft.Offset(0, 4))
        )

    def get_weather_color(self, weather_str):
        if "雨" in weather_str: return "#1976D2"
        if "雪" in weather_str: return "#03A9F4"
        if "晴" in weather_str: return "#FFA000"
        return "#78909C"

    def get_weather_icon(self, weather_str):
        if "雨" in weather_str: return "🌧️"
        if "雪" in weather_str: return "❄️"
        if "晴" in weather_str: return "☀️" if "曇" not in weather_str else "🌤️"
        return "☁️"

def main(page: ft.Page):
    WeatherApp(page)

if __name__ == "__main__":
    ft.app(target=main)