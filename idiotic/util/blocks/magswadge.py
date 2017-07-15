from idiotic.block import Block
import threading
import asyncio
import socket
import struct
import time
import concurrent.futures
import collections
import functools
import json
import logging
import requests

log = logging.getLogger(__name__)

BUTTON_RIGHT = 1
BUTTON_DOWN = 2
BUTTON_LEFT = 3
BUTTON_UP = 4
BUTTON_SELECT = 5
BUTTON_START = 6
BUTTON_B = 7
BUTTON_A = 8

BUTTON_NAMES = {
    BUTTON_RIGHT: "right",
    BUTTON_DOWN: "down",
    BUTTON_LEFT: "left",
    BUTTON_UP: "up",
    BUTTON_SELECT: "select",
    BUTTON_START: "start",
    BUTTON_B: "b",
    BUTTON_A: "a",
}

STATUS_UPDATE = 1
LED_CONTROL = 2
LED_RSSI_MODE = 3
WIFI_UPDATE = 4
WIFI_UPDATE_REPLY = 5
LED_RAINBOW_MODES = 7
CONFIGURE = 8
DEEP_SLEEP = 9

SCAN_INTERVAL = 2
SCAN_SPLAY = 15

SAVE_INTERVAL = 60


RED = (255, 0, 0)
ORANGE = (255, 128, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def dim(color, amt):
    return (int(color[0] * amt), int(color[1] * amt), int(color[2] * amt))


ROOM_COLORS = {
    'unknown': BLACK * 3,
    'living room': dim(RED, .1) + dim(RED, .1) + dim(RED, .1),
    'dining room': dim(GREEN, .1) + dim(GREEN, .1) + dim(GREEN, .1),
    'kitchen': dim(ORANGE, .1) + dim(GREEN, .1) + dim(ORANGE, .1),
    'hallway': dim(CYAN, .1) + dim(CYAN, .1) + dim(CYAN, .1),
    'dylan\'s room': dim(BLUE, .1) + dim(BLUE, .1) + dim(BLUE, .1),
    'basement': dim(CYAN, .1) + dim(BLUE, .1) + dim(CYAN, .1),
    'mark\'s room': dim(RED, .1) + dim(GREEN, .1) + dim(BLUE, .1),
}

def next_room(cur_room, dir=1):
    if cur_room == 'unknown':
        return 'living room' if dir == 1 else 'mark\'s room'

    rooms = list((k for k in ROOM_COLORS.keys() if k != 'unknown'))
    index = rooms.index(cur_room)
    return rooms[(index+dir)%len(rooms)]

def prev_room(cur_room):
    return next_room(cur_room, -1)

def debug(badge_id, *strs):
    log.debug('%s', ' '.join((str(s) for s in strs)))

executor = concurrent.futures.ThreadPoolExecutor(max_workers=64)


class Badge:
    @classmethod
    def from_bytes(cls, packet):
        res = cls(
            packet[1], # wifi_power
            packet[2:8], # connected_bssid
            packet[8], # gpio_state
            packet[9], # gpio_trigger
            packet[10], # trigger_direction
            packet[11], # led_power
            int.from_bytes(packet[12:14], 'big'), # batt_voltage
            int.from_bytes(packet[14:16], 'big'), # update_id
            int.from_bytes(packet[16:18], 'big'), # heap_free
            packet[18], # sleep_performance
            int.from_bytes(packet[20:24], 'big'), # status_count
        )

        return res

    def __init__(self, badge_id):
        self.id = badge_id
        self.game = None
        self.join_time = 0
        self.last_update = 0
        self.buttons = collections.deque(maxlen=16)


def format_mac(mac):
    return ':'.join(('%02X' % d for d in mac))


class BadgeServer(Block):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wifi_scans = {}
        self.badge_ips = {}
        self.badges = {}
        self.socket = None
        self.buttons = {}
        self.join_codes = {}
        self.game_map = {}
        self.default_color = (0,) * 12
        self.packet_queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()

        self.find_modes = {}
        self.find_rooms = {}
        self.learn_active = {}
        self.loc_rooms = {}
        self.always_scan = set()

        self.inputs = {

        }

    def send_packet(self, badge_id, packet):
        debug(badge_id, "packet", packet)
        debug(badge_id, "game state", self.game_map[badge_id])
        if badge_id in self.badge_ips:
            ip = self.badge_ips[badge_id]
            debug(badge_id, "sending...")
            self.socket.sendto(b'\x00\x00\x00\x00\x00\x00' + packet, (ip, 8001))
            debug(badge_id, "sent the packet")
        else:
            log.debug("LOL NOPE CAN'T DO THAT")

    def request_scan(self, badge_id):
        debug(badge_id, "Requesting scan from {}".format(badge_id))
        self.send_packet(badge_id, b'\x04')

    def scan_all(self, subset=1, target=0):
        for badge_id in set(self.badge_ips.keys()):
            if (int(badge_id[-2:], 16) % subset) == target \
                    or badge_id in self.always_scan:
                self.request_scan(badge_id)

    def send_packet_all(self, packet):
        for badge_id in set(self.badge_ips.keys()):
            self.send_packet(badge_id, packet)

    async def rainbow(self, badge_id, runtime=1000, speed=128, intensity=128, offset=0):
        debug(badge_id, "RAINBOW " + badge_id)
        executor.submit(self.send_packet, badge_id, struct.pack(">BBBBHBBB", LED_RAINBOW_MODES, 0, 0, 0, runtime, speed, intensity, offset))

    async def rainbow_all(self, *args, **kwargs):
        for badge_id in set(self.badge_ips.keys()):
            log.debug("Rainbowed a badge")
            await self.rainbow(badge_id, *args, **kwargs)

    async def set_lights_one(self, badge_id, r, g, b):
        debug(badge_id, "Setting lights!")
        await self.rainbow(badge_id, 5000, 32, 128, 64)

    async def set_lights(self, badge_id, *colors):
        r1, g1, b1, r2, g2, b2, r3, g3, b3, r4, g4, b4 = colors
        debug(badge_id, 'setting lights')
        executor.submit(self.send_packet, badge_id, bytes((LED_CONTROL, 0, 0, 0, g1, r1, b1, g2, r2, b2, g3, r3, b3, g4, r4, b4)))

    def rssi(self, badge_id, min=30, max=45, intensity=96):
        self.send_packet(badge_id, struct.pack('BbbB', LED_RSSI_MODE, min, max, intensity))

    def rssi_all(self, min=30, max=45, intensity=96):
        self.send_packet_all(b"\x03" + struct.pack('bbB', min, max, intensity))

    async def set_lights_nogame(self, *args):
        for badge in DEBUG_BADGES:
            if not self.game_map[badge]:
                await self.set_lights(badge, *args)

    def udp_thread(self):
        log.debug("Starting udp_thread")
        self.socket = sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 8000))
        log.debug("Bound")

        our_ip = socket.gethostbyname_ex(socket.gethostname())[2]
        log.info("Our ip: {}".format(our_ip))
        while True:
            #log.info("Starting recv loop")
            try:
                data, (ip, port) = sock.recvfrom(1024)
                #log.debug("THREAD got packet")
                if ip in our_ip:
                    continue

                badge_id = format_mac(data[0:6])
                msg_type = data[6]
                packet = data[7:]

                if badge_id not in self.badge_ips:
                    if not len(self.badge_ips) % 10:
                        log.debug("{} clients".format(len(self.badge_ips)))
                    self.badge_ips[badge_id] = ip
                    self.game_map[badge_id] = None

                if badge_id not in self.badges:
                    self.badges[badge_id] = Badge(badge_id)

                self.loop.call_soon_threadsafe(self.packet_queue.put_nowait, (badge_id, msg_type, packet))
            except KeyboardInterrupt:
                return
            except:
                log.exception("Raised while reading from socket")
                continue

    def save(self):
        with open('magswadge_state.json', 'w') as f:
            json.dump({
                'badge_ips': self.badge_ips,
                'join_codes': self.join_codes,
                'game_map': self.game_map,
                'find_modes': self.find_modes,
                'find_rooms': self.find_rooms,
                'learn_active': self.learn_active,
                'loc_rooms': self.loc_rooms,
            }, f)

    async def run(self):
        next_scan = time.time() + SCAN_INTERVAL
        next_save = time.time() + SAVE_INTERVAL
        next_subset = 0
        threading.Thread(target=self.udp_thread, daemon=True).start()
        try:
            with open('magswadge_state.json') as data_file:
                saved_data = json.load(data_file)
                self.badge_ips = saved_data.get('badge_ips', {})
                self.join_codes = saved_data.get('join_codes', {})
                self.game_map = saved_data.get('game_map', {})
                self.find_modes = saved_data.get('find_modes', {})
                self.find_rooms = saved_data.get('find_rooms', {})
                self.learn_active = saved_data.get('learn_active', {})
                self.loc_rooms = saved_data.get('loc_rooms', {})
        except:
            pass

        while True:
            try:
                badge_id, msg_type, packet = await self.packet_queue.get()
                badge = self.badges[badge_id]

                if msg_type == STATUS_UPDATE:
                    gpio_state, gpio_trigger, gpio_direction = packet[8], packet[9], packet[10]

                    if gpio_trigger:
                        button = BUTTON_NAMES[gpio_trigger]
                        if not gpio_direction:
                            badge.buttons.append(gpio_trigger)

                        if self.game_map[badge_id]:
                            self.send_button_updates(self.game_map[badge_id], badge, button, gpio_direction)
                        else:
                            if gpio_direction:
                                log.debug("Button %s pressed!", BUTTON_NAMES[gpio_trigger])
                                await self.output(1, 'state_' + button)
                                await self.output(1, 'btn_down_' + button)
                            else:
                                await self.output(0, 'state_' + button)
                                await self.output(1, 'btn_up_' + button)
                                log.debug("Button %s released!", BUTTON_NAMES[gpio_trigger])

                                if button == 'start' or button == 'right':
                                    if self.find_modes.get(badge_id) == 'learn':
                                        self.learn_active[badge_id] = not self.learn_active.get(badge_id, False)
                                    elif self.find_modes.get(badge_id) == 'track':
                                        room = self.loc_rooms.get(badge_id, 'unknown')
                                        if room != 'unknown':
                                            self.loc_rooms[badge_id] = room
                                            self.learn_active[badge_id] = True
                                elif button == 'select':
                                    self.learn_active[badge_id] = False
                                    if self.find_modes.get(badge_id, 'track') == 'track':
                                        self.find_modes[badge_id] = 'learn'
                                    else:
                                        self.find_modes[badge_id] = 'track'
                                elif button == 'up':
                                    self.learn_active[badge_id] = False
                                    self.find_modes[badge_id] = 'learn'
                                    self.find_rooms[badge_id] = next_room(self.find_rooms.get(badge_id, 'unknown'))
                                elif button == 'down':
                                    self.learn_active[badge_id] = False
                                    self.find_modes[badge_id] = 'learn'
                                    self.find_rooms[badge_id] = prev_room(self.find_rooms.get(badge_id, 'unknown'))
                                elif button == 'left':
                                    self.find_modes[badge_id] = 'track'
                                    self.learn_active[badge_id] = False

                                    if badge_id in self.always_scan:
                                        self.always_scan.remove(badge_id)
                                    else:
                                        self.always_scan.add(badge_id)

                    elif not gpio_state and not self.game_map[badge_id]:
                        pass
                        #debug(badge_id, 'no gpio received and game map is', self.game_map[badge_id])
                        #await self.set_lights(badge_id, *self.default_color)

                    find_mode = self.find_modes.get(badge_id, 'track')
                    if find_mode == 'track':
                        room_color = ROOM_COLORS.get(self.loc_rooms.get(badge_id, 'unknown'), BLACK * 3)
                        await self.set_lights(badge_id, *room_color, *dim(GREEN, .1))
                    elif find_mode == 'learn':
                        room_color = ROOM_COLORS.get(self.find_rooms.get(badge_id, 'unknown'), BLACK * 3)
                        active = self.learn_active.get(badge_id, False)
                        indic_color = dim(WHITE, .05) if active else BLACK
                        await self.set_lights(badge_id, *room_color, *indic_color)

                elif msg_type == WIFI_UPDATE_REPLY:
                    log.debug("Got wifi reply: {}".format(packet))
                    scan_id = int.from_bytes(packet[0:4], 'big')
                    scan_len = packet[4]

                    if scan_id not in self.wifi_scans:
                        self.wifi_scans[scan_id] = []

                    log.debug("Got scan of {} SSIDs from {}".format(scan_len, badge_id))

                    if scan_len:
                        for i in range(scan_len):
                            self.wifi_scans[scan_id].append((packet[5+8*i:11+8*i], packet[11+8*i]-128))
                    if scan_len == 0 or scan_len <= 47:
                        if scan_id in self.wifi_scans:
                            executor.submit(functools.partial(self.scan_complete, badge_id, scan_id))
                        else:
                            log.warn("Got WIFI UPDATE END for nonexistent scan ID")

                if time.time() > next_scan:
                    next_scan = time.time() + SCAN_INTERVAL
                    try:
                        self.scan_all(SCAN_SPLAY, next_subset)
                        next_subset = (next_subset + 1) % SCAN_SPLAY
                    except:
                        log.exception("Exception scanning")

                if time.time() > next_save:
                    next_save = time.time() + SAVE_INTERVAL
                    self.save()
            except KeyboardInterrupt:
                self.save()
                break
            except:
                log.exception("An exception happened")
            await asyncio.sleep(.001)

    def scan_complete(self, badge_id, scan_id):
        log.debug("Sending off scan with #{} SSIDs".format(len(self.wifi_scans[scan_id])))
        if len(self.wifi_scans[scan_id]):
            #self.publish(u'me.magbadge.badge.scan', badge_id, [{"mac": format_mac(mac), "rssi": rssi} for mac, rssi in self.wifi_scans[scan_id]])
            payload = {
                "username": "swadge_" + badge_id.replace(':', '').lower(),
                "group": "hackafe",
                "time": int(time.time() * 1000),
                "wifi-fingerprint": [{"mac": format_mac(mac).upper(), "rssi": rssi} for mac, rssi in self.wifi_scans[scan_id]]
            }

            mode = self.find_modes.get(badge_id, 'track')
            active = self.learn_active.get(badge_id, False)
            room = self.find_rooms.get(badge_id, 'unknown')

            if mode == 'learn':
                if active and room and room != 'unknown':
                    payload["location"] = room
                    res = requests.post("http://find.hackafe.net/learn", json=payload)
                    log.debug(res)
            elif mode == 'track':
                payload["location"] = "tracking"
                res = requests.post("http://find.hackafe.net/track", json=payload)

                location = res.json().get("location", 'unknown')
                self.loc_rooms[badge_id] = location
                log.debug('badge %s is at %s', badge_id, location)

            #log.debug([{"mac": format_mac(mac).upper(), "rssi": rssi} for mac, rssi in self.wifi_scans[scan_id]])
        del self.wifi_scans[scan_id]
''