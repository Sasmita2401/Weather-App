import tkinter as tk
from tkinter import messagebox
import requests
from PIL import Image, ImageTk, ImageSequence
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------- CONFIG ----------------
API_KEY = "YOUR_OPENWEATHER_API_KEY_HERE"  # Replace with your own key locally
BASE_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
BASE_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

# ---------------- SCROLLABLE FRAME FUNCTION ----------------
def create_scrollable_frame(master, title):
    outer_frame = tk.LabelFrame(master, text=title)
    outer_frame.pack(fill="both", expand=True, padx=10, pady=5)

    canvas = tk.Canvas(outer_frame, height=150)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    inner_frame = tk.Frame(canvas)
    canvas.create_window((0,0), window=inner_frame, anchor="nw")

    return inner_frame

# ---------------- WEATHER ASSETS ----------------
weather_assets = {
    "Clear": {"gif": "sunny.gif", "bg": "#87CEEB"},       # Sky blue
    "Clouds": {"gif": "cloudy.gif", "bg": "#B0C4DE"},    # Light steel blue
    "Rain": {"gif": "rain.gif", "bg": "#708090"},        # Slate gray
    "Drizzle": {"gif": "rain.gif", "bg": "#708090"},
    "Thunderstorm": {"gif": "storm.gif", "bg": "#2F4F4F"}, # Dark slate gray
    "Snow": {"gif": "snow.gif", "bg": "#F0F8FF"},        # Alice blue
    "Mist": {"gif": "cloudy.gif", "bg": "#C0C0C0"},      # Gray
}

# ---------------- IP-BASED LOCATION ----------------
def get_location_by_ip():
    try:
        response = requests.get("https://ipinfo.io/json")
        response.raise_for_status()
        data = response.json()
        city = data.get("city")
        country = data.get("country")
        if city and country:
            return f"{city},{country}"
        elif city:
            return city
        else:
            return None
    except Exception:
        return None

# ---------------- DISPLAY ANIMATED WEATHER ICON ----------------
def display_weather_gif(condition):
    asset = weather_assets.get(condition, {"gif": "sunny.gif", "bg": "#87CEEB"})
    root.configure(bg=asset["bg"])

    try:
        gif_image = Image.open(asset["gif"])
    except Exception:
        return

    frames = [ImageTk.PhotoImage(frame.copy().convert('RGBA')) for frame in ImageSequence.Iterator(gif_image)]

    def animate(counter=0):
        frame = frames[counter]
        icon_label.config(image=frame)
        icon_label.image = frame
        root.after(150, animate, (counter+1)%len(frames))

    animate()

# ---------------- API CALLS ----------------
def get_weather_data(city):
    try:
        params = {"q": city, "appid": API_KEY, "units": unit_var.get()}
        response = requests.get(BASE_WEATHER_URL, params=params)
        response.raise_for_status()
        current_data = response.json()

        forecast_response = requests.get(BASE_FORECAST_URL, params=params)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        return current_data, forecast_data

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            messagebox.showerror("API Error", "Invalid or inactive API key. Check your OpenWeatherMap account.")
        elif response.status_code == 404:
            messagebox.showerror("City Error", "City not found. Check spelling or add country code (e.g., Tiruchengode,IN).")
        else:
            messagebox.showerror("HTTP Error", str(http_err))
        return None, None
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return None, None

# ---------------- UPDATE WEATHER ----------------
def update_weather():
    city = city_entry.get().strip()

    if not city:
        auto_city = get_location_by_ip()
        if auto_city:
            city = auto_city
            city_entry.delete(0, tk.END)
            city_entry.insert(0, city)
        else:
            messagebox.showwarning("Input Error", "Please enter a city name or check your internet connection.")
            return

    if "," not in city:
        city = city + ",IN"

    current_data, forecast_data = get_weather_data(city)
    if not current_data:
        return

    temp = current_data["main"]["temp"]
    humidity = current_data["main"]["humidity"]
    weather_desc = current_data["weather"][0]["description"].title()
    wind_speed = current_data["wind"]["speed"]
    pressure = current_data["main"]["pressure"]
    visibility = current_data.get("visibility", "N/A")

    weather_label.config(text=f"Weather: {weather_desc}")
    temp_label.config(text=f"Temperature: {temp}° {'C' if unit_var.get()=='metric' else 'F'}")
    humidity_label.config(text=f"Humidity: {humidity}%")
    wind_label.config(text=f"Wind Speed: {wind_speed} m/s")
    pressure_label.config(text=f"Pressure: {pressure} hPa")
    visibility_label.config(text=f"Visibility: {visibility/1000 if visibility != 'N/A' else 'N/A'} km")

    main_condition = current_data["weather"][0]["main"]
    display_weather_gif(main_condition)

    for widget in hourly_frame.winfo_children():
        widget.destroy()
    hours = forecast_data["list"][:12]
    hour_temps = []
    for hour in hours:
        dt_txt = hour["dt_txt"]
        hour_temp = hour["main"]["temp"]
        hour_desc = hour["weather"][0]["description"].title()
        tk.Label(hourly_frame, text=f"{dt_txt} | {hour_temp}° | {hour_desc}").pack(anchor="w")
        hour_temps.append(hour_temp)

    for widget in daily_frame.winfo_children():
        widget.destroy()
    daily_data = {}
    for item in forecast_data["list"]:
        date_str = item["dt_txt"].split(" ")[0]
        temp_day = item["main"]["temp"]
        desc = item["weather"][0]["description"].title()
        if date_str not in daily_data:
            daily_data[date_str] = {"temps": [], "descs": []}
        daily_data[date_str]["temps"].append(temp_day)
        daily_data[date_str]["descs"].append(desc)
    for date, info in list(daily_data.items())[:7]:
        avg_temp = sum(info["temps"]) / len(info["temps"])
        main_desc = max(set(info["descs"]), key=info["descs"].count)
        tk.Label(daily_frame, text=f"{date} | {round(avg_temp,1)}° | {main_desc}").pack(anchor="w")

    fig.clear()
    ax = fig.add_subplot(111)
    ax.plot(range(1, len(hour_temps)+1), hour_temps, marker='o', color='orange')
    ax.set_title("12-interval (3-hr) Temperature Forecast")
    ax.set_xlabel("Interval")
    ax.set_ylabel(f"Temperature ({'°C' if unit_var.get()=='metric' else '°F'})")
    ax.grid(True)
    canvas.draw()

# ---------------- GUI SETUP ----------------
root = tk.Tk()
root.title("Advanced Weather App - Internship Ready")
root.geometry("520x780")

city_entry = tk.Entry(root, font=("Arial", 14))
city_entry.pack(pady=10)
city_entry.insert(0, "Enter City Name (Leave blank for automatic location)")

unit_var = tk.StringVar(value="metric")
tk.Radiobutton(root, text="Celsius", variable=unit_var, value="metric").pack()
tk.Radiobutton(root, text="Fahrenheit", variable=unit_var, value="imperial").pack()

tk.Button(root, text="Get Weather", command=update_weather, bg="blue", fg="white").pack(pady=10)

weather_label = tk.Label(root, text="Weather: ", font=("Arial", 12))
weather_label.pack()
temp_label = tk.Label(root, text="Temperature: ", font=("Arial", 12))
temp_label.pack()
humidity_label = tk.Label(root, text="Humidity: ", font=("Arial", 12))
humidity_label.pack()
wind_label = tk.Label(root, text="Wind Speed: ", font=("Arial", 12))
wind_label.pack()
pressure_label = tk.Label(root, text="Pressure: ", font=("Arial", 12))
pressure_label.pack()
visibility_label = tk.Label(root, text="Visibility: ", font=("Arial", 12))
visibility_label.pack()

icon_label = tk.Label(root)
icon_label.pack(pady=10)

hourly_frame = create_scrollable_frame(root, "Hourly Forecast (3-hr intervals)")
daily_frame = create_scrollable_frame(root, "Daily Forecast (average temp)")

fig = plt.Figure(figsize=(5,2))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(pady=10)

root.mainloop()
