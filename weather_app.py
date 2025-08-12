import os
import sys
import requests
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from meteostat import Daily, Point
from matplotlib.figure import Figure
from datetime import datetime, timedelta
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QMainWindow, QDialog)
from PyQt5.QtCore import Qt


# Load environment variables from .env file
load_dotenv()
# Get OpenWeatherMap API key from environment variables
weather_api = os.getenv('OWM_API_KEY')

# Class for displaying weather charts in a separate window
class PlotWindow(QWidget):
    def __init__(self, city, lat, lon):
        super().__init__()
        self.city = city
        self.lat = lat
        self.lon = lon

        # Window setup
        self.setWindowTitle("Weather chart")
        self.resize(1000, 800)  # Set initial window size

        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(12, 10), dpi=100)  # 12x10 inch figure
        self.canvas = FigureCanvas(self.figure)  # Canvas to embed figure in Qt

        # Set up layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # Plot the data
        self.plot_data(city, lat, lon)

    def plot_data(self, city, lat, lon):
        # Get date range (last 30 days)
        end = datetime.now()
        start = end - timedelta(days=30)

        # Fetch weather data from Meteostat
        data = Daily(Point(lat, lon), start, end).fetch()

        # Create grid layout for subplots
        # - 2 rows, 1 column
        # - Height ratio 3:1 between top and bottom plots
        # - 0.25 spacing between subplots
        gs = self.figure.add_gridspec(
            nrows=2,
            ncols=1,
            height_ratios=[3, 1],
            hspace=0.25
        )

        # Create subplots
        ax_temp = self.figure.add_subplot(gs[0])  # Temperature plot (top)
        ax_wind = self.figure.add_subplot(gs[1], sharex=ax_temp)  # Wind plot (bottom)

        # --- Temperature Plot ---
        ax_temp.plot(data.index, data['tmin'], color='blue',
                    linestyle='--', linewidth=1, label='Minimum t°C')
        ax_temp.plot(data.index, data['tmax'], color='red',
                    linestyle='--', linewidth=1, label='Maximum t°C')
        ax_temp.set_title(f'Temperature in {city.capitalize()}', pad=15)
        ax_temp.set_ylabel('Temperature (°C)')
        ax_temp.legend(loc='upper right')
        ax_temp.grid()
        ax_temp.yaxis.set_major_locator(mdates.DayLocator(interval=2))

        # --- Wind Speed Plot ---
        ax_wind.bar(data.index, data['wspd'], color='green',
                   alpha=0.5, width=0.8)
        ax_wind.set_title(f'Wind speed in {city.capitalize()}')
        ax_wind.set_ylabel('Wind (m/s)')
        ax_wind.grid()

        # X-axis formatting
        ax_wind.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))  # Day.Month format
        ax_wind.xaxis.set_major_locator(mdates.DayLocator(interval=2))  # Show every 2nd day

        # Rotate x-axis labels for both subplots
        for ax in [ax_temp, ax_wind]:
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=7)

        # Adjust subplot spacing
        self.figure.subplots_adjust(
            left=0.1,    # Left margin
            right=0.95,  # Right margin
            top=0.9,     # Top margin
            bottom=0.1   # Bottom margin
        )

        # Redraw canvas to display changes
        self.canvas.draw()

    def closeEvent(self, event):
        """Clean up matplotlib figure when window is closed"""
        plt.close(self.figure)
        event.accept()


# Main application window
class WeatherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window setup
        self.setWindowTitle("Weather")
        self.resize(500, 450)

        # Create central widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # UI Elements
        self.city_label = QLabel("Enter city name: ")
        self.city_input = QLineEdit(self)

        # Buttons
        self.get_weather_button = QPushButton("Current weather")
        self.get_weather_button.clicked.connect(self.get_weather)

        self.get_plot = QPushButton("Weather chart for the month")
        self.get_plot.clicked.connect(self.open_plot_window)

        # Layout setup
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.city_label)
        self.layout.addWidget(self.city_input)
        self.layout.addWidget(self.get_weather_button)
        self.layout.addWidget(self.get_plot)
        self.main_widget.setLayout(self.layout)

        # Widget styling
        self.city_label.setObjectName("city_label")
        self.city_input.setObjectName("city_input")
        self.get_weather_button.setObjectName("get_weather_button")
        self.get_plot.setObjectName("get_plot")

        # Alignment
        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_input.setAlignment(Qt.AlignCenter)

        # CSS styling
        self.setStyleSheet("""
            QLabel, QPushButton {
                font-family: calibri;
            }
            QLabel#city_label {
                font-size: 30px;
                padding: 20px;
            }
            QLineEdit#city_input {
                font-size: 30px;
                padding: 20px;
            }
            QPushButton#get_weather_button {
                font-size: 30px;
                padding: 30px;
            }
            QPushButton#get_plot {
                font-size: 30px;
                padding: 30px;
            }
        """)

    def open_plot_window(self):
        """Open window with weather charts"""
        city = self.city_input.text()
        lat, lon = self.get_coordinates(city)
        if lat is not None and lon is not None:
            self.plot_window = PlotWindow(city, lat, lon)
            self.plot_window.show()

    def get_coordinates(self, city):
        """Get latitude/longitude coordinates for a city using geocoding API"""
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        try:
            response = requests.get(url, timeout=5).json()
            if 'results' in response and len(response['results']) > 0:
                return response['results'][0]['latitude'], response['results'][0]['longitude']
        except Exception:
            return None, None

    def get_weather(self):
        """Get current weather data from OpenWeatherMap API"""
        city = self.city_input.text()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&lang=en&appid={weather_api}&units=metric"
        try:
            response = requests.get(url)
            weather = response.json()
            if weather["cod"] == 200:
                self.display_weather(weather, city)
        except Exception as e:
            print(f"Error fetching weather: {e}")

    def display_weather(self, data, city):
        """Show current weather in a dialog window"""
        dialog = QDialog(self)
        dialog.resize(450, 350)
        dialog.setWindowTitle("Current weather")

        # Create widgets
        info_label = QLabel(f"Current weather in {city.capitalize()}:")
        temperature_label = QLabel(f"{data['main']['temp']:.1f} C ")
        description_label = QLabel(data['weather'][0]['description'].capitalize())
        emoji_label = QLabel(self.emoji_weather(data['weather'][0]['id']))

        # Style widgets
        for label in [info_label, temperature_label, description_label, emoji_label]:
            label.setStyleSheet("font-size: 40px;")
            label.setAlignment(Qt.AlignCenter)

        # Setup layout
        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(info_label)
        dialog_layout.addWidget(temperature_label)
        dialog_layout.addWidget(emoji_label)
        dialog_layout.addWidget(description_label)
        dialog.setLayout(dialog_layout)

        # Show dialog
        dialog.exec_()

    def emoji_weather(self, emoji_id):
        """Return appropriate weather emoji based on weather condition code"""
        if 200 <= emoji_id <= 232:  # Thunderstorm
            return "⛈"
        elif 300 <= emoji_id <= 321:  # Drizzle
            return "🌦️"
        elif 500 <= emoji_id <= 531:  # Rain
            return "🌧 ☔"
        elif 600 <= emoji_id <= 622:  # Snow
            return "☃ ❄"
        elif 701 <= emoji_id <= 781:  # Atmosphere (fog, haze, etc)
            return "🌫️"
        elif emoji_id == 800:  # Clear
            return "🔆"
        else:  # Default (mostly cloudy)
            return "⛅"


if __name__ == "__main__":
    # Create and run application
    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    weather_app.show()
    sys.exit(app.exec_())


#  emoji
# "🔆"
# "☁"
# "⛅"
# "⛈"
# "🌤"
# "🌥"
# "🌦"
# "🌧"
# "🌨"
# "🌩"
# "🌞"
# "☔"
# "❄"
# "☃"
# "🌬"