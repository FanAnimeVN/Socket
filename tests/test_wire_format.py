"""
tests/test_wire_format.py - XEM TỪNG BYTE THẬT mà chương trình gửi ra mạng (UDP và TCP), bằng một "peer giả".

Peer giả là đoạn mã của test: tự phát HELLO để chương trình thật nghĩ có người online, và tự mở một cổng TCP.
Khi chương trình thật /chat tới peer giả, mọi byte nó gửi tới peer giả được đọc ra và so với giao thức (docs/PROTOCOL.md):
    HELLO|Wire|<cổng>|online          (UDP broadcast, bắt bằng một socket UDP thô)
    HI|Wire|chat|                      (frame đầu tiên của kết nối chat)
    MSG|9|Xin chào                     (tiếng Việt: 8 ký tự nhưng length = 9 BYTE)
    BYE|                               (/leave)
    HI|Wire|file|FILE|note.txt|11|hello world      (kết nối file riêng: header rồi tới byte của file)
Đặt biến môi trường SAVE_EVIDENCE_TO=<thư mục> để lưu bản ghi (dạng chữ + hex) làm minh chứng cho báo cáo.
Đặt SKIP_NETWORK_TESTS=1 để bỏ qua test này.
"""
import os
import socket
import tempfile
import threading
import time
import unittest

from tests.test_end_to_end import BROADCAST_CANDIDATES, Instance, free_port

HELLO_PORT = 9999


def read_idle(conn, idle_seconds=1.5):
    """Đọc mọi byte tới được; dừng khi `idle_seconds` giây không có thêm byte nào."""
    conn.settimeout(idle_seconds)
    data = b""
    try:
        while True:
            chunk = conn.recv(65536)
            if chunk == b"":
                break
            data += chunk
    except socket.timeout:
        pass
    return data


def describe(label, data):
    return [f"{label}", f"   text: {data!r}", f"   hex : {data.hex(' ')}", f"   size: {len(data)} bytes"]


@unittest.skipIf(os.environ.get("SKIP_NETWORK_TESTS") == "1", "SKIP_NETWORK_TESTS=1")
class WireFormatTest(unittest.TestCase):
    def test_bytes_on_the_wire(self):
        evidence = []
        fake_server = socket.socket()
        fake_server.bind(("127.0.0.1", 0))
        fake_server.listen()
        fake_port = fake_server.getsockname()[1]
        self.addCleanup(fake_server.close)

        # --- bắt gói UDP thô trên cổng 9999 ---
        capture = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        capture.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        capture.bind(("", HELLO_PORT))
        capture.settimeout(1)
        self.addCleanup(capture.close)

        wire = Instance("Wire", BROADCAST_CANDIDATES[0])
        self.addCleanup(wire.stop)
        self.assertTrue(wire.wait_for("Broadcasting presence", timeout=15), wire.dump())

        hello = None
        deadline = time.time() + 8
        while hello is None and time.time() < deadline:
            try:
                data, addr = capture.recvfrom(1024)
            except socket.timeout:
                continue
            if data.startswith(b"HELLO|Wire|"):
                hello = (data, addr)
        self.assertIsNotNone(hello, "no HELLO datagram from the program was captured")
        self.assertEqual(hello[0], f"HELLO|Wire|{wire.port}|online".encode())
        evidence += describe(f"[UDP] datagram captured on port 9999 (from {hello[1][0]}:{hello[1][1]})", hello[0])

        # --- peer giả tự giới thiệu bằng HELLO để chương trình thật thấy "Fake" online ---
        stop_announcing = threading.Event()

        def announce():
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not stop_announcing.is_set():
                sender.sendto(f"HELLO|Fake|{fake_port}|online".encode(), (BROADCAST_CANDIDATES[0], HELLO_PORT))
                stop_announcing.wait(1)
            sender.close()

        threading.Thread(target=announce, daemon=True).start()
        self.addCleanup(stop_announcing.set)
        self.assertTrue(wire.wait_for("Fake is online", timeout=10), wire.dump())

        # --- kết nối chat: HI rồi MSG (tiếng Việt) ---
        wire.say("/chat Fake")
        chat_conn, _ = fake_server.accept()
        self.addCleanup(chat_conn.close)
        self.assertEqual(read_idle(chat_conn), b"HI|Wire|chat|")
        evidence += describe("[TCP #1] first bytes after the 3-way handshake (A -> B)", b"HI|Wire|chat|")
        wire.say("Xin chào")
        sent = read_idle(chat_conn)
        self.assertEqual(sent, "MSG|9|Xin chào".encode("utf-8"))
        self.assertEqual((len("Xin chào"), len("Xin chào".encode("utf-8"))), (8, 9))
        evidence += describe("[TCP #1] chat message 'Xin chào' = 8 characters but 9 bytes (A -> B)", sent)
        chat_conn.sendall(b"MSG|2|ok")
        self.assertTrue(wire.wait_for("[Fake] ok"), wire.dump())
        evidence += describe("[TCP #1] reply from the fake peer (B -> A), program shows '[Fake] ok'", b"MSG|2|ok")
        wire.say("/leave")
        self.assertEqual(read_idle(chat_conn), b"BYE|")
        evidence += describe("[TCP #1] /leave (A -> B)", b"BYE|")

        # --- gửi file: kết nối TCP riêng ---
        wire.say("/chat Fake")
        second_chat, _ = fake_server.accept()
        self.addCleanup(second_chat.close)
        read_idle(second_chat)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "note.txt")
            with open(path, "wb") as f:
                f.write(b"hello world")
            wire.say(f"/send {path}")
            file_conn, _ = fake_server.accept()
            self.addCleanup(file_conn.close)
            file_bytes = read_idle(file_conn)
        self.assertEqual(file_bytes, b"HI|Wire|file|FILE|note.txt|11|hello world")
        evidence += describe("[TCP #3] separate file connection (A -> B): HI, FILE header, then the raw file bytes", file_bytes)

        folder = os.environ.get("SAVE_EVIDENCE_TO")
        if folder:
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "wire_format.txt"), "w", encoding="utf-8") as f:
                f.write("MINH CHUNG: byte THAT tren day (tests/test_wire_format.py)\n\n" + "\n".join(evidence) + "\n")


if __name__ == "__main__":
    unittest.main()
