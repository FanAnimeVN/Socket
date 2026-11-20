"""
tests/test_ui.py - Kiểm tra phần "gõ phím khi tin nhắn đang đến" (đề mục 4.3) mà không cần console thật.

Kỹ thuật: thay sys.stdout bằng StringIO để đọc lại những gì chương trình "vẽ", và đưa vào một hàm đọc phím giả
(trả về từng phím trong một danh sách) để mô phỏng người gõ.
Việc kiểm tra bằng console Windows THẬT (bơm phím thật) nằm ở tests/manual_console_check.py.
"""
import io
import sys
import threading
import unittest
from unittest import mock

import ui


class UiTestCase(unittest.TestCase):
    def setUp(self):
        self.out = io.StringIO()
        for patcher in (mock.patch.object(sys, "stdout", self.out), mock.patch.object(ui, "_interactive", True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        ui._buffer = ""


class ShowMessageTest(UiTestCase):
    def test_message_goes_above_input_and_typed_text_is_redrawn(self):
        for ch in "you can che":
            ui._type_char(ch)
        self.out.truncate(0)
        self.out.seek(0)
        ui.show_message("[Minh] ok, which part?")
        # 3 bước: xóa dòng nhập -> in tin + xuống dòng -> vẽ lại "> " + chữ đang gõ dở
        self.assertEqual(self.out.getvalue(), "\r\033[K[Minh] ok, which part?\n> you can che")
        self.assertEqual(ui._buffer, "you can che")

    def test_backspace_and_take_line(self):
        for ch in "abc":
            ui._type_char(ch)
        ui._backspace()
        self.assertEqual(ui._buffer, "ab")
        self.assertEqual(ui._take_line(), "ab")
        self.assertEqual(ui._buffer, "")
        ui._backspace()                                            # buffer rỗng: không lỗi
        self.assertEqual(ui._buffer, "")

    def test_many_threads_printing_do_not_interleave_lines(self):
        def worker(tag):
            for i in range(50):
                ui.show_message(f"[{tag}] line {i}")
        threads = [threading.Thread(target=worker, args=(t,)) for t in "ABCD"]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        text = self.out.getvalue().replace("\r\033[K", "").replace("> ", "")
        lines = [line for line in text.split("\n") if line]
        self.assertEqual(len(lines), 200)
        self.assertTrue(all(line.startswith("[") and "] line " in line for line in lines))   # không dòng nào bị cắt giữa chừng


class InputLoopTest(UiTestCase):
    def run_keys(self, keys, on_line):
        keys = iter(keys)
        ui.input_loop(on_line, key_reader=lambda: next(keys))

    def test_enter_sends_line_and_quit_stops(self):
        lines = []

        def on_line(line):
            lines.append(line)
            return line != "/quit"

        self.run_keys(list("xin chào") + ["\r"] + list("/quit") + ["\r"], on_line)
        self.assertEqual(lines, ["xin chào", "/quit"])

    def test_backspace_special_keys_and_vietnamese(self):
        lines = []
        keys = list("Việtt") + ["\b"] + [None, "\r", "\x03"]       # None = phím mũi tên (bỏ qua); Ctrl+C thoát
        self.run_keys(keys, lambda line: lines.append(line))
        self.assertEqual(lines, ["Việt"])

    def test_typed_text_survives_incoming_message_between_keys(self):
        lines = []
        calls = {"n": 0}
        keys = list("hello") + ["\r", "\x03"]

        def read_key():
            calls["n"] += 1
            if calls["n"] == 4:                                    # giữa lúc đang gõ, có tin đến
                ui.show_message("[Minh] hi")
            return keys[calls["n"] - 1]

        ui.input_loop(lambda line: lines.append(line), key_reader=read_key)
        self.assertEqual(lines, ["hello"])                         # chữ gõ dở không bị mất
        self.assertIn("[Minh] hi\n> hel", self.out.getvalue())     # tin chen vào, rồi dòng nhập được vẽ lại với "hel"


class PlainModeTest(unittest.TestCase):
    def test_plain_mode_reads_lines_and_prints_without_ansi(self):
        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out), mock.patch.object(ui, "_interactive", False), \
                mock.patch.object(sys, "stdin", io.StringIO("one\n/quit\nnever\n")):
            lines = []
            ui.input_loop(lambda line: lines.append(line) or line != "/quit")
            ui.show_message("hello")
        self.assertEqual(lines, ["one", "/quit"])
        self.assertEqual(out.getvalue(), "hello\n")                # không có mã ANSI, không có dấu nhắc


if __name__ == "__main__":
    unittest.main()
