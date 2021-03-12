import unittest
import signal
import socket
import subprocess
import tempfile
import time

import psutil

try:
    socket.socket().bind(('127.0.0.1', 7656))
    i2p_port_free = True
except (OSError, socket.error):
    i2p_port_free = False


class TestProcessProto(unittest.TestCase):
    """Test process attributes, common flow"""
    _process_cmd = ['minode']
    _connection_limit = 16
    _listen = None
    _listening_port = None

    home = None

    @classmethod
    def setUpClass(cls):
        if not cls.home:
            cls.home = tempfile.gettempdir()
        cmd = cls._process_cmd + [
            '--data-dir', cls.home,
            '--connection-limit', str(cls._connection_limit)
        ]
        if cls._listen is True:
            if cls._listening_port:
                cmd += ['-p', cls._listening_port]
        elif cls._listen is False:
            cmd += ['--no-incoming']
        cls.process = psutil.Popen(cmd, stderr=subprocess.STDOUT)  # nosec

    @classmethod
    def _stop_process(cls, timeout=5):
        cls.process.send_signal(signal.SIGTERM)
        try:
            cls.process.wait(timeout)
        except psutil.TimeoutExpired:
            return False
        return True

    @classmethod
    def tearDownClass(cls):
        """Ensures that pybitmessage stopped and removes files"""
        try:
            if not cls._stop_process(10):
                try:
                    cls.process.kill()
                except psutil.NoSuchProcess:
                    pass
        except psutil.NoSuchProcess:
            pass


class TestProcessShutdown(TestProcessProto):
    """Separate test case for SIGTERM"""
    def test_shutdown(self):
        """Send to minode SIGTERM and ensure it stopped"""
        # longer wait time because it's not a benchmark
        self.assertTrue(
            self._stop_process(20),
            '%s has not stopped in 20 sec' % ' '.join(self._process_cmd))


class TestProcess(TestProcessProto):
    """The test case for minode process"""
    _wait_time = 20

    def test_connections(self):
        """Check minode process connections"""
        _started = time.time()
        connections = []
        for t in range(self._wait_time * 2):
            connections = self.process.connections()
            if len(connections) > self._connection_limit / 2:
                _time_to_connect = round(time.time() - _started)
                break
            time.sleep(0.5)
        else:
            self.fail(
                'Failed establish at least %s connections in %s sec'
                % (self._connection_limit / 2, self._wait_time))
        for t in range(_time_to_connect * 2):
            self.assertLessEqual(
                len(connections),
                # shared.outgoing_connections, one listening
                8 if self._listen is False else self._connection_limit + 1,
                'Opened more connections than required by --connection-limit')
            time.sleep(0.5)
        for c in connections:
            if c.status == 'LISTEN':
                if self._listen is False:
                    return self.fail(
                        'Listening while started with --no-incoming')
                self.assertEqual(c.laddr[1], self._listening_port or 8444)
                break


@unittest.skipIf(i2p_port_free, 'no running i2pd detected')
class TestProcessI2P(TestProcess):
    """Test minode process with --i2p and no IP"""
    _process_cmd = ['minode', '--i2p', '--no-ip']
    _connection_limit = 4
    _wait_time = 120
    _listening_port = 8448
