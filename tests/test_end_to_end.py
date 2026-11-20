"""
tests/test_end_to_end.py - CHẠY CHƯƠNG TRÌNH THẬT: 3 instance lanchat.py trên một máy, UDP + TCP thật.

Test này làm đúng những việc trong kịch bản demo: thấy nhau online, chat hai chiều, tin của người thứ ba
thành "unread", gửi file (so mã hash), lệnh sai, đối phương /leave, đối phương bị tắt đột ngột, trùng tên.
Mỗi instance chạy ở chế độ "thường" (đọc dòng từ pipe) nên ta "gõ" bằng cách ghi vào stdin của nó.

Tên instance bắt đầu bằng "Test" để dễ nhận ra. Test thử broadcast qua 127.255.255.255 (chỉ trong máy) trước;
không được thì thử 255.255.255.255 (gói này có thể lọt ra mạng LAN thật). Cả hai đều không được -> test bị bỏ qua (skip).
Đặt biến môi trường SKIP_NETWORK_TESTS=1 để bỏ qua test này.
"""
import hashlib
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROADCAST_CANDIDATES = ["127.255.255.255", "255.255.255.255"]


def free_port():
    """Xin hệ điều hành một cổng TCP đang rảnh."""
    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


class Instance:
    """Một chương trình lanchat.py đang chạy; đọc stdout ở thread riêng, "gõ" bằng stdin."""

    def __init__(self, name, bcast, port=None):
        self.name = name
        self.port = port or free_port()
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        command = [sys.executable, "-u", "lanchat.py", "--name", name, "--port", str(self.port), "--bcast", bcast]
        self.proc = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        self.lines = []
        threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self):
        for line in self.proc.stdout:
            self.lines.append(line.rstrip("\r\n"))

    def say(self, text):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def mark(self):
        """Vị trí hiện tại trong đầu ra, để sau đó chỉ tìm các dòng MỚI."""
        return len(self.lines)

    def wait_for(self, text, since=0, timeout=15):
        """Chờ tới khi có dòng chứa `text` (sau vị trí `since`). Trả về dòng đó hoặc None nếu hết giờ."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for line in self.lines[since:]:
                if text in line:
                    return line
            time.sleep(0.1)
        return None

    def has(self, text, since=0):
        return any(text in line for line in self.lines[since:])

    def dump(self):
        return "\n".join(self.lines)

    def stop(self):
        if self.proc.poll() is None:
            try:
                self.say("/quit")
                self.proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                self.proc.kill()
        self.proc.wait()
        for pipe in (self.proc.stdin, self.proc.stdout):       # đóng pipe để không còn cảnh báo "unclosed file"
            try:
                pipe.close()
            except OSError:
                pass


@unittest.skipIf(os.environ.get("SKIP_NETWORK_TESTS") == "1", "SKIP_NETWORK_TESTS=1")
class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instances = []
        for bcast in BROADCAST_CANDIDATES:
            cls.a, cls.b, cls.c = (Instance(name, bcast) for name in ("TestA", "TestB", "TestC"))
            cls.instances = [cls.a, cls.b, cls.c]
            if cls.a.wait_for("TestB is online", timeout=14) and cls.a.wait_for("TestC is online", timeout=5):
                cls.bcast = bcast
                return
            for instance in cls.instances:
                instance.stop()
        raise unittest.SkipTest("UDP broadcast does not reach other instances on this machine (firewall?)")

    @classmethod
    def tearDownClass(cls):
        for instance in cls.instances:
            instance.stop()
        folder = os.environ.get("SAVE_EVIDENCE_TO")      # lưu "đầu ra màn hình" của từng instance làm minh chứng
        if folder:
            os.makedirs(folder, exist_ok=True)
            for instance in cls.instances:
                with open(os.path.join(folder, f"session_{instance.name}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"MINH CHUNG: man hinh cua {instance.name} trong test dau-cuoi (tests/test_end_to_end.py)\n\n")
                    f.write(instance.dump() + "\n")

    def test_full_scenario(self):
        a, b, c = self.a, self.b, self.c

        # ---- /list ----
        mark = a.mark()
        a.say("/list")
        self.assertTrue(a.wait_for("1. TestB", mark), a.dump())
        self.assertTrue(a.wait_for("2. TestC", mark), a.dump())

        # ---- A mở chat với B, gửi tin có tiếng Việt và ký tự '|' ----
        a.say("/chat TestB")
        self.assertTrue(a.wait_for("Connected to TestB"), a.dump())
        mark_b = b.mark()
        a.say("xin chào | ok")
        self.assertTrue(a.wait_for("[TestA] xin chào | ok"), a.dump())
        self.assertTrue(b.wait_for("New message from TestA (1 unread)", mark_b), b.dump())

        # ---- B mở chat với A: thấy tin chưa đọc, rồi trả lời ----
        mark_b = b.mark()
        b.say("/chat TestA")
        self.assertTrue(b.wait_for("Switched to TestA", mark_b), b.dump())
        self.assertTrue(b.wait_for("[TestA] xin chào | ok", mark_b), b.dump())
        mark_a = a.mark()
        b.say("ok nhé")
        self.assertTrue(a.wait_for("[TestB] ok nhé", mark_a), a.dump())

        # ---- C nhắn cho A (A đang chat với B): chỉ báo unread, không hiện nội dung ----
        c.say("/chat TestA")
        self.assertTrue(c.wait_for("Connected to TestA"), c.dump())
        mark_a = a.mark()
        c.say("hi from C")
        self.assertTrue(a.wait_for("New message from TestC (1 unread)", mark_a), a.dump())
        self.assertFalse(a.has("[TestC] hi from C", mark_a), "the message must not be shown while chatting with B")
        mark_a = a.mark()
        a.say("/list")
        self.assertTrue(a.wait_for("[1 unread]", mark_a), a.dump())
        mark_a = a.mark()
        a.say("/chat TestC")
        self.assertTrue(a.wait_for("[TestC] hi from C", mark_a), a.dump())
        a.say("/chat TestB")                                    # quay lại chat với B
        self.assertTrue(a.wait_for("Switched to TestB", mark_a), a.dump())

        # ---- /status away được UDP đưa tới người khác ----
        mark_b = b.mark()
        a.say("/status away")
        self.assertTrue(b.wait_for("TestA is now away", mark_b, timeout=8), b.dump())

        # ---- gửi file 3 MB trong lúc vẫn chat, rồi so mã hash ----
        content = os.urandom(3 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bao cao test.bin")      # tên có dấu cách
            with open(path, "wb") as f:
                f.write(content)
            mark_a, mark_b = a.mark(), b.mark()
            a.say(f'/send "{path}"')
            a.say("chat during transfer")
            self.assertTrue(b.wait_for("[TestA] chat during transfer", mark_b), b.dump())
            self.assertTrue(a.wait_for("100%  Done.", mark_a, timeout=20), a.dump())
            line = b.wait_for("Received", mark_b, timeout=20)
            self.assertTrue(line, b.dump())
            saved = re.search(r"Received (.+?) \(", line).group(1)
        received_path = os.path.join(ROOT, "downloads", saved)
        try:
            with open(received_path, "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), hashlib.sha256(content).hexdigest())
        finally:
            if os.path.exists(received_path):
                os.remove(received_path)

        # ---- lỗi: người không tồn tại, file không tồn tại, lệnh sai, chat với chính mình ----
        mark_a = a.mark()
        a.say("/chat Nobody")
        self.assertTrue(a.wait_for("No online user 'Nobody'", mark_a), a.dump())
        a.say("/send no_such_file.xyz")
        self.assertTrue(a.wait_for("File not found", mark_a), a.dump())
        a.say("/foo")
        self.assertTrue(a.wait_for("Unknown command: /foo", mark_a), a.dump())
        self.assertTrue(a.wait_for("/quit", mark_a), "a short help must follow an unknown command")
        a.say("/chat TestA")
        self.assertTrue(a.wait_for("cannot chat with yourself", mark_a), a.dump())

        # ---- B bấm /leave: A (đang chat với B) được báo ----
        mark_a = a.mark()
        b.say("/leave")
        self.assertTrue(a.wait_for("TestB left the chat", mark_a), a.dump())

        # ---- C bị tắt đột ngột: báo mất kết nối ngay, và "went offline" sau ~10 s ----
        mark_a = a.mark()
        c.proc.kill()
        self.assertTrue(a.wait_for("TestC disconnected", mark_a), a.dump())
        a.say("/chat TestC")                                    # C chưa hết hạn 10 s trong danh sách nhưng đã chết: connect bị từ chối
        self.assertTrue(a.wait_for("Cannot connect to TestC", mark_a, timeout=8), a.dump())
        self.assertTrue(a.wait_for("TestC went offline", mark_a, timeout=16), a.dump())

        # ---- chương trình không crash sau tất cả những chuyện trên ----
        self.assertIsNone(a.proc.poll())
        self.assertIsNone(b.proc.poll())

    def test_same_tcp_port_is_refused(self):
        """Trên Windows, nếu chỉ dùng SO_REUSEADDR thì chương trình thứ hai sẽ cùng nghe một cổng mà không báo lỗi."""
        twin = Instance("TestP", self.bcast, port=self.a.port)
        try:
            self.assertEqual(twin.proc.wait(timeout=15), 1)
            self.assertTrue(twin.has("Cannot use TCP port"), twin.dump())
        finally:
            twin.stop()

    def test_duplicate_name_is_refused(self):
        twin = Instance("TestA", self.bcast)
        try:
            self.assertEqual(twin.proc.wait(timeout=15), 1)
            self.assertTrue(twin.has("already used"), twin.dump())
        finally:
            twin.stop()


if __name__ == "__main__":
    unittest.main()
