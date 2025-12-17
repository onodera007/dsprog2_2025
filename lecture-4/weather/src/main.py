import flet as ft
import requests
import json
from typing import Dict, List


class WeatherApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "天気予報"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        self.areas: Dict[str, str] = {}  # area_code: area_name
        self.weather_data: Dict = {}
        self.selected_area_code: str = None
        
        self.setup_ui()
        self.load_areas()
    
    def setup_ui(self):
        """UIコンポーネントを設定"""
        # ヘッダーセクション
        header = ft.Container(
            ft.Column(
                [
                    ft.Text("天気予報", size=48, weight="bold", color="white"),
                    ft.Text("気象庁の天気情報を表示", size=16, color="rgba(255,255,255,0.8)"),
                ],
                spacing=8,
            ),
            padding=ft.padding.symmetric(vertical=24, horizontal=20),
            bgcolor="#0d47a1",
            border_radius=0,
        )
        
        # エラーメッセージ表示用
        self.error_text = ft.Text("", color="#d32f2f", size=12)
        
        # ロード中表示
        self.loading = ft.ProgressRing(visible=False, color="#1e88e5")
        
        # 地域選択セクション
        self.area_dropdown = ft.Dropdown(
            label="地域を選択してください",
            width=480,
            on_change=self.on_area_changed,
            disabled=True,
            filled=True,
            bgcolor="#f5f5f5",
            border_color="#e0e0e0",
            label_style=ft.TextStyle(color="#666", size=14),
        )
        
        area_section = ft.Container(
            ft.Column(
                [
                    ft.Text("地域選択", size=18, weight="bold", color="#0d47a1"),
                    self.area_dropdown,
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(vertical=20, horizontal=20),
            bgcolor="#fafafa",
            border_radius=12,
            width=520,
        )
        
        # 天気情報表示エリア
        self.weather_display = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
        )
        
        # 天気情報コンテナ
        weather_container = ft.Container(
            self.weather_display,
            padding=20,
            width=500,
        )
        
        # メインコンテンツ
        content = ft.Column(
            [
                header,
                ft.SafeArea(
                    ft.Column(
                        [
                            self.error_text,
                            self.loading,
                            area_section,
                            weather_container,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=20,
                    ),
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        )
        
        self.page.add(content)
    
    def load_areas(self):
        """気象庁APIから地域リストを取得"""
        self.loading.visible = True
        self.page.update()
        
        try:
            response = requests.get("http://www.jma.go.jp/bosai/common/const/area.json")
            response.raise_for_status()
            
            data = response.json()
            
            # 地域（offices）から地域情報を取得
            if "offices" in data:
                offices = data["offices"]
                for area_code, area_info in offices.items():
                    self.areas[area_code] = area_info.get("name", area_code)
            
            # ドロップダウンのオプションを設定
            self.area_dropdown.options = [
                ft.dropdown.Option(
                    key=code,
                    text=name
                )
                for code, name in sorted(self.areas.items(), key=lambda x: x[1])
            ]
            
            self.area_dropdown.disabled = False
            self.error_text.value = ""
            
        except requests.exceptions.RequestException as e:
            self.error_text.value = f"エラー: 地域リストの取得に失敗しました - {str(e)}"
        
        finally:
            self.loading.visible = False
            self.page.update()
    
    def on_area_changed(self, e):
        """地域選択変更時のハンドラ"""
        if self.area_dropdown.value:
            self.selected_area_code = self.area_dropdown.value
            self.load_weather()
    
    def load_weather(self):
        """選択した地域の天気情報を取得"""
        if not self.selected_area_code:
            return
        
        self.loading.visible = True
        self.weather_display.visible = False
        self.page.update()
        
        try:
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{self.selected_area_code}.json"
            response = requests.get(url)
            response.raise_for_status()
            
            self.weather_data = response.json()
            self.display_weather()
            self.error_text.value = ""
            
        except requests.exceptions.RequestException as e:
            self.error_text.value = f"エラー: 天気予報の取得に失敗しました - {str(e)}"
        
        finally:
            self.loading.visible = False
            self.page.update()
    
    def display_weather(self):
        """天気情報をUIに表示"""
        self.weather_display.controls.clear()
        
        if not self.weather_data:
            self.error_text.value = "天気データがありません"
            return
        
        try:
            # レスポンスがリストの場合
            if not isinstance(self.weather_data, list) or len(self.weather_data) == 0:
                self.error_text.value = "天気データの形式が正しくありません"
                return
            
            # 最初の要素を取得
            forecast = self.weather_data[0]
            
            # timeSeries が存在するか確認
            if "timeSeries" not in forecast:
                self.error_text.value = "予報データが見つかりません"
                return
            
            timeseries = forecast.get("timeSeries", [])
            
            if not timeseries:
                self.error_text.value = "予報データがありません"
                return
            
            # タイトル
            area_name = self.areas.get(self.selected_area_code, self.selected_area_code)
            title = ft.Text(
                f"{area_name}",
                size=28,
                weight="bold",
                color="#1e88e5"
            )
            self.weather_display.controls.append(title)
            
            # 複数のtimeSeriesを別々のセクションで表示
            section_count = 0
            
            for ts_index, ts_data in enumerate(timeseries):
                time_defines = ts_data.get("timeDefines", [])
                areas = ts_data.get("areas", [])
                
                if not areas or not time_defines:
                    continue
                
                # 地域データを取得
                area_data = areas[0]
                weathers = area_data.get("weathers", [])
                winds = area_data.get("winds", [])
                
                # 表示対象の日数を決定
                if ts_index == 0:
                    # 最初のセクション：全日分表示
                    display_times = time_defines
                    display_weathers = weathers
                    display_winds = winds
                    section_title_str = "今後の天気予報"
                else:
                    # その後のセクション：最初の日だけ表示（重複を避けるため）
                    if len(time_defines) > 0:
                        display_times = time_defines[:1]
                        display_weathers = weathers[:1]
                        display_winds = winds[:1]
                        section_title_str = "詳細気象情報"
                    else:
                        continue
                
                # セクションタイトル
                section_title = ft.Text(section_title_str, size=20, weight="bold", color="#0d47a1")
                self.weather_display.controls.append(section_title)
                
                # 日ごとのカード
                day_cards = []
                for i in range(len(display_times)):
                    time_str = display_times[i]
                    
                    # 日付をフォーマット
                    try:
                        date_part = time_str[5:10]  # MM-DD
                        day_of_week = ["月", "火", "水", "木", "金", "土", "日"]
                        from datetime import datetime
                        dt = datetime.fromisoformat(time_str.replace("+09:00", ""))
                        day_name = day_of_week[dt.weekday()]
                        time_display = f"{date_part}({day_name})"
                    except:
                        time_display = time_str
                    
                    # 天気情報を取得
                    weather_str = display_weathers[i] if i < len(display_weathers) else "データなし"
                    wind_str = display_winds[i] if i < len(display_winds) else "データなし"
                    
                    # 天気アイコンの背景色を天気によって変更
                    weather_color = self.get_weather_color(weather_str)
                    
                    # 天気アイコンを取得
                    weather_icon = self.get_weather_icon(weather_str)
                    
                    # 個別カード
                    card = ft.Container(
                        ft.Column(
                            [
                                # 日付
                                ft.Container(
                                    ft.Text(time_display, size=15, weight="bold", color="white"),
                                    bgcolor=weather_color,
                                    padding=ft.padding.symmetric(vertical=10, horizontal=8),
                                    border_radius=8,
                                    alignment=ft.alignment.center,
                                    width=140,
                                ),
                                ft.Divider(height=10, color="transparent"),
                                # 天気アイコン
                                ft.Text(weather_icon, size=40),
                                ft.Divider(height=8, color="transparent"),
                                # 天気
                                ft.Column(
                                    [
                                        ft.Text("天気", size=11, color="#666", weight="500"),
                                        ft.Text(weather_str, size=12, weight="bold", text_align=ft.TextAlign.CENTER),
                                    ],
                                    spacing=3,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Divider(height=10, color="transparent"),
                                # 風
                                ft.Column(
                                    [
                                        ft.Text("風", size=11, color="#666", weight="500"),
                                        ft.Text(wind_str, size=12, weight="bold", text_align=ft.TextAlign.CENTER),
                                    ],
                                    spacing=3,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        border=ft.border.all(1.5, "#e8e8e8"),
                        border_radius=14,
                        padding=ft.padding.symmetric(vertical=14, horizontal=12),
                        bgcolor="white",
                        width=160,
                        shadow=ft.BoxShadow(
                            blur_radius=4,
                            color="#00000015",
                            offset=(0, 2),
                        ),
                    )
                    
                    day_cards.append(card)
                
                # 横並びで表示
                cards_row = ft.Row(
                    day_cards,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=10,
                    run_spacing=10,
                )
                
                self.weather_display.controls.append(cards_row)
                self.weather_display.controls.append(ft.Divider(height=15, color="transparent"))
                
                section_count += 1
                if section_count >= 1:  # 最初のセクションのみ表示
                    break
            
            self.weather_display.visible = True
        
        except Exception as e:
            import traceback
            self.error_text.value = f"エラー: {str(e)}"
            traceback.print_exc()
    
    def get_weather_color(self, weather_str: str) -> str:
        """天気に応じて色を返す"""
        if "雨" in weather_str:
            return "#1976d2"  # 青
        elif "雪" in weather_str:
            return "#64b5f6"  # 薄い青
        elif "晴" in weather_str or "晴れ" in weather_str:
            return "#fbc02d"  # 黄
        elif "くもり" in weather_str or "曇り" in weather_str:
            return "#9e9e9e"  # グレー
        else:
            return "#1e88e5"  # デフォルト青
    
    def get_weather_icon(self, weather_str: str) -> str:
        """天気に応じて絵文字を返す"""
        if "雨" in weather_str and "雪" not in weather_str:
            return "🌧️"  # 雨
        elif "雪" in weather_str:
            return "❄️"  # 雪
        elif "晴" in weather_str or "晴れ" in weather_str:
            if "雲" not in weather_str:
                return "☀️"  # 晴れ
            else:
                return "🌤️"  # 晴れ時々曇り
        elif "くもり" in weather_str or "曇り" in weather_str:
            return "☁️"  # 曇り
        elif "ふぶく" in weather_str or "吹雪" in weather_str:
            return "🌪️"  # 吹雪
        elif "霧" in weather_str:
            return "🌫️"  # 霧
        else:
            return "🌐"  # その他


def main(page: ft.Page):
    app = WeatherApp(page)


ft.app(main)

