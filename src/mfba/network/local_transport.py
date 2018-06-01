import asyncio
from socket import socketpair

from ..common import (
    log,
)

from .endpoint import Endpoint
from .base_transport import BaseTransport


LOCAL_TRANSPORT_LIST = dict(
)

class LocalTransportProtocol(asyncio.Protocol):
    transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        raise NotImplementedError()

    def connection_lost(self, exc):
        pass
        
class LocalTransport(BaseTransport):
    loop = None
    rsock = None
    wsock = None
    protocol = None

    buf = None
    data_delimeter = list('\r\n\r\n')

    def __init__(self, name, endpoint, loop):
        super(LocalTransport, self).__init__(name, endpoint)

        self.loop = loop
        self.buf = list()
        LOCAL_TRANSPORT_LIST[self.endpoint.uri] = self

    def start(self, *a, **kw):
        super(LocalTransport, self).start(*a, **kw)

        self.rsock, self.wsock = socketpair()

        conn = self.loop.create_connection(LocalTransportProtocol, sock=self.rsock)
        _, self.protocol = self.loop.run_until_complete(conn)
        self.protocol.data_received = self.data_receive

        return

    def data_receive(self, data):
        self.receive(data.decode())

        return

    def receive(self, data):
        log.transport.debug('%s: received: %s', self.name, data.encode())

        if '\r\n\r\n' not in data:
            self.buf.append(data)

            return

        messages = list()
        cr = list()
        sl = self.buf
        self.buf = list()
        for s in data:
            if s == self.data_delimeter[len(cr)]:
                cr.append(s)

                if self.data_delimeter == cr:
                    messages.append(''.join(sl))
                    cr = list()
                    sl = list()

                continue

            if len(cr) > 0 and s != self.data_delimeter[len(cr)]:
                s = ''.join(cr) + s
                cr = list()

            sl.append(s)

        if len(sl) > 0:
            self.buf.extend(sl)

        self.message_received_callback(messages)

        return

    def write(self, data):
        log.transport.debug('%s: wrote: %s', self.name, data.encode())

        return self.wsock.send(data.encode())

    def send(self, endpoint, data):
        assert isinstance(endpoint, Endpoint)

        log.transport.debug('%s: send: %s', self.name, data.strip().encode())

        LOCAL_TRANSPORT_LIST[endpoint.uri].write(data)

        return