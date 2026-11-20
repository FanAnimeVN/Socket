"""
tests/test_protocol.py - Tự kiểm tra protocol.py MÀ KHÔNG cần mạng thật.

Chạy (từ thư mục gốc):   python -m unittest discover -s tests -t . -v

KỸ THUẬT: socket.socketpair() tạo sẵn HAI socket đã nối với nhau trong cùng một chương trình.
          Gửi bằng a, đọc bằng b -> kiểm tra framing mà không cần server/cổng/firewall.
"""
import socket
import threading
import unittest

import protocol


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.a, self.b = socket.socketpair()      # a gửi, b nhận
        self.b.settimeout(5)                      # lỡ có lỗi thì test báo lỗi chứ không treo

    def tearDown(self):
        self.a.close()
        self.b.close()

    def test_recv_exact_waits_for_all_bytes(self):
        """Gửi 10 byte làm 2 lần (5 + 5) cách nhau một chút; recv_exact phải trả về đủ 10 byte."""
        self.a.sendall(b"12345")
        timer = threading.Timer(0.2, lambda: self.a.sendall(b"67890"))
        timer.start()
        self.assertEqual(protocol.recv_exact(self.b, 10), b"1234567890")
        timer.join()

    def test_recv_exact_raises_when_peer_closes(self):
        """Gửi 3 byte rồi đóng; recv_exact(10) phải ném ConnectionError (không treo, không trả thiếu)."""
        self.a.sendall(b"abc")
        self.a.close()
        with self.assertRaises(ConnectionError):
            protocol.recv_exact(self.b, 10)

    def test_msg_roundtrip_ascii(self):
        protocol.send_msg(self.a, "hello")
        self.assertEqual(protocol.read_frame(self.b), ("MSG", "hello"))

    def test_msg_length_counts_bytes_not_characters(self):
        """Bẫy #1: "Việt" là 4 ký tự nhưng 6 byte. Header phải ghi 6."""
        protocol.send_msg(self.a, "Việt")
        self.assertEqual(self.b.recv(100), "MSG|6|Việt".encode("utf-8"))

    def test_msg_roundtrip_vietnamese_pipe_and_empty(self):
        for text in ["Xin chào, tôi tên Huy", "a|b|c", "", "dòng dài " * 500, "emoji 😀"]:
            protocol.send_msg(self.a, text)
            self.assertEqual(protocol.read_frame(self.b), ("MSG", text))

    def test_two_messages_back_to_back(self):
        """Gửi 2 tin liền nhau rồi mới đọc: read_frame phải tách đúng từng tin (bằng chứng framing hoạt động)."""
        protocol.send_msg(self.a, "một")
        protocol.send_msg(self.a, "hai")
        self.assertEqual(protocol.read_frame(self.b), ("MSG", "một"))
        self.assertEqual(protocol.read_frame(self.b), ("MSG", "hai"))

    def test_hi_and_bye(self):
        protocol.send_hi(self.a, "Quan", protocol.KIND_CHAT)
        protocol.send_bye(self.a)
        self.assertEqual(protocol.read_frame(self.b), ("HI", "Quan", "chat"))
        self.assertEqual(protocol.read_frame(self.b), ("BYE",))

    def test_file_header_leaves_file_bytes_unread(self):
        protocol.send_file_header(self.a, "a b.txt", 5)
        self.a.sendall(b"DATA!")
        self.assertEqual(protocol.read_frame(self.b), ("FILE", "a b.txt", 5))
        self.assertEqual(protocol.recv_exact(self.b, 5), b"DATA!")      # byte của file vẫn còn nguyên

    def test_pipe_in_filename_is_replaced(self):
        protocol.send_file_header(self.a, "x|y.txt", 1)
        self.assertEqual(protocol.read_frame(self.b), ("FILE", "x_y.txt", 1))

    def test_garbage_raises_valueerror(self):
        for garbage in [b"XYZ|", b"MSG|abc|", b"MSG|-5|", b"HI||chat|", b"HI|Quan|other|", b"A" * 2000]:
            a, b = socket.socketpair()
            b.settimeout(5)
            a.sendall(garbage)
            with self.assertRaises(ValueError, msg=repr(garbage[:20])):
                protocol.read_frame(b)
            a.close()
            b.close()

    def test_message_too_long_is_rejected(self):
        self.a.sendall(b"MSG|99999999999|")
        with self.assertRaises(ValueError):
            protocol.read_frame(self.b)

    def test_peer_closed_raises_connectionerror(self):
        self.a.close()
        with self.assertRaises(ConnectionError):
            protocol.read_frame(self.b)


if __name__ == "__main__":
    unittest.main()
