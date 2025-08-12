import io
import os
import logging
import asyncio
import aiohttp

from dotenv import load_dotenv
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from aiogram import Bot, Dispatcher, F, Router, types

from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator

import keyboard as kb
from meteostat import Daily, Point

# Load environment variables from .env file
load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')
weather_api = os.getenv('OWM_API_KEY')

# Initialize bot and dispatcher
bot = Bot(token=bot_token)
dp = Dispatcher()
router = Router()


# Define possible states for the weather bot using FSM
class WeatherStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_city_history = State()


# Handler for the /start command
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply(f"Hi {message.from_user.first_name} ✋ !\
                        \nI'm weather bot!"
                        " 🔆\nPlease select what information"
                            "you want to receive ⬇",
                        reply_markup=kb.main)


# Handler for button clicks ("Current weather" or "Weather history")
@router.message(F.text.in_(["Current weather 🌤️", "Weather history (1 month)"]))
async def handle_buttons(message: Message, state: FSMContext):

    if message.text == "Current weather 🌤️":
        await message.answer("Please write city name: ",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(WeatherStates.waiting_for_city)

    elif message.text == "Weather history (1 month)":

        await message.answer("Please write city name:",
                             reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(WeatherStates.waiting_for_city_history)


# Handler for processing city name input
@router.message(WeatherStates.waiting_for_city)
async def current_weather(message: Message, state: FSMContext):
    city = message.text.strip()
    await state.clear()  # Resets the FSM state after processing

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "q": city,
                "lang": "en",
                "appid": weather_api,
                "units": "metric"
            }
            # Get current weather
            url = "https://api.openweathermap.org/data/2.5/weather"
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                weather = await response.json()
                # Extract weather data
                temp = weather['main']['temp']
                desc = weather['weather'][0]['description']

                await message.answer(
                    f"Current weather in {city.capitalize()}:\n"
                    f"🌡 Temperature: {round(temp, 1)} °C\n"
                    f"⛅ Description: {desc.capitalize()}",
                    reply_markup=kb.main
                )
    except Exception as e:
        await message.answer(
            f"Error: {str(e)}",
            reply_markup=kb.main
        )


# Handler for processing city name input for history
@router.message(WeatherStates.waiting_for_city_history)
async def get_history_data(message: Message, state: FSMContext):
    city = message.text.strip()
    lat, lon = await get_coordinates(city)

    if None in (lat, lon):
        await message.answer(
            "Could not get coordinates for this city",
            reply_markup=kb.main
        )
        await state.clear()  # Resets the FSM state after processing
        return

    try:
        # Set date range (last 30 days)
        end = datetime.now()
        start = end - timedelta(days=30)
        data = Daily(Point(lat, lon), start, end).fetch()  # Get hist. data

        # Create figure with two subplots (temperature and wind)
        fig, (ax_temp, ax_wind) = plt.subplots(
            nrows=2,
            ncols=1,
            figsize=(12, 10),
            sharex=True,
            gridspec_kw={
                'height_ratios': [3, 1],
                'hspace': 0.25
                }
        )
        # Top Plot
        ax_temp.plot(data.index, data['tmin'], label='Minimum t°C',
                     color='blue', linestyle='--', linewidth=1)
        ax_temp.plot(data.index, data['tmax'], label='Maximum t°C',
                     color='red', linestyle='--', linewidth=1)

        ax_temp.yaxis.set_major_locator(DayLocator(interval=2))
        ax_temp.set_title(f'Temperature in {city.capitalize()}', pad=10)
        ax_temp.set_ylabel('Temperature (°C)')
        ax_temp.legend(loc='upper right')
        ax_temp.grid()

        # Bottom Plot
        ax_wind.bar(data.index, data['wspd'], label='Wind speed',
                    color='green', alpha=0.5, width=0.8)
        date_format = DateFormatter("%d.%m")
        ax_wind.xaxis.set_major_formatter(date_format)
        ax_wind.xaxis.set_major_locator(DayLocator(interval=2))
        ax_wind.yaxis.set_major_locator(DayLocator(interval=5))

        ax_wind.set_title(f'Wind speed in {city.capitalize()}', pad=10)
        ax_wind.set_ylabel('Wind (m/s)')
        ax_wind.grid()

        # Rotate x-axis labels for both subplots
        for ax in [ax_temp, ax_wind]:
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=7)

        # Adjust layout
        fig.tight_layout()
        fig.subplots_adjust(
            left=0.1,
            right=0.95,
            top=0.9,
            bottom=0.1
        )

        # Save plot to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        buf.seek(0)

        photo = BufferedInputFile(buf.getvalue(), filename="weather.png")

        # Send plot as photo
        await message.answer_photo(
            photo=photo,
            caption="Temperature graph",
            reply_markup=kb.main
        )
        plt.close()

    except Exception as e:
        await message.answer(
            f"Error: {str(e)}",
            reply_markup=kb.main
        )
    finally:
        await state.clear()


# Get coordinates city for load historycal data
async def get_coordinates(city: str):
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city, "count": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                # Get latitude and longitude
                if data.get('results'):
                    return (
                        data['results'][0]['latitude'],
                        data['results'][0]['longitude']
                    )
    except Exception as e:
        logging.error(f"Coordinates error: {e}")
    return None, None


# Enter point
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.run_until_complete(main())
    else:
        asyncio.run(main())
