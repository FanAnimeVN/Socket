"""
tests/test_project_rules.py - Test KIỂM TRA CHÍNH CÁC LUẬT TỔ CHỨC của dự án (xem CLAUDE.md).

Nếu test này đỏ nghĩa là có file vi phạm luật: quá 300 dòng, thiếu chú thích đầu file, thêm file .py lạ ở thư mục gốc,
import sai hướng, hoặc báo cáo có chứa code. Sửa file đó (không sửa test để cho qua).
"""
import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", ".omc", ".claude", "__pycache__", "downloads", "samples"}
MAX_LINES = 300

# 8 file của chương trình (cấu trúc phẳng, mỗi file một việc) và những module mà mỗi file được phép import.
ALLOWED_IMPORTS = {
    "config.py": set(),
    "state.py": {"config"},
    "protocol.py": {"config"},
    "ui.py": set(),
    "discovery.py": {"config", "state", "ui"},
    "filetransfer.py": {"config", "protocol", "state", "ui"},
    "tcp_chat.py": {"config", "filetransfer", "protocol", "state", "ui"},
    "lanchat.py": {"config", "discovery", "filetransfer", "protocol", "state", "tcp_chat", "ui"},
}
PROJECT_MODULES = {name[:-3] for name in ALLOWED_IMPORTS}


def all_files(extensions):
    for folder, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            if name.endswith(extensions):
                yield os.path.join(folder, name)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def relative(path):
    return os.path.relpath(path, ROOT)


class ProjectRulesTest(unittest.TestCase):
    def test_no_file_over_300_lines(self):
        for path in all_files((".py", ".md")):
            count = read(path).count("\n") + 1
            self.assertLessEqual(count, MAX_LINES, msg=f"{relative(path)} has {count} lines")

    def test_only_the_eight_program_files_at_root(self):
        root_py = {name for name in os.listdir(ROOT) if name.endswith(".py")}
        self.assertEqual(root_py, set(ALLOWED_IMPORTS), msg="add new code inside an existing file or discuss first")

    def test_every_code_file_starts_with_a_docstring(self):
        for path in all_files(".py"):
            self.assertTrue(ast.get_docstring(ast.parse(read(path))), msg=f"{relative(path)} has no header docstring")

    def test_imports_follow_the_dependency_direction(self):
        for filename, allowed in ALLOWED_IMPORTS.items():
            found = set()
            for node in ast.walk(ast.parse(read(os.path.join(ROOT, filename)))):
                if isinstance(node, ast.Import):
                    found.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    found.add(node.module.split(".")[0])
            extra = (found & PROJECT_MODULES) - allowed
            self.assertEqual(extra, set(), msg=f"{filename} must not import {sorted(extra)}")

    def test_report_has_no_code_and_its_images_exist(self):
        report = os.path.join(ROOT, "docs", "BAO_CAO.md")
        if not os.path.exists(report):
            self.skipTest("report not written yet")
        text = read(report)
        self.assertNotIn("```", text, "the report must contain technical writing only, no code blocks")
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
            self.assertTrue(os.path.exists(os.path.join(ROOT, "docs", target)), msg=f"missing image: {target}")


if __name__ == "__main__":
    unittest.main()
