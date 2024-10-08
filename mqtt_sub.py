import logging
import os

import fileutils
import paho.mqtt.client as paho
from paho.mqtt.enums import CallbackAPIVersion
from sqlite3utils import SQLite, create_table, write_row

TABLE_NAME = 'permittedlist'
PERMITTED_FILE: str = os.environ.get('PERMITTED_FILE')  # type: ignore
DATABASE_FILE: str = os.environ.get('DATABASE_FILE')  # type: ignore

MQTT_CLIENT_ID: str = os.environ.get('CLIENT_ID')  # type: ignore
MQTT_HOST: str = os.environ.get('HOST')  # type: ignore
MQTT_USERNAME: str = os.environ.get('USERNAME')  # type: ignore
MQTT_PASSWORD: str = os.environ.get('PASSWORD')  # type: ignore


conn = SQLite(DATABASE_FILE)
logging.basicConfig(level=logging.DEBUG)


def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f'CONNACK received with code {rc}.')

    create_table(table_name=TABLE_NAME, conn=conn)


def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    logging.info(f'Subscribed: {str(mid)} {str(granted_qos)}')


def on_message(client, userdata, msg):
    logging.info(f'{msg.topic} {str(msg.qos)} {str(msg.payload)}')

    try:
        payload = str(msg.payload.decode())
        write_row(
            table_name=TABLE_NAME,
            rowdict={'steamid64': payload},
            conn=conn,
        )
        fileutils.append_row(PERMITTED_FILE, payload)
    except Exception as exc:
        logging.error(exc)


mqtt_client = paho.Client(
    client_id=MQTT_CLIENT_ID,
    userdata=None,
    protocol=paho.MQTTv5,
    callback_api_version=CallbackAPIVersion.VERSION2,
)

mqtt_client.tls_set(tls_version=paho.ssl.PROTOCOL_TLS)  # type: ignore
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_HOST, 8883)

mqtt_client.on_connect = on_connect
mqtt_client.on_subscribe = on_subscribe
mqtt_client.on_message = on_message

mqtt_client.subscribe('steamid/#', qos=1)

try:
    logging.info('Press CTRL+C to exit...')
    mqtt_client.loop_forever()
except Exception as exc:
    logging.info('Caught an Exception, something went wrong...')
    logging.exception(exc)
finally:
    logging.info('Disconnecting from the MQTT broker')
    mqtt_client.disconnect()
