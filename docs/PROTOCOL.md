# Giao thức LAN Chat

> Đề nói rõ: *"create your protocol by yourself"*. File này là **nguồn sự thật**: code trong `protocol.py` (khung TCP)
> và `discovery.py` (gói HELLO) khớp với nó, và phần "Protocol" của báo cáo lấy từ đây.
> Khi vấn đáp, bạn phải giải thích được **từng dòng** của file này.

## 1. UDP - thông báo hiện diện (discovery + status)

Một datagram, dạng text, gửi tới địa chỉ broadcast, cổng `9999`, mỗi **3 giây** (và ngay khi đổi `/status`):

```
HELLO|<name>|<tcp_port>|<status>
vd:  HELLO|Quan|5000|online
```

| Trường | Ý nghĩa | Ràng buộc |
|---|---|---|
| `name` | Tên hiển thị, **duy nhất** trong mạng | Không rỗng, không có dấu cách, **không chứa `\|`**, tối đa 20 ký tự |
| `tcp_port` | Cổng TCP mà peer này đang nghe | số nguyên 1-65535 |
| `status` | `online` hoặc `away` | một trong hai giá trị |

Quy tắc bên nhận (`discovery.py`, thread udp-listener):
- [x] Bỏ qua gói có `name` trùng tên mình (gói do chính mình phát; so không phân biệt hoa/thường).
- [x] Gói sai định dạng: bỏ qua, không crash (`parse_hello` trả `None`).
- [x] IP của peer = địa chỉ nguồn của datagram (không có trong gói).
- [x] Peer không nghe thấy trong **10 giây** -> coi như offline, in `[*] <name> went offline`.
- [x] Peer mới xuất hiện -> in `[*] <name> is online`; đổi `online <-> away` -> in `[*] <name> is now away`.
- [x] **Hai peer trùng `name`: từ chối người đến sau.** Lúc khởi động (`discovery.find_name_owner`) chương trình nghe
  3.5 giây (lâu hơn chu kỳ 3 s) trước khi tự phát; nếu nghe thấy HELLO mang tên mình thì thoát với lỗi
  "The name 'X' is already used by <IP>".

## 2. TCP - khung dữ liệu (framing)

TCP là dòng byte nên mọi gói đều có header. Trường trong header ngăn cách bằng `|` (header kết thúc bằng `|`).

| Frame | Định dạng | Ghi chú |
|---|---|---|
| Giới thiệu | `HI\|<name>\|<kind>\|` | Frame **đầu tiên** của mọi kết nối TCP. `kind` = `chat` hoặc `file` |
| Tin nhắn | `MSG\|<length>\|<nội dung>` | `length` = số **BYTE** UTF-8 (không phải số ký tự) |
| Gửi file | `FILE\|<filename>\|<size>\|<byte của file>` | `size` = số byte; chỉ chứa **tên** file, không đường dẫn |
| Kết thúc | `BYE\|` | Báo đóng chat lịch sự |

Cách bên nhận đọc (`protocol.read_frame`) - đây là câu vấn đáp quan trọng:
1. Đọc **từng byte** tới `|` đầu tiên -> biết **loại** frame (`recv_until`). Đọc từng byte để không bao giờ đọc lẹm sang phần sau.
2. Tùy loại, đọc thêm các trường, mỗi trường kết thúc bằng `|`.
3. Với `MSG`: đọc **đúng `length` byte** bằng vòng lặp `recv` (`recv_exact`) rồi `decode("utf-8")`.
4. Với `FILE`: chỉ đọc header; phần byte file do `filetransfer.receive_file` đọc **đúng `size` byte**, ghi ra đĩa từng khối.

Quyết định thiết kế:
- [x] Header kết thúc bằng `|` (như mẫu của đề), không dùng xuống dòng.
- [x] Giới hạn: header tối đa 1024 byte (`config.HEADER_MAX_LEN`), một tin tối đa 1 MB (`config.MAX_MSG_BYTES`).
  Vượt quá hoặc `length` không phải số -> `ValueError` -> đóng kết nối, không crash.
- [x] Ký tự `|` trong nội dung `MSG` **không sao**, vì nội dung được đọc theo `length`, không tìm dấu `|`.
  Trong **filename** thì có sao (vì filename nằm trong header), nên người gửi đổi `|` thành `_`.
- [x] **Vì sao HI có thêm `kind`?** (khác mẫu đề) Người nhận cần biết ngay kết nối này để chat hay để nhận file.
  Nếu không, một kết nối gửi file có thể bị nhầm là kết nối chat và đè lên kết nối chat thật.

## 3. Luồng hoạt động

**Mở chat** (A gõ `/chat B`):
```
A ---- TCP connect ----> B          (bắt tay 3 bước, thấy được trong Wireshark)
A ---- HI|A|chat| ------> B         B biết "kết nối này của A", lưu vào state, bật thread nhận tin
A ---- MSG|5|Hello ----> B          hai chiều, trên cùng một kết nối
B ---- MSG|3|Hi! ------> A
A ---- BYE| ------------> B         /leave hoặc /quit; rồi A đóng socket
```

**Gửi file** (kết nối RIÊNG, theo cập nhật 09/11 của đề):
```
A ---- TCP connect (kết nối mới) ----> B
A ---- HI|A|file| -------------------> B
A ---- FILE|slides.pdf|2516582| -----> B
A ---- <2516582 byte, từng khối 64 KB> -> B   (thread riêng, chat vẫn chạy)
A ---- đóng kết nối                    B   B kiểm tra đã nhận đủ size byte chưa
```

## 4. Xử lý lỗi theo giao thức

| Tình huống | Bên phát hiện | Cách xử lý |
|---|---|---|
| Peer đóng/crash giữa chat | `recv` trả `b""` hoặc `ConnectionError` | `[*] B disconnected (connection lost).`, gỡ kết nối, nếu là partner thì hết partner; về prompt |
| Peer gửi `BYE` | bên nhận | `[*] B left the chat.` rồi dọn như trên |
| Header sai / `length` không phải số / loại frame lạ | bên nhận | `ValueError` -> đóng kết nối đó |
| Kết nối mới không gửi HI trong 5 s | acceptor | đóng kết nối (chống kết nối rác chiếm thread) |
| File đứt giữa chừng (hoặc 30 s không có byte) | bên nhận | xóa file dở + `[!] Receiving ... failed ... Partial file deleted.` |
| Connect tới peer đã offline | bên gọi | `[!] Cannot connect to B: <lý do>` sau tối đa 3 s, không crash |
| Kết nối chat mới tới khi đã có kết nối cũ cùng tên | bên nhận | kết nối **mới thay thế** kết nối cũ (cũ thường đã chết do đối phương khởi động lại) |
