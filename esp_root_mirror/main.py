# import mrequests
# from ili9341 import Display, color565
# from xpt2046 import Touch
# from machine import idle, Pin, SPI
import time
import ui_handler
import network
import machine
import json

group_id = -1
login_info = None
is_logged_in = False
portraitname = f"retrato_{machine.unique_id().hex()[:6]}"
ui = ui_handler.UI_handler(machine_name=portraitname)

wlan = network.WLAN(network.STA_IF)
if not wlan.isconnected():
    ui.setup_network()

from umqtt.robust import MQTTClient

curr_image_url = ""
new_image = False

def sub_cb(topic, msg):
    global new_image, curr_image_url, login_info
    print((topic,msg))
    if(topic == b"portrait/group/{}".format(group_id)):
        print("received update_request")
        if(msg == b'RENEW'):
            new_image = True
    if(topic == b"portrait/login/{}".format(portraitname)):
        print("received group_id")
        login_info = json.loads(msg)

with open("mqtt.json", 'rb') as f:
    mc = json.load(f)    
    mqtt = MQTTClient(portraitname, mc['broker'], port=mc['port'], user=mc['user'], password=mc['password'])

mqtt.set_callback(sub_cb)


if not mqtt.connect():
    print("New session being set up")
    mqtt.subscribe(f"portrait/login/{portraitname}")
    mqtt.subscribe("retrato/image_url")
    

last_login_request = 0

while 1:
    mqtt.check_msg()
    if(is_logged_in):
        if(new_image):
            print("drawing image")
            ui.update_image()
            new_image = False
        if ui.wants_skip:
            mqtt.publish(f"portrait/skip/{group_id}", b'SKIP')
            ui.wants_skip = False
    elif(not login_info):
        if(time.time() - last_login_request > 5):
            last_login_request = time.time()
            mqtt.publish(f"portrait/device/{portraitname}", b"LOGIN")
    else:
        group_id = login_info['groupid']
        ui.api_url = login_info['api_url']
        print(f"loggin in to group {group_id}")
        mqtt.subscribe(f'portrait/group/{group_id}')
        ui.update_image()
        is_logged_in = True