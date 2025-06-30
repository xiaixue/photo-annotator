from PIL import Image, ImageDraw, ImageFont
import os
import json
import piexif
import datetime
import math
import random as rnd
import tkinter as tk
import tkinter.filedialog as fd
from tkinter import messagebox as mbx
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import configparser

global langs
langs = {
  "en": ["评论", "重要性", "日期", "时间", "地方", "影响半径", "类型", "高", "中" ,"低", "信息", "请选择您要保存图片的文件夹", "错误", "数据无效。请检查输入的数据。", "照片注释器"],
  "es": ["Comentario", "Importancia", "Fecha", "Hora", "Ubicación", "Radio", "Tipo", "Alto", "Medio", "Bajo", "Información", "Selecciona la carpeta donde quieres guardar las imágenes.", "Error", "Dato inválido. Verificar datos ingresado.", "Anotador de fotos"],
  "en": ["Annotation", "Importance", "Date", "Time", "Location", "Radius", "Type", "High", "Medium", "Low", "Info", "Select the folder where you want to save the pictures", "Error", "Invalid data. Please check the data entered.", "Photo Annotator"]}

def isNumber(text):
  try:
    float(text)
    return True
  except:
    return False

def config():
  config = configparser.ConfigParser()
  config.read('config.ini')
  lang = config["settings"]["lang"]
  return lang

def coordinates_generator(coords, radius):
  coords = coords.split(",")
  radius = float(radius)
  try:
    lat, long = float(coords[0]), float(coords[1])
    x, y, zone = latlon_to_utm(lat, long)
  except:
    return 0
  
  r = radius * math.sqrt(rnd.uniform(0, 1))
  theta = rnd.uniform(0, 2 * math.pi)
  delta_x = r * math.cos(theta)
  delta_y = r * math.sin(theta)

  x = x + delta_x
  y = y + delta_y
  return x, y, zone

def save_database(data_relation):
  with open("./photo_database.json", "w") as f:
    json.dump(data_relation, f, indent= 2)
  return 0

def load_database():
  with open("./photo_database.json", "r") as f:
    data_relation = json.load(f)
  return data_relation

def set_exif_datetime_gps(image_path, output_path, dt, lat, lon, file_name):
    """
    Write date/time and GPS coordinates into the EXIF metadata of an image.

    Args:
      image_path (str): Path to the input image.
      output_path (str): Path to save the updated image.
      dt (datetime): Date and time to set in metadata.
      lat (float): Latitude in decimal degrees.
      lon (float): Longitude in decimal degrees.
    """

    def to_deg(value, loc):
      """Convert decimal coordinate into (deg, min, sec) tuple for EXIF"""
      if value < 0:
          value = -value
          loc_value = loc[1]
      else:
          loc_value = loc[0]

      deg = int(value)
      min_float = (value - deg) * 60
      min_ = int(min_float)
      sec = round((min_float - min_) * 60 * 100)
      return ((deg, 1), (min_, 1), (sec, 100)), loc_value

    im = Image.open(image_path)

    # Try to load existing EXIF data
    exif_bytes = im.info.get("exif")
    if exif_bytes:
        exif_dict = piexif.load(exif_bytes)
    else:
        # If no EXIF present, create empty EXIF dict structure
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

    # DateTimeOriginal tag format: "YYYY:MM:DD HH:MM:SS"
    date_str = dt.strftime("%Y:%m:%d %H:%M:%S")
    exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str.encode()
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str.encode()
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str.encode()

    # GPS Info
    if lat is not None and lon is not None:
      gps_ifd = {}

      lat_deg, lat_ref = to_deg(lat, ("N", "S"))
      lon_deg, lon_ref = to_deg(lon, ("E", "W"))

      gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = lat_ref.encode()
      gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_deg
      gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = lon_ref.encode()
      gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_deg

      exif_dict["GPS"] = gps_ifd

    # Insert exif back into image
    exif_bytes_new = piexif.dump(exif_dict)
    im.save(output_path + "\\" + file_name, "jpeg", exif=exif_bytes_new)

    print(f"Metadata saved to {output_path}")

def latlon_to_utm(lat, lon):
  # WGS84 ellipsoid parameters
  a = 6378137.0  # semi-major axis in meters
  f = 1 / 298.257223563  # flattening
  k0 = 0.9996  # scale factor

  # Derived parameters
  e = math.sqrt(f * (2 - f))  # eccentricity

  # Calculate UTM zone
  zone = int((lon + 180) / 6) + 1

  # Central meridian for the zone
  lon0 = (zone - 1) * 6 - 180 + 3
  lon0_rad = math.radians(lon0)

  lat_rad = math.radians(lat)
  lon_rad = math.radians(lon)

  # Auxiliary values
  N = a / math.sqrt(1 - e**2 * math.sin(lat_rad)**2)
  T = math.tan(lat_rad)**2
  C = (e**2 / (1 - e**2)) * math.cos(lat_rad)**2
  A = math.cos(lat_rad) * (lon_rad - lon0_rad)

  # Calculate the meridional arc
  M = a * (
    (1 - e ** 2 / 4 - 3 * e **4 / 64 - 5 * e ** 6 / 256) * lat_rad
    - (3 * e ** 2 / 8 + 3 * e **4 / 32 + 45 * e ** 6 / 1024) * math.sin(2 * lat_rad)
    + (15 * e ** 4 / 256 + 45 * e ** 6 / 1024) * math.sin(4 * lat_rad)
    - (35 * e ** 6 / 3072) * math.sin(6 * lat_rad))

  # Calculate Easting (x)
  easting = k0 * N * (
    A + (1 - T + C) * A**3 / 6 + (5 - 18 * T + T**2 + 72 * C - 58 * (e**2 / (1 - e**2))) * A**5 / 120
  ) + 500000.0  # 500,000 meter offset for the central meridian

  # Calculate Northing (y)
  northing = k0 * (
    M + N * math.tan(lat_rad) * (
      A**2 / 2 + (5 - T + 9 * C + 4 * C**2) * A**4 / 24 + 
      (61 - 58 * T + T**2 + 600 * C - 330 * (e**2 / (1 - e**2))) * A**6 / 720
    ))

  # If in southern hemisphere, add 10,000,000 meters to northing
  if lat < 0:
    northing += 10000000.0

  return easting, northing, zone

def utm_to_latlon(easting, northing, zone, northern_hemisphere=True):
  # WGS84 parameters
  a = 6378137.0
  f = 1 / 298.257223563
  k0 = 0.9996

  e = math.sqrt(f * (2 - f))
  e1sq = e**2 / (1 - e**2)

  # Adjust northing for southern hemisphere
  if not northern_hemisphere:
    northing -= 10000000.0

  # Central meridian of the zone
  lon0 = (zone - 1) * 6 - 180 + 3
  lon0_rad = math.radians(lon0)

  M = northing / k0

  mu = M / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))

  # Footprint latitude
  e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))

  J1 = 3 * e1 / 2 - 27 * e1**3 / 32
  J2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
  J3 = 151 * e1**3 / 96
  J4 = 1097 * e1**4 / 512

  fp_lat = mu + J1 * math.sin(2 * mu) + J2 * math.sin(4 * mu) + J3 * math.sin(6 * mu) + J4 * math.sin(8 * mu)

  sin_fp = math.sin(fp_lat)
  cos_fp = math.cos(fp_lat)
  tan_fp = math.tan(fp_lat)

  C1 = e1sq * cos_fp**2
  T1 = tan_fp**2
  N1 = a / math.sqrt(1 - e**2 * sin_fp**2)
  R1 = a * (1 - e**2) / (1 - e**2 * sin_fp**2)**1.5
  D = (easting - 500000.0) / (N1 * k0)

  # Latitude
  lat_rad = fp_lat - (N1 * tan_fp / R1) * (
    D**2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * e1sq) * D**4 / 24 +
    (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * e1sq - 3 * C1**2) * D**6 / 720)

  # Longitude
  lon_rad = lon0_rad + (
    D - (1 + 2 * T1 + C1) * D**3 / 6 +
    (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * e1sq + 24 * T1**2) * D**5 / 120
  ) / cos_fp

  return math.degrees(lat_rad), math.degrees(lon_rad)

def random_date_generator(ini_date, end_date, ini_hour, end_hour):
  ini_date = ini_date
  end_date = end_date + datetime.timedelta(days= 1)
  ini_hour = int(ini_hour[:2]) + int(ini_hour[-2:]) / 60
  end_hour = int(end_hour[:2]) + int(end_hour[-2:]) / 60

  dy_span = int((end_date- ini_date).days)
  hr_span = int(end_hour - ini_hour)

  rnd_dy_diff = rnd.randint(0, dy_span)
  rnd_hr_diff = round(rnd.uniform(0, hr_span) * 4) / 4

  rnd_date = ini_date + datetime.timedelta(days= rnd_dy_diff, hours= rnd_hr_diff + ini_hour)

  return rnd_date

class Writer():
  def __init__(self, root, folder_path):
    self.root = root
    self.changer = 0
    self.bg = "#fff"
    self.font = ("Segoe UI", 12)
    self.confi()

    self.database = load_database()
    
    self.left_frame = tk.Frame(self.root, bg= self.bg)
    self.left_frame.place(relx=0, rely=0, relheight=1, relwidth=0.7)
    self.right_frame = tk.Frame(self.root, bg= self.bg)
    self.right_frame.place(relx=0.7, rely=0, relheight=1, relwidth=0.3)
    
    self.next_button = tk.Button(self.right_frame, text= "→", bg= self.bg, bd= 0, font= self.font, command= lambda: self.image_changer("next"))
    self.back_button = tk.Button(self.right_frame, text= "←", bg= self.bg, bd= 0, font= self.font, command= lambda: self.image_changer("back"))
    self.save_button = tk.Button(self.right_frame, text= "💾", bg= self.bg, bd= 0, font= self.font, command= lambda: self.save_fun())

    self.next_button.place(relx=0.55, rely=0.85, relheight=0.05, relwidth=0.15)
    self.back_button.place(relx=0.3, rely=0.85, relheight=0.05, relwidth=0.15)
    self.save_button.place(relx=0.45, rely=0.85, relheight=0.05, relwidth=0.1)
    
    entradas = [langs[self.lang][0], langs[self.lang][1], langs[self.lang][2], langs[self.lang][3], langs[self.lang][4], langs[self.lang][5], langs[self.lang][6]]
    
    self.notes = tk.StringVar()
    self.prior = tk.StringVar(); self.prior.set(langs[self.lang][8])
    self.fecha_ini = tk.StringVar()
    self.fecha_end = tk.StringVar()
    self.types = tk.StringVar()
    self.types_list = []
    self.hour_from_var = tk.StringVar(); self.hour_from_var.set("00:00")
    self.hour_to_var = tk.StringVar(); self.hour_to_var.set("00:00")
    self.coordinates_var = tk.StringVar()
    self.radius_var = tk.StringVar(); self.radius_var.set("0")
  
    self.fecha_ini.set((datetime.date.today()).strftime("%Y-%m-%d"))
    self.fecha_end.set((datetime.date.today()).strftime("%Y-%m-%d"))
    
    tcl_up_or_down = self.right_frame.register(self.up_or_down)
    
    for i in range(7):
      self.label = ttk.Label(self.right_frame, text=f"{entradas[i]}:", background= self.bg)
      self.label.place(relx= 0.1, rely= 0.05 + 0.1 * i, relwidth= 0.8, relheight= 0.05)
      
      if i == 0:
        self.entry = ttk.Entry(self.right_frame, background= self.bg , font= self.font, textvariable= self.notes)
        self.entry.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.8, relheight= 0.05)
      
      if i == 2:
        self.date = tk.Spinbox(self.right_frame, background= self.bg , readonlybackground= self.bg, bd= 1, font= self.font, state= "readonly", textvariable= self.fecha_ini, command= (tcl_up_or_down, "%d", "i"))
        self.date_f = tk.Spinbox(self.right_frame, background= self.bg , readonlybackground= self.bg, bd= 1, font= self.font, state= "readonly", textvariable= self.fecha_end, command=(tcl_up_or_down, "%d", "e"))
        
        self.last_ini_date = datetime.datetime.strptime(self.fecha_ini.get(), "%Y-%m-%d").date()
        self.last_end_date = datetime.datetime.strptime(self.fecha_end.get(), "%Y-%m-%d").date()
        
        self.date.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)
        self.date_f.place(relx=0.53, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)
      elif i == 1:
        self.importance = ttk.Combobox(self.right_frame, background= self.bg, font= self.font, state= "readonly", values= [langs[self.lang][7], langs[self.lang][8] ,langs[self.lang][9]], textvariable= self.prior)
        self.importance.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.8, relheight= 0.05)
      elif i == 3:
        self.hour_from = ttk.Entry(self.right_frame, background= self.bg , font= self.font, textvariable= self.hour_from_var)
        self.hour_to = ttk.Entry(self.right_frame, background= self.bg , font= self.font, textvariable= self.hour_to_var)
        
        self.hour_from.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)
        self.hour_to.place(relx=0.53, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)
      elif i == 4:
        self.coords_entry = ttk.Entry(self.right_frame, background= self.bg , font= self.font, textvariable= self.coordinates_var)
        self.coords_entry.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.8, relheight= 0.05)
      elif i == 5:
        self.radius_entry = ttk.Entry(self.right_frame, background= self.bg , font= self.font, textvariable= self.radius_var)
        self.radius_entry.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)

        self.radius_unit = ttk.Label(self.right_frame, background= self.bg , font= self.font, text= "m").place(relx=0.5, rely= 0.1 + 0.1 * i, relwidth= 0.37, relheight= 0.05)
      elif i == 6:
        self.type_entry = ttk.Combobox(self.right_frame, background= self.bg, font= self.font, values= self.types_list, textvariable= self.types)
        self.type_entry.place(relx=0.1, rely= 0.1 + 0.1 * i, relwidth= 0.8, relheight= 0.05)
    
    self.images = []
    self.images_paths = []
    lista_archivos = os.listdir(folder_path)

    filtered_files = [f for f in lista_archivos if f.endswith("g")]
    
    for k, file_name in enumerate(filtered_files):
      if file_name[-1] != "g":
        k -= 1
        continue
      absolute_path = os.path.join(folder_path, file_name)
      image_opened = Image.open(absolute_path)
      self.images.append(image_opened)
      self.images_paths.append(absolute_path)
      
    self.fig = Figure()
    self.ax = self.fig.add_subplot()
    self.canvas = FigureCanvasTkAgg(self.fig, master=self.left_frame)
    self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    self.image_on_ax = self.ax.imshow(self.images[self.changer])  # Show first image
    
    self.canvas.draw()

    while True:
      mbx.showinfo(title= langs[self.lang][10], message= langs[self.lang][11])
      self.safe_output = fd.askdirectory()
      if self.safe_output == "":
        continue
      break
  
  def confi(self):
    config = configparser.ConfigParser()
    config.read('config.ini')

    self.write_font = config["settings"]["font"]
    self.red = config["settings"].getint("red")
    self.green = config["settings"].getint("green")
    self.blue = config["settings"].getint("blue")
    self.phone = config["settings"]["phone"]
    self.lang = config["settings"]["lang"]
    return
  
  def image_viewer(self, control= 0):        
  
    #self.fig, self.ax = plt.subplots()
    #self.ax.imshow(self.images[control])
    #self.ax.set_xticks([])
    #self.ax.set_yticks([])
    #self.ax.set_xticklabels([])
    #self.ax.set_yticklabels([])
    #self.canvas = FigureCanvasTkAgg(self.fig, master= self.left_frame)
    #self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    self.image_on_ax = self.ax.imshow(self.images[control])
    self.canvas.draw()
  
  def up_or_down(self, direction, which):
    if direction == "down":
      if which == "e":
        self.fecha_end.set((datetime.datetime.strptime(self.fecha_end.get(), "%Y-%m-%d") + datetime.timedelta(days= -1)).strftime("%Y-%m-%d"))
      else:
        
        self.fecha_ini.set((datetime.datetime.strptime(self.fecha_ini.get(), "%Y-%m-%d") + datetime.timedelta(days= -1)).strftime("%Y-%m-%d"))
    else:
      if which == "e":
        self.fecha_end.set((datetime.datetime.strptime(self.fecha_end.get(), "%Y-%m-%d") + datetime.timedelta(days= 1)).strftime("%Y-%m-%d"))
      else:
        self.fecha_ini.set((datetime.datetime.strptime(self.fecha_ini.get(), "%Y-%m-%d") + datetime.timedelta(days= 1)).strftime("%Y-%m-%d"))
  
  def image_changer(self, change):
    if change == "next":
      if self.changer + 1 > len(self.images) - 1: 
        self.changer = 0
      else:
        self.changer += 1
    else:
      if self.changer < 1: 
        self.changer = len(self.images) - 1
      else:
        self.changer -= 1
        
    self.image_on_ax.remove()
    self.image_on_ax = None
    self.image_viewer(self.changer)
  
  def save(self):

    notes = self.notes.get()
    prior = self.prior.get()
    types = self.types.get()

    if types not in self.types_list:
      self.types_list.append(types)
      self.type_entry['values'] = self.types_list

    # Parse dates
    fecha_ini = datetime.datetime.strptime(self.fecha_ini.get(), "%Y-%m-%d")
    fecha_end = datetime.datetime.strptime(self.fecha_end.get(), "%Y-%m-%d")

    if fecha_end < fecha_ini:
        fecha_ini, fecha_end = fecha_end, fecha_ini

    # Parse hours
    hour_from_var = self.hour_from_var.get()
    hour_to_var = self.hour_to_var.get()

    if hour_to_var < hour_from_var:
        return 0

    # Generate random date & time
    gen_date = random_date_generator(fecha_ini, fecha_end, hour_from_var, hour_to_var)

    # Generate coordinates
    coordinates_var = self.coordinates_var.get()
    radius_var = self.radius_var.get()

    if isNumber(radius_var) == False or float(radius_var) < 0:
        return 0

    coords = coordinates_generator(coordinates_var, radius_var)

    if coords == 0:
        lat, long = None, None
    else:
        lat, long = utm_to_latlon(coords[0], coords[1], coords[2])

    # Work on image: open original
    image_path = self.images_paths[self.changer]
    file_name = image_path.split("\\")[-1]

    im = Image.open(image_path)

    # Draw the date string on image
    draw = ImageDraw.Draw(im)
    try:
      font = ImageFont.truetype(f"{self.write_font}.ttf", 40)
    except:
      font = ImageFont.load_default()
      
    write_date = gen_date.strftime("%d/%m/%Y %H:%M")
    width, height = im.size
    bbox = draw.textbbox((0, 0), f"{self.phone} {write_date}", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = (width - text_width - 20, height - text_height - 20)
    draw.text(position, f"{self.phone} {write_date}", font= font, fill= (self.red, self.green, self.blue))

    # Save temporary image with text (but without EXIF)
    temp_path = self.safe_output + "\\" + file_name
    im.save(temp_path, "jpeg")

    # Now call your existing function to insert EXIF metadata
    set_exif_datetime_gps(temp_path, self.safe_output, gen_date, lat, long, file_name)

    # Save database
    self.database[self.images_paths[self.changer]] = {
        "note": notes,
        "coordinates": [lat, long],
        "importance": prior,
        "date": gen_date.strftime("%Y-%m-%d %H:%M"),
        "category": types
    }

    save_database(self.database)
    return

  def save_fun(self):
    state = self.save()
    if state == 0:
      mbx.showerror(title= langs[self.lang][12], message= langs[self.lang][13])
    return 
  

if __name__ == "__main__":
  
  root = tk.Tk()
  root.withdraw()
  
  while True:
    mbx.showinfo(title= "Info", message="Select the folder where you have the pictures")
    x = fd.askdirectory(initialdir="../")
    if x == "":
      continue
    break
  
  lang_cur = config()
  root.deiconify()  # Show root window again after dialogs
  root.title(langs[lang_cur][-1])
  root.iconbitmap("./assets/icon.ico")
  root.geometry("1200x500") 
  a = Writer(root, x)
  root.mainloop()