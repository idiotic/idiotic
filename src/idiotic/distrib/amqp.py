import asyncio
import logging
import string
from . import base
import json
import pika

log = logging.getLogger("idiotic.distrib.amqp")

class AMQPItem(base.RemoteItem):
    pass

class AMQPModule(base.RemoteModule):
    pass

class AMQPNeighbor(base.Neighbor):
    def __init__(self, host):
        self.host = host
        self.modules = []
        self.items = []

class AMQPTransportMethod(base.TransportMethod):
    NEIGHBOR_CLASS = AMQPNeighbor
    MODULE_CLASS = AMQPModule
    ITEM_CLASS = AMQPItem

    def __init__(self, hostname, config):
        self.hostname = hostname

        config = config or {}

        self.amqp_host = config.get("host")
        self.amqp_port = config.get("port")
        self.amqp_vhost = config.get("vhost")

        self.incoming = asyncio.Queue()
        self.neighbor_dict = {}

        if not self.amqp_host:
            log.warn("No AMQP host specified. Using 'localhost' instead.")

        self.credentials = None
        auth = config.get("auth")
        if auth:
            auth_type = auth.get("type", "basic")

            if auth_type == "basic":
                user = config.get("user")
                password = config.get("password")

                if user and password:
                    self.credentials = pika.credentials.PlainCredentials(user, password)
            else:
                log.warn("Unknown AMQP auth type '{}'".format(auth_type))

    def connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.amqp_host, self.amqp_port, self.amqp_vhost, self.credentials))
        self.channel = self.connection.channel()

        # For discovering other instances
        self.channel.exchange_declare(exchange='discovery',
                                      type='fanout')
        # Events go here
        self.channel.exchange_declare(exchange='events',
                                      type='fanout')
        # Messages to me go here!
        self.channel.exchange_declare(exchange='instance',
                                      type='direct')

        self.discovery_queue = self.channel.queue_declare()
        self.channel.queue_bind(exchange='discovery',
                                queue=self.discovery_queue.method.queue)

        self.events_queue = self.channel.queue_declare()
        self.channel.queue_bind(exchange='events',
                                queue=self.events_queue.method.queue)

        self.my_queue = self.channel.queue_declare(queue='test')
        #self.channel.queue_bind(exchange='instance',
        #                        queue=self.my_queue.method.queue,
        #                        routing_key=self.hostname)

        self.channel.basic_consume(self._discovery_callback,
                                   queue=self.discovery_queue.method.queue)
        self.channel.basic_consume(self._event_callback,
                                   queue=self.events_queue.method.queue)
        self.channel.basic_consume(self._instance_callback,
                                   queue=self.my_queue.method.queue)

        print("Sending announce")
        self.channel.basic_publish(exchange='',
                                   body=json.dumps({
                                       'type': 'announce',
                                       'host': self.hostname
                                   }).encode('UTF-8'),
                                   routing_key='discovery')

    def disconnect(self):
        self.connection.close()

    def send(self, event, targets=True):
        self.channel.basic_publish(exchange='events',
                                   routing_key='idiotic_events',
                                   body=event)

    def _discovery_callback(self, ch, method, properties, body):
        print(ch, method, properties, body)
        dec = json.loads(body.decode('UTF-8'))
        if dec['type'] == "announce":
            self.neighbor_dict[dec['host']] = AMQPNeighbor(dec['host'])
            print("Received announce")
            self.channel.basic_publish(exchange='instance',
                                       body=json.encode({
                                           'type': 'announce_response',
                                           'host': self.hostname
                                       }).encode('UTF-8'),
                                       routing_key=dec['ost'])
        elif dec['type'] == "announce_response":
            print("Received announce response")
            self.neighbor_dict[dec['host']] = AMQPNeighbor(dec['host'])

    def _event_callback(self, ch, method, properties, body):
        print(ch, method, properties, body)
        self.incoming.put(str(body))

    def _instance_callback(self, ch, method, properties, body):
        print(ch, method, properties, body)
        dec = json.decode(body.decode('UTF-8'))
        print('from instance')

    def neighbors(self):
        return list(self.neighbor_dict.keys())

    def receive(self):
        print("Receiving!")
        self.channel.start_consuming()
