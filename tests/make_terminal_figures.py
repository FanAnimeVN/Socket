"""
tests/make_terminal_figures.py - Dựng "ảnh chụp màn hình console" (SVG) từ các file minh chứng THẬT trong docs/evidence/.

Nội dung các hình KHÔNG gõ tay: mỗi dòng đều được cắt ra từ file log do chương trình thật sinh ra. Muốn cập nhật hình
sau khi chạy lại minh chứng:
    SAVE_EVIDENCE_TO=docs/evidence python -m unittest discover -s tests -t .
    python tests/manual_console_check.py            (chỉ Windows)
    python tests/make_terminal_figures.py
Ghi chú: đây là hình DỰNG LẠI từ log, không phải ảnh chụp cửa sổ; trong log tự động (không có người gõ) các lệnh
đã gõ (ví dụ /list) không hiện lại, chỉ có kết quả. Không có tên test_*.py nên "unittest discover" không chạy file này.
"""
import os
import re
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "docs", "evidence")
IMAGES = os.path.join(ROOT, "docs", "img")
CHAR_WIDTH, LINE_HEIGHT, PAD = 8.0, 19, 16


def read_lines(filename):
    with open(os.path.join(EVIDENCE, filename), encoding="utf-8") as f:
        return f.read().splitlines()


def slice_between(lines, first_pattern, last_pattern):
    """Các dòng từ dòng khớp first_pattern tới dòng khớp last_pattern (gồm cả hai)."""
    start = next(i for i, line in enumerate(lines) if re.search(first_pattern, line))
    end = next(i for i in range(start, len(lines)) if re.search(last_pattern, lines[i]))
    return lines[start:end + 1]


def line_color(line):
    if line.startswith("[!]"):
        return "#fca5a5"                     # lỗi: đỏ nhạt
    if line.startswith("> "):
        return "#fde68a"                     # dòng nhập: vàng
    if line.startswith("[*]"):
        return "#93c5fd"                     # thông báo hệ thống: xanh
    if line.startswith("[") or line.strip().startswith("text:"):
        return "#86efac"                     # tin nhắn / dữ liệu: xanh lá
    return "#e5e7eb"


def panel_svg(x, y, title, lines):
    """Một cửa sổ terminal kiểu tối: thanh tiêu đề + các dòng chữ. Trả về (svg, width, height)."""
    width = int(max(len(title) + 6, *(len(line) for line in lines)) * CHAR_WIDTH + 2 * PAD)
    height = 34 + len(lines) * LINE_HEIGHT + PAD
    parts = [f'<g transform="translate({x},{y})">',
             f'<rect width="{width}" height="{height}" rx="9" fill="#111827"/>',
             f'<rect width="{width}" height="26" rx="9" fill="#1f2937"/><rect y="14" width="{width}" height="12" fill="#1f2937"/>',
             '<circle cx="16" cy="13" r="5" fill="#ef4444"/><circle cx="32" cy="13" r="5" fill="#f59e0b"/><circle cx="48" cy="13" r="5" fill="#22c55e"/>',
             f'<text x="64" y="17" class="bar">{escape(title)}</text>']
    for index, line in enumerate(lines):
        baseline = 34 + (index + 1) * LINE_HEIGHT - 5
        parts.append(f'<text x="{PAD}" y="{baseline}" fill="{line_color(line)}" xml:space="preserve">{escape(line) or " "}</text>')
    parts.append("</g>")
    return "\n".join(parts), width, height


def write_figure(filename, panels, label):
    """Xếp các panel cạnh nhau (cách 16 px) và ghi ra docs/img/<filename>."""
    body, x, tallest = [], 0, 0
    for title, lines in panels:
        svg, width, height = panel_svg(x, 0, title, lines)
        body.append(svg)
        x += width + 16
        tallest = max(tallest, height)
    total_width = x - 16
    style = ('<style>text{font-family:Consolas,"Cascadia Mono","Courier New",monospace;font-size:13.5px;white-space:pre}'
             '.bar{font-family:"Segoe UI",Arial,sans-serif;font-size:12px;fill:#9ca3af}</style>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_width} {tallest}" width="{total_width}" '
           f'role="img" aria-label="{escape(label)}">{style}\n' + "\n".join(body) + "\n</svg>\n")
    os.makedirs(IMAGES, exist_ok=True)
    with open(os.path.join(IMAGES, filename), "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote docs/img/{filename}  ({total_width}x{tallest})")


def main():
    console = read_lines("console_typing_while_receiving.txt")
    screen_2 = slice_between(console, r"^\[2\]", r"^> you can che")[1:]
    write_figure("hinh6_console_that.svg", [("Console Windows THẬT - tin đến lúc đang gõ dở", screen_2)],
                 "Màn hình console thật: tin nhắn chèn lên trên, dòng nhập giữ nguyên chữ đang gõ")

    session_a = read_lines("session_TestA.txt")[2:]
    session_b = read_lines("session_TestB.txt")[2:]
    chat = slice_between(session_a, r"Checking that the name", r"Your status is now away")
    write_figure("hinh8_phien_chat.svg", [("Máy của TestA - khởi động, danh sách online, chat, tin chưa đọc", chat)],
                 "Phiên chat thật: khởi động, danh sách online, chat, tin chưa đọc")

    sending = slice_between(session_a, r"chat during transfer", r"100%  Done")
    receiving = slice_between(session_b, r"chat during transfer", r"Received")
    write_figure("hinh7_gui_file.svg", [("Máy gửi (TestA)", sending), ("Máy nhận (TestB)", receiving)],
                 "Gửi file 3 MB có tiến độ trong lúc vẫn chat; máy nhận lưu file")

    wire = [line for line in read_lines("wire_format.txt")[2:] if "hex :" not in line]
    write_figure("hinh9_byte_tren_day.svg", [("Byte THẬT bắt được trên dây (peer giả ghi lại)", wire)],
                 "Các byte thật trên dây: gói UDP HELLO và các frame TCP")


if __name__ == "__main__":
    main()
