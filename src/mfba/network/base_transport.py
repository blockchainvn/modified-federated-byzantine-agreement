from .endpoint import Endpoint

class BaseTransport:
    name = None
    endpoint = None
    message_received_callback = None

    def __init__(self, name, endpoint):
        self.name = name
        self.endpoint = Endpoint.from_uri(endpoint)

    def receive(self, data):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def send(self, data):
        raise NotImplementedError()

    def start(self, message_received_callback):
        self.message_received_callback = message_received_callback

        return