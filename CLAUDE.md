# Quy tắc của dự án LAN Chat (ĐỌC TRƯỚC KHI SỬA / THÊM CODE)

Đồ án socket: chat + gửi file trong mạng LAN, Python, **chỉ dùng thư viện chuẩn** (không `pip install`).
Người đọc code là **người mới học** → ưu tiên đơn giản, dễ đọc hơn là "thông minh" hay ngắn gọn.

## 1. Cấu trúc (PHẲNG, mỗi file một việc - không tách thư mục con cho code)

```
lanchat.py       Điểm vào: đọc tham số, khởi động thread, bảng lệnh /list /chat /send ...
config.py        Hằng số (cổng, 3 giây, 10 giây, timeout...). Không có logic.
state.py         Dữ liệu dùng chung giữa các thread + LOCK (tên mình, người online, kết nối chat, unread)
protocol.py      Khung tin TCP: HI / MSG / FILE / BYE, recv_exact, mở/đóng kết nối
discovery.py     UDP: broadcast HELLO + lắng nghe + danh sách online + /status
tcp_chat.py      TCP chat: acceptor, thread nhận tin, /chat, gửi tin, /leave
filetransfer.py  Gửi/nhận file, tiến độ %, thư mục downloads/
ui.py            Console: dòng nhập ở cuối, tin đến chèn lên trên, đọc từng phím
downloads/       File nhận được (không commit nội dung)
exercises/       Bài tập Milestone 1 (TCP echo, UDP send/recv)
tests/           Test tự động       docs/   Tài liệu, báo cáo, minh chứng, hình
```

- **Hướng phụ thuộc (không import ngược, không vòng):**
  `lanchat → tcp_chat → filetransfer → protocol / state / ui`; `discovery → state / ui`; `state, protocol → config`.
  `tests/test_project_rules.py` kiểm tra tự động.
- Không thêm file `.py` mới ở thư mục gốc. Việc mới → thêm vào đúng file theo công việc của nó. Nếu một file sắp
  vượt 300 dòng thì tách ra file mới tên rõ nghĩa **và** ghi nó vào `ALLOWED_IMPORTS` trong `tests/test_project_rules.py`.

## 2. Luật viết file

1. **Mỗi file MỘT việc.** Tên file nói rõ việc đó (xem bảng trên).
2. **Không file nào quá 300 dòng** (code lẫn `.md`). Test sẽ báo lỗi.
3. **Trước khi viết cái mới, kiểm tra nó đã có chưa** (Grep/Glob tìm tên hàm, tên file, từ khóa). Có rồi thì dùng lại
   hoặc sửa chỗ đó, không viết bản thứ hai.
4. **Chú thích cho người mới**, bằng tiếng Việt đơn giản:
   - Đầu mỗi file có khung chú thích: *việc của file / luồng chạy / bẫy hay gặp / đọc tiếp ở đâu*.
   - Mỗi hàm có 1-3 dòng nói nó làm gì; chỗ khó (lock, thread, byte) giải thích TẠI CHỖ vì sao.
   - Tên biến/hàm bằng tiếng Anh, rõ nghĩa (`peer_name`, không phải `pn`). Hàm ngắn (≈ dưới 30 dòng).
5. Không thêm thư viện ngoài, không thêm tính năng ngoài đề.

## 3. Luật thread và lock (hay bị hỏi vấn đáp)

- Dữ liệu dùng chung chỉ đọc/ghi qua hàm trong `state.py` (lock nằm sẵn trong hàm). Hàm trong `state.py` không in ra
  màn hình và không gọi hàm khác của `state.py` khi đang giữ lock → không deadlock.
- **Mọi thứ in ra màn hình đi qua `ui.show_message`**, không dùng `print()` trong code chạy ở thread nền.
- Thread nền là `daemon=True` và kiểm tra `state.is_stopped()` để dừng khi `/quit`.
- Mỗi socket chat chỉ có MỘT thread gửi (main thread). File gửi bằng kết nối TCP riêng.

## 4. Báo cáo và minh chứng

- `docs/BAO_CAO.md` là **báo cáo kỹ thuật, KHÔNG chứa code** (không khối ```, không trích hàm). Viết bằng lời, bảng, hình.
  Test sẽ báo lỗi nếu có khối code hoặc ảnh bị thiếu.
- Hình nằm ở `docs/img/`, minh chứng chạy thật (log, byte trên dây, kết quả test) ở `docs/evidence/`.
  Không bịa ảnh/kết quả: thứ chưa chụp/chưa chạy thì ghi rõ "CHƯA CÓ" (ví dụ ảnh Wireshark phải chụp trên 2 máy thật).

## 5. Chạy và kiểm tra

```
python lanchat.py --name Huy --port 5001
python -m unittest discover -s tests -t . -v
SAVE_EVIDENCE_TO=docs/evidence python -m unittest discover -s tests -t .   (lưu lại minh chứng)
```

Tài liệu: `README.md` (cài đặt/chạy) · `docs/HUONG_DAN_DOC_CODE.md` (thứ tự đọc code + luồng từng chức năng)
· `docs/PROTOCOL.md` (giao thức) · `docs/KE_HOACH.md` (kế hoạch, ngân hàng câu vấn đáp).
