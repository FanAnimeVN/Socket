"""
tests/test_filetransfer.py - Kiểm tra filetransfer.py: tên file an toàn, không ghi đè, tiến độ %, nhận file (đủ / đứt giữa chừng).
"""
import os
import socket
import tempfile
import unittest
from unittest import mock

import config
import filetransfer


class SafeFilenameTest(unittest.TestCase):
    def test_path_tricks_are_removed(self):
        self.assertEqual(filetransfer._safe_filename("..\\..\\evil.exe"), "evil.exe")
        self.assertEqual(filetransfer._safe_filename("../../etc/passwd"), "passwd")
        self.assertEqual(filetransfer._safe_filename("a/b/c.txt"), "c.txt")
        self.assertEqual(filetransfer._safe_filename("C:\\Windows\\x.dll"), "x.dll")

    def test_bad_characters_and_empty_names(self):
        self.assertEqual(filetransfer._safe_filename("a<b>c?.txt"), "a_b_c_.txt")
        for empty in ["", "..", "..."]:
            self.assertEqual(filetransfer._safe_filename(empty), "received_file")
        self.assertEqual(filetransfer._safe_filename("CON.txt"), "_CON.txt")

    def test_vietnamese_name_is_kept(self):
        self.assertEqual(filetransfer._safe_filename("báo cáo.pdf"), "báo cáo.pdf")

    def test_long_name_keeps_extension(self):
        name = filetransfer._safe_filename("a" * 400 + ".pdf")
        self.assertTrue(name.endswith(".pdf"))
        self.assertLessEqual(len(name), 150)


class DownloadFolderTestCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(config, "DOWNLOAD_DIR", self.folder.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.folder.cleanup)
        messages = mock.patch("ui.show_message")                 # không in ra màn hình thật; lưu lại để kiểm tra
        self.messages = messages.start()
        self.addCleanup(messages.stop)


class OpenDownloadTest(DownloadFolderTestCase):
    def test_same_name_gets_a_number_instead_of_overwriting(self):
        names = []
        for _ in range(3):
            out, path = filetransfer._open_download("slides.pdf")
            out.close()
            names.append(os.path.basename(path))
        self.assertEqual(names, ["slides.pdf", "slides(1).pdf", "slides(2).pdf"])

    def test_file_cannot_escape_download_folder(self):
        out, path = filetransfer._open_download("..\\..\\evil.exe")
        out.close()
        self.assertEqual(os.path.dirname(path), self.folder.name)

    def test_delete_ignores_missing_file(self):
        out, path = filetransfer._open_download("x.bin")
        out.close()
        filetransfer._delete_file(path)
        self.assertFalse(os.path.exists(path))
        filetransfer._delete_file(path)                          # xóa lần nữa: không lỗi


class ReceiveFileTest(DownloadFolderTestCase):
    def setUp(self):
        super().setUp()
        self.sender, self.receiver = socket.socketpair()
        self.receiver.settimeout(5)
        self.addCleanup(self.receiver.close)

    def test_complete_file_is_saved(self):
        content = os.urandom(200 * 1024)                        # lớn hơn một khối 64 KB
        self.sender.sendall(content)
        self.sender.close()
        filetransfer.receive_file(self.receiver, "Minh", "data.bin", len(content))
        with open(os.path.join(self.folder.name, "data.bin"), "rb") as f:
            self.assertEqual(f.read(), content)

    def test_interrupted_file_is_deleted(self):
        self.sender.sendall(b"only half of the file")
        self.sender.close()                                      # người gửi đứt giữa chừng
        filetransfer.receive_file(self.receiver, "Minh", "data.bin", 1000)
        self.assertEqual(os.listdir(self.folder.name), [])       # file dở đã bị xóa
        shown = " ".join(str(call.args[0]) for call in self.messages.call_args_list)
        self.assertIn("Partial file deleted", shown)

    def test_zero_byte_file(self):
        self.sender.close()
        filetransfer.receive_file(self.receiver, "Minh", "empty.txt", 0)
        self.assertEqual(os.path.getsize(os.path.join(self.folder.name, "empty.txt")), 0)


class SendFileChecksTest(unittest.TestCase):
    """Các kiểm tra nhanh của /send xảy ra TRƯỚC khi tạo thread, nên báo lỗi tức thì."""

    def test_send_without_open_chat_reminds_the_user(self):
        with mock.patch("ui.show_message") as show:
            filetransfer.send_file_async(None, "whatever.txt")
        self.assertIn("No chat open", show.call_args.args[0])

    def test_send_missing_file_reports_not_found(self):
        with mock.patch("ui.show_message") as show:
            filetransfer.send_file_async("Minh", "no_such_file.xyz")
        self.assertIn("File not found", show.call_args.args[0])


class ProgressTest(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(filetransfer._percent(0, 0), 100)       # file 0 byte: không chia cho 0
        self.assertEqual(filetransfer._percent(50, 200), 25)
        self.assertEqual(filetransfer._percent(999, 1000), 99)

    def test_report_every_ten_percent(self):
        last, reported = 0, []
        for done in range(0, 1000, 37):                          # các bước nhỏ, lẻ
            percent = filetransfer._percent(done, 1000)
            if filetransfer._should_report(percent, last):
                last = percent
                reported.append(percent)
        self.assertTrue(all(b - a >= 10 for a, b in zip(reported, reported[1:])))
        self.assertLessEqual(len(reported), 10)                  # không bao giờ spam mỗi khối

    def test_format_size(self):
        self.assertEqual(filetransfer.format_size(0), "0 B")
        self.assertEqual(filetransfer.format_size(1023), "1023 B")
        self.assertEqual(filetransfer.format_size(1536), "1.5 KB")
        self.assertEqual(filetransfer.format_size(2516582), "2.4 MB")


if __name__ == "__main__":
    unittest.main()
