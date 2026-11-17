"""
tests/test_protocol.py - Tự kiểm tra protocol.py MÀ KHÔNG cần mạng thật.

Người viết: HUY (khi làm protocol.py)        Người đọc hiểu + bổ sung thêm 1 test: PHONG

Chạy (từ thư mục gốc của dự án):   python -m unittest -v tests.test_protocol

KỸ THUẬT: socket.socketpair() tạo sẵn HAI socket đã nối với nhau trong cùng một chương trình.
          Gửi bằng a, đọc bằng b -> kiểm tra framing mà không cần server/port/firewall.
Lưu ý: nếu protocol.py của bạn dùng tên hàm khác, sửa lại test cho khớp.

Mỗi test dưới đây đang ở trạng thái "skip". Khi viết xong hàm tương ứng, XÓA dòng self.skipTest(...)
và viết thân test. Một test viết xong phải CHẠY ĐƯỢC và THẤT BẠI nếu bạn cố ý làm hỏng protocol.py
(thử phá thử để chắc test có tác dụng).
"""
import socket
import unittest

import protocol


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        # a gửi, b nhận
        self.a, self.b = socket.socketpair()

    def tearDown(self):
        self.a.close()
        self.b.close()

    def shortDescription(self):
        # Chỉ in tên test (không in dòng đầu docstring) để console Windows không làm méo tiếng Việt.
        return None

    def test_recv_exact_waits_for_all_bytes(self):
        """Gửi 10 byte làm 2 lần (5 + 5) cách nhau một chút; recv_exact(b, 10) phải trả về đủ 10 byte.
        Gợi ý: dùng threading.Timer hoặc một thread nhỏ để gửi lần 2 sau 0.2 giây."""
        self.skipTest("TODO")

    def test_recv_exact_raises_when_peer_closes(self):
        """Gửi 3 byte rồi đóng a; recv_exact(b, 10) phải ném ConnectionError (không treo, không trả thiếu)."""
        self.skipTest("TODO")

    def test_msg_roundtrip_ascii(self):
        """send_msg(a, "hello") -> read_frame(b) == ("MSG", "hello")  (hoặc dạng bạn đã chọn)."""
        self.skipTest("TODO")

    def test_msg_roundtrip_vietnamese(self):
        """Tin có dấu: "Xin chào, tôi tên Huy". Quan trọng nhất: length trong header phải là số BYTE.
        Kiểm tra thêm: tin chứa ký tự '|' và tin rỗng vẫn đi đúng."""
        self.skipTest("TODO")

    def test_two_messages_back_to_back(self):
        """Gửi 2 tin liền nhau rồi mới đọc: read_frame phải tách đúng từng tin (đây là bằng chứng framing hoạt động)."""
        self.skipTest("TODO")

    def test_hi_and_bye(self):
        """send_hi / send_bye -> read_frame cho ra ("HI", name) / ("BYE",)."""
        self.skipTest("TODO")

    def test_file_header(self):
        """send_file_header(a, "a b.txt", 123) -> read_frame(b) == ("FILE", "a b.txt", 123), phần byte file chưa bị đọc."""
        self.skipTest("TODO")

    def test_garbage_header_raises_valueerror(self):
        """Gửi dữ liệu rác (không có '|' hoặc length không phải số): read_frame phải ném ValueError."""
        self.skipTest("TODO")


if __name__ == "__main__":
    unittest.main()
