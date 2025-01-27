import mrequests
from ili9341 import Display, color565
from xpt2046 import Touch
from machine import Pin, SPI
import machine
import time

import gc

from parse_bitmap import BMPStreamReader

spi1 = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
spi2 = SPI(2, baudrate=1000000, sck=Pin(25), mosi=Pin(32), miso=Pin(39))
bl_pin = Pin(21, Pin.OUT)

WHITE = color565(255, 255, 255)
BEIGE = color565(224, 209, 175)
BLACK = color565(0,0,0)

# API_BASE_URL = "http://192.168.0.87:8000/api/v1"
IMAGE_ENDPOINT = "/image"
QR_ENDPOINT = "/qrcode"

def draw_centered_text(display, txt, offset_x=0, offset_y=0):
    display.draw_text8x8(
        display.width//2 - len(txt)*8//2 + offset_x,
        display.height//2 - 4 + offset_y,
        txt,
        WHITE,
        background=BLACK
    )

class Button():
    def __init__(self, x, y, w, h, action, title=""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.action = action
        self.title = title
    
    def is_target(self, x, y):
        return ((x >= self.x)
            and (x <= self.x + self.w)
            and (y >= self.y)
            and (y <= self.y + self.h)
        )

def new_image_action(ui, button):
    ui.wants_skip = True
    ui.display.clear(hlines=16)
    draw_centered_text(ui.display, "Enviando Pedido", offset_x=0, offset_y=0)
    ui.menu_active = False

def open_album_qrcode(ui, button):
    ui.draw_bitmap_from_url(ui.api_url+QR_ENDPOINT)
    ui.menu_active = False

def reset_wifi_action(ui, button):
    if(not ui.cancel_wifi_confirm):
        button.title = f"Confirma?"
        ui.draw_button(button, True)
        ui.cancel_wifi_confirm = True
        return
    ui.display.clear(hlines=16)
    from wifi_setup.credentials import Credentials
    Credentials().clear()
    machine.reset()
    ##
    

    

class UI_handler():
    def __init__(self, machine_name):
        self.machine_name = machine_name
        self.display = Display(spi1, dc=Pin(2), cs=Pin(15), rst=Pin(0), width=320, height=240, rotation=0)
        self.bl = bl_pin
        self.bl.on()
        self.buttons = [
            Button(10, 10, 80, 60, new_image_action, title="Nova Foto"),
            Button(10, 80, 80, 60, open_album_qrcode, title="Album QR"),
            Button(10, 170, 80, 60, reset_wifi_action, title="cfg. wifi")
        ]
        self.menu_active = False
        self.cancel_wifi_confirm = False
        self.touch = Touch(spi2, cs=Pin(33), int_pin=Pin(36), int_handler=self.handle_touch)
        self.wants_skip = False
        self.api_url = ""
        
    def _itter_buttons(self):
        for button in self.buttons:
            if(button.active):
                yield button
    
    def update_image(self):
        self.draw_bitmap_from_url(self.api_url+IMAGE_ENDPOINT)
        
    def handle_touch(self, x, y):
        '''Process touchscreen press events.'''
        print(f"Display touched on x:{x} y:{y} ")
        xi = y
        yi = x
        if(self.menu_active):
            if(xi >= 110):
                self.menu_active = False
                self.display.clear(hlines=16)
                self.draw_bitmap_from_url(self.api_url+IMAGE_ENDPOINT)
            for button in self.buttons:
                if(button.is_target(xi, yi)):
                    self.draw_button(button, True)
                    time.sleep(0.2)
                    self.draw_button(button, False)
                    button.action(self, button)
        else:
            self.menu_active = True
            self.draw_menu()
        
    # draw_bitmap_from_url
    def draw_bitmap_from_url(self, url):
#         print("fetching image from", url)
        if not url:
            draw_centered_text(self.display, "Imagem nao encontrada...")
            return False
        try:
            self.display.clear(hlines=16)
            draw_centered_text(self.display, "Carregando imagem...")
            gc.collect()
            r = mrequests.get(url, headers={'accept': 'image/bmp', 'machine': self.machine_name})
            bmp_reader = BMPStreamReader(r)
            self.display.draw_from_pixel_stream(bmp_reader, x=0,y=0, w=bmp_reader.width, h=bmp_reader.height)
            bmp_reader.empty_stream()
            gc.collect()
        except OSError as e:
            print(e)
            self.display.clear(hlines=16)
            draw_centered_text(self.display, "Erro ao carregar imagem")
            draw_centered_text(self.display, str(e), offset_y=16)
            return False
        return True
    
    def draw_button(self, button, pressed):
        print(button)
        bg_color = BEIGE if pressed else WHITE
        self.display.fill_rectangle(button.x, button.y, button.w, button.h, bg_color)
        self.display.draw_rectangle(button.x, button.y, button.w, button.h, BLACK)
        text_size = len(button.title)*8
        xi = button.x + button.w//2 - text_size//2
        yi = button.y + button.h//2 - 4
        self.display.draw_text8x8(xi, yi, button.title, color=WHITE if pressed else BLACK, background=bg_color)
    
    def draw_menu(self):
        self.display.fill_rectangle(0,0, 100, self.display.height, WHITE)
        for button in self.buttons:
            self.draw_button(button, False)
            
    def setup_network(self):
        from wifi_setup.wifi_setup import WiFiSetup
        ws = WiFiSetup(self.machine_name)
        draw_centered_text(self.display, "Configurando Wi-Fi")
        if not ws.connect():
            draw_centered_text(self.display, f"conecte-se na rede", offset_y=-16)
            draw_centered_text(self.display, self.machine_name)
            draw_centered_text(self.display, "para configurar o wifi", offset_y=16)
        sta = ws.connect_or_setup()
        del ws
        self.display.clear(hlines=16)
        draw_centered_text(self.display, "Conectado a", offset_y=-16)
        draw_centered_text(self.display, sta.config("ssid"))
    
