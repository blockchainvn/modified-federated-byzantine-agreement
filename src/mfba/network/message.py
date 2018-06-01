import time
import hashlib
import uuid
import json


CLOCK_SEQ = int(time.time() * 1000000)


class Message:
    class InvalidMessageError(Exception):
        pass

    message_id = None
    hash_id = None
    data = None

    def __init__(self, node, message_id, hash_id, data):
        assert isinstance(data, str)
        assert message_id is not None
        assert hash_id == hashlib.sha1(data.encode()).hexdigest()

        self.node = node
        self.message_id = message_id
        self.hash_id = hash_id
        self.data = data

    def __repr__(self):
        d = self.__dict__.copy()
        d['data'] = d['data'] if len(d['data']) < 10 else (d['data'][:10] + '...')
        return '<Message: node=%(node)s message_id=%(message_id)s data=%(data)s>' % d

    def __eq__(self, message):
        if not isinstance(message, Message):
            return False

        if message.message_id != self.message_id:
            return False

        if message.hash_id != self.hash_id:
            return False

        if message.data != self.data:
            return False

        return True

    def copy(self):
        return self.__class__(
            self.node,
            self.message_id,
            self.hash_id,
            self.data,
        )

    def to_dict(self):
        return dict(
            message=self.to_message_dict(),
        )

    def to_message_dict(self):
        return dict(
            hash_id=self.hash_id,
            message_id=self.message_id,
            data=self.data,
        )

    def serialize(self, node):
        d = self.to_dict()
        d['node'] = node.name
        d['type_name'] = 'message'
        return json.dumps(d) + '\r\n\r\n'

    @classmethod
    def new(cls, data):
        assert isinstance(data, str)

        return cls(
            None,
            uuid.uuid1(clock_seq=CLOCK_SEQ).hex,
            hashlib.sha1(data.encode()).hexdigest(),
            data,
        )

    @classmethod
    def from_json(cls, data):
        try:
            o = json.loads(data)
        except json.decoder.JSONDecodeError as e:
            raise cls.InvalidMessageError(e)

        if 'type_name' not in o or o['type_name'] != 'message':
            raise cls.InvalidMessageError('`type_name` is not "message"')

        try:
            m = o['message']
            return cls(o['node'], m['message_id'], m['hash_id'], m['data'])
        except KeyError as e:
            raise cls.InvalidMessageError(e)

    @classmethod
    def from_dict(cls, o):
        m = o['message']
        return cls(o['node'], m['message_id'], m['hash_id'], m['data'])

    def get_message(self):
        return self