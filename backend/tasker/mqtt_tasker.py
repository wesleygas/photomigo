from app.db import engine
from app.models import Device, Group
from app.config import settings
from sqlmodel import Session, select
import paho.mqtt.client as mqtt
import datetime
import time
import requests
import json 

import logging
logging.basicConfig()
logger = logging.getLogger('sqlalchemy.engine')
logger.setLevel(logging.WARN)


switch_photo_requests = {}
login_requests = {}
reconnected = False


def on_connect(client, userdata, flags, reason_code, properties):
    global reconnected
    print(f"Connected with result code {reason_code}")
    client.subscribe("portrait/skip/#")
    reconnected = True


def on_message(client, userdata, msg):
    global switch_photo_requests, login_requests
    topic: str = msg.topic
    print(topic+" "+str(msg.payload))
    if(topic.startswith('portrait/skip/')):
        if(msg.payload == b'SKIP'):
            try:
                groupid = topic.split('/')[2]
                #rint("received skip request for group", groupid)
                switch_photo_requests[int(groupid)] = True
            except (IndexError,ValueError):
                print(f"Topic {topic} has invalid groupid")
                pass
    if(topic.startswith('portrait/device/')):
        if(msg.payload == b'LOGIN'):
            try:
                device_id = topic.split('/')[2]
                login_requests[device_id] = True
            except IndexError :
                print(f"Topic {topic} has invalid device_id")


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.username_pw_set(username=settings.MQTT_USER, password=settings.MQTT_PASSWORD)
mqttc.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)

def sub_to_machines(session: Session):
    global reconnected
    if(reconnected):
        devices = session.exec(select(Device)).all()
        for device in devices:
            print(f"subbing to portrait/device/{device.id}")
            mqttc.subscribe(f"portrait/device/{device.id}")
    reconnected = False


def trigger_group_renew(group_id):
    mqttc.publish(f"portrait/group/{group_id}", "RENEW", qos=1)

def get_next_asset_id(album_id, current_asset):
    try:
        response = requests.get(f"{settings.IMMICH_API_PATH}/albums/{album_id}?withoutAssets=true", stream=True, headers={"x-api-key": settings.IMMICH_API_KEY})
        assetcount = response.json()['assetCount']
        return (current_asset+1)%assetcount
    except Exception as e:
        print(e)
        return 0

def send_rollover_command(session: Session, group: Group):
    group.last_rollover = datetime.datetime.now()
    group.current_asset = get_next_asset_id(group.album_id, group.current_asset)
    trigger_group_renew(group.id)
    return group


# a cada 30 segundos, checa se passou o tempo necessário para atualizar as imagens
def timeout_check(session: Session):
    groups = session.exec(select(Group)).all()
    now = datetime.datetime.now()
    for group in groups:
        if(now - group.last_rollover > datetime.timedelta(minutes=2)):
            send_rollover_command(session, group)
            session.add(group)
    session.commit()

def handle_login_requests(session: Session):
    global login_requests
    if(not login_requests):
        return
    device_ids = login_requests.keys()
    devices = session.exec(select(Device).where(Device.id.in_(device_ids)))
    login_requests = {}
    for device in devices:
        mqttc.publish(f"portrait/login/{device.id}", json.dumps({"groupid": device.group_id, "api_url": settings.API_URL}))


def switch_photo_check(session: Session):
    global switch_photo_requests
    if(not switch_photo_requests):
        return
    group_ids = switch_photo_requests.keys()
    now = datetime.datetime.now()
    groups = session.exec(select(Group).where(Group.id.in_(group_ids)))
    switch_photo_requests = {}
    for group in groups:
        if(now - group.last_skip_request > datetime.timedelta(seconds=5)):
            group.last_skip_request = now
            group = send_rollover_command(session, group)
            session.add(group)
    session.commit()


def main(session: Session):
    mqttc.loop_start()
    while 1:
        sub_to_machines(session)
        handle_login_requests(session)
        timeout_check(session)
        switch_photo_check(session)
        time.sleep(2)
    mqttc.loop_stop()
    pass



with Session(engine) as session:
    main(session)

