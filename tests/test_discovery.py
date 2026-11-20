"""
tests/test_discovery.py - Kiểm tra discovery.py: gói HELLO (ghép/đọc, gói rác), tìm người theo tên/số, in danh sách /list.
"""
import unittest

import discovery
import state
from tests.test_state import reset_state


class HelloTest(unittest.TestCase):
    def test_build_then_parse(self):
        packet = discovery.build_hello("Quan", 5000, "online")
        self.assertEqual(packet, b"HELLO|Quan|5000|online")
        self.assertEqual(discovery.parse_hello(packet), ("Quan", 5000, "online"))

    def test_vietnamese_name(self):
        packet = discovery.build_hello("Ngọc", 5002, "away")
        self.assertEqual(discovery.parse_hello(packet), ("Ngọc", 5002, "away"))

    def test_bad_packets_return_none(self):
        bad = [
            b"",                          # rỗng
            b"HELLO|Quan|5000",           # thiếu trường
            b"HELLO|Quan|5000|online|x",  # thừa trường
            b"HI|Quan|5000|online",       # sai loại
            b"HELLO||5000|online",        # tên rỗng
            b"HELLO|Quan|abc|online",     # cổng là chữ
            b"HELLO|Quan|0|online",       # cổng ngoài phạm vi
            b"HELLO|Quan|70000|online",   # cổng ngoài phạm vi
            b"HELLO|Quan|5000|busy",      # status lạ
            b"\xff\xfe\xfd",              # byte không phải utf-8
        ]
        for packet in bad:
            self.assertIsNone(discovery.parse_hello(packet), msg=repr(packet))


class PeerListTest(unittest.TestCase):
    def setUp(self):
        reset_state()
        for name in ["Minh", "Huy", "Lan"]:
            state.update_peer(name, "192.168.1.5", 5000, "online")

    def test_find_by_number_or_name(self):
        self.assertEqual(discovery.find_peer("1"), "Huy")
        self.assertEqual(discovery.find_peer("3"), "Minh")
        self.assertEqual(discovery.find_peer("minh"), "Minh")           # không phân biệt hoa/thường
        self.assertIsNone(discovery.find_peer("0"))
        self.assertIsNone(discovery.find_peer("4"))
        self.assertIsNone(discovery.find_peer("Nobody"))

    def test_list_format_matches_the_assignment_example(self):
        state.update_peer("Lan", "192.168.1.5", 5000, "away")
        lines = discovery.format_peer_list()
        self.assertEqual(lines[0], "  1. Huy   (192.168.1.5)  online")
        self.assertEqual(lines[1], "  2. Lan   (192.168.1.5)  away")

    def test_list_shows_unread_and_partner(self):
        state.record_incoming("Huy", "[Huy] hi")
        state.set_partner("Minh")
        lines = discovery.format_peer_list()
        self.assertTrue(lines[0].endswith("[1 unread]"))
        self.assertTrue(lines[2].endswith("<- chatting"))

    def test_empty_list_message(self):
        reset_state()
        self.assertEqual(discovery.format_peer_list(), ["[*] Nobody else is online yet."])


if __name__ == "__main__":
    unittest.main()
