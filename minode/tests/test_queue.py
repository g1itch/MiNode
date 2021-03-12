import zmq

from .test_process import TestProcessProto


class TestProcessQueue(TestProcessProto):
    _process_cmd = ['minode', '--msg-queue']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        context = zmq.Context()
        cls.socket = context.socket(zmq.SUB)
        cls.socket.connect('tcp://localhost:5556')
        cls.socket.setsockopt(zmq.RCVTIMEO, 300)
        cls.socket.setsockopt(zmq.SUBSCRIBE, b'obj')

    def test_receive_msg(self):
        """wait a couple of messages"""
        tag, data = self.socket.recv().split(b'\x00', 1)
        self.assertEqual(tag, b'obj')
