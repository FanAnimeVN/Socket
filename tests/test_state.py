"""
tests/test_state.py - Kiểm tra dữ liệu dùng chung trong state.py: người online, kết nối chat, unread, trạng thái.
Mỗi test tự đưa kho dữ liệu về trạng thái sạch (vì kho là biến toàn cục của module).
"""
import socket
import threading
import unittest

import state


def reset_state():
    state._peers.clear()
    state._connections.clear()
    state._unread.clear()
    state._history.clear()
    state._partner = None


class PeersTest(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_update_reports_new_status_same(self):
        self.assertEqual(state.update_peer("Minh", "1.2.3.4", 6000, "online"), "new")
        self.assertEqual(state.update_peer("Minh", "1.2.3.4", 6000, "online"), "same")
        self.assertEqual(state.update_peer("Minh", "1.2.3.4", 6000, "away"), "status")

    def test_expired_peers_are_removed(self):
        state.update_peer("Minh", "1.2.3.4", 6000, "online")
        state.update_peer("Lan", "1.2.3.5", 6001, "online")
        state._peers["Minh"]["last_seen"] -= 11          # Minh im lặng 11 giây
        self.assertEqual(state.remove_expired_peers(10), ["Minh"])
        self.assertIsNone(state.get_peer("Minh"))
        self.assertIsNotNone(state.get_peer("Lan"))

    def test_sorted_by_name(self):
        for name in ["Minh", "huy", "Lan"]:
            state.update_peer(name, "1.1.1.1", 5000, "online")
        self.assertEqual([n for n, _ in state.get_peers_sorted()], ["huy", "Lan", "Minh"])

    def test_returned_copies_do_not_change_the_store(self):
        state.update_peer("Minh", "1.2.3.4", 6000, "online")
        state.get_peer("Minh")["status"] = "hacked"
        self.assertEqual(state.get_peer("Minh")["status"], "online")


class ChatsTest(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.sock_a, self.sock_b = socket.socketpair()

    def tearDown(self):
        self.sock_a.close()
        self.sock_b.close()

    def test_unread_counts_only_for_non_partner(self):
        state.set_partner("Minh")
        self.assertEqual(state.record_incoming("Minh", "[Minh] hi"), (True, 0))
        self.assertEqual(state.record_incoming("Huy", "[Huy] a"), (False, 1))
        self.assertEqual(state.record_incoming("Huy", "[Huy] b"), (False, 2))
        self.assertEqual(state.unread_count("Huy"), 2)
        self.assertEqual(state.take_unread("Huy"), 2)
        self.assertEqual(state.unread_count("Huy"), 0)
        self.assertEqual(state.history_tail("Huy", 2), ["[Huy] a", "[Huy] b"])
        self.assertEqual(state.history_tail("Huy", 0), [])

    def test_new_connection_replaces_old_and_old_cleanup_is_silent(self):
        self.assertIsNone(state.add_connection("Minh", self.sock_a))
        self.assertIs(state.add_connection("Minh", self.sock_b), self.sock_a)           # trả về socket cũ để đóng
        self.assertEqual(state.remove_connection("Minh", self.sock_a), (False, False))  # cũ: đã bị thay -> im lặng
        self.assertIs(state.get_connection("Minh"), self.sock_b)

    def test_remove_connection_resets_partner(self):
        state.add_connection("Minh", self.sock_a)
        state.set_partner("Minh")
        self.assertEqual(state.remove_connection("Minh", self.sock_a), (True, True))
        self.assertIsNone(state.get_partner())
        self.assertIsNone(state.get_connection("Minh"))

    def test_pop_all_connections_empties_everything(self):
        state.add_connection("Minh", self.sock_a)
        state.add_connection("Lan", self.sock_b)
        state.set_partner("Minh")
        self.assertEqual({name for name, _ in state.pop_all_connections()}, {"Minh", "Lan"})
        self.assertIsNone(state.get_connection("Minh"))
        self.assertIsNone(state.get_partner())

    def test_many_threads_counting_unread_do_not_lose_updates(self):
        def worker():
            for _ in range(500):
                state.record_incoming("Huy", "x")
        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(state.unread_count("Huy"), 4000)       # có lock thì không mất lần đếm nào


class MyInfoTest(unittest.TestCase):
    def test_status_validation(self):
        self.assertTrue(state.set_status("away"))
        self.assertEqual(state.get_status(), "away")
        self.assertFalse(state.set_status("busy"))
        self.assertEqual(state.get_status(), "away")             # giá trị sai không làm đổi gì
        state.set_status("online")

    def test_identity(self):
        state.set_identity("Quan", 5000)
        self.assertEqual((state.get_name(), state.get_tcp_port()), ("Quan", 5000))


if __name__ == "__main__":
    unittest.main()
