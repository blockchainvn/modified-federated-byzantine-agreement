from ..common import log

class BaseServer:
    name = None
    transport_class = None
    transport = None

    def __init__(self, name, transport):
        self.name = name
        self.transport = transport

    def __str__(self):
        return '<Server: name=%(name)s>' % self.__dict__

    def start(self):
        log.server.debug('%s: trying to start server', self.name)

        self.transport.start(
            message_received_callback=self.message_receive,
        )

        log.server.debug('%s: server started', self.name)

        return

    def message_receive(self, data_list):
        log.server.debug('%s: received: %s', self.name, data_list)