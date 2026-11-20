"""
tests/ - Test tự động. Không cần mạng thật (trừ test_end_to_end). Chạy từ thư mục gốc:

    python -m unittest discover -s tests -t . -v

  test_protocol.py       khung TCP (HI/MSG/FILE/BYE), recv_exact, dữ liệu rác                (protocol.py)
  test_discovery.py      gói UDP HELLO, tìm người theo tên/số, định dạng /list               (discovery.py)
  test_state.py          dữ liệu dùng chung, kể cả nhiều thread cùng ghi                     (state.py)
  test_filetransfer.py   tên file an toàn, không ghi đè, nhận file đủ/đứt giữa chừng, tiến độ (filetransfer.py)
  test_ui.py             dòng nhập không bị tin nhắn đến phá                                 (ui.py)
  test_project_rules.py  kiểm tra các luật tổ chức trong CLAUDE.md
  test_end_to_end.py     chạy 3 chương trình thật trên một máy và cho chúng chat, gửi file
  test_wire_format.py    đọc từng BYTE thật chương trình gửi ra (UDP HELLO, TCP HI/MSG/BYE/FILE) bằng peer giả
  manual_console_check.py  (chạy tay, chỉ Windows) bơm phím thật vào console thật để kiểm tra UI gõ dở
"""
