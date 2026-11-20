# Hướng dẫn đọc code (cho người mới)

Mỗi file Python mở đầu bằng một khung chú thích: **việc của file / luồng chạy / bẫy hay gặp / đọc tiếp ở đâu**.
Chỉ cần đọc khung đó là biết file làm gì và nên đọc file nào kế tiếp.

## 1. Bản đồ: 8 file, mỗi file một việc

| File | Việc duy nhất của nó | Số dòng | Thread liên quan |
|---|---|---|---|
| `lanchat.py` | Điểm vào, đọc tham số, bảng lệnh `/list /chat /send...` | 214 | Main |
| `config.py` | Hằng số: cổng 9999, chu kỳ 3 s, timeout 10 s... | 46 | - |
| `state.py` | Dữ liệu dùng chung + lock: người online, kết nối chat, unread | 225 | mọi thread |
| `protocol.py` | Khung tin TCP `HI/MSG/FILE/BYE`, `recv_exact`, mở/đóng kết nối | 158 | - |
| `discovery.py` | UDP: phát HELLO, nghe HELLO, danh sách online, `/status` | 205 | udp-broadcaster, udp-listener |
| `tcp_chat.py` | TCP chat: acceptor, nhận tin, `/chat`, gửi tin, `/leave` | 240 | tcp-acceptor, tcp-receiver, chat-receiver |
| `filetransfer.py` | Gửi/nhận file, tiến độ %, tên file an toàn | 186 | file-sender |
| `ui.py` | Dòng nhập ở cuối, in tin phía trên, đọc từng phím | 190 | Main (và mọi thread khi in) |

Thư mục khác: `downloads/` (file nhận được) · `exercises/` (bài M1) · `tests/` · `docs/`.

## 2. Thứ tự đọc gợi ý (mỗi bước 10-15 phút)

1. `README.md`, rồi **chạy thử** hai instance để thấy chương trình làm gì.
2. `lanchat.py` - toàn cảnh: 8 bước khởi động, bảng lệnh, các thread.
3. `protocol.py` + `tests/test_protocol.py` - khung TCP, vì sao cần `recv_exact`, vì sao `length` là byte.
4. `discovery.py` + `state.py` (phần người online) - phát hiện người dùng bằng UDP.
5. `tcp_chat.py` - chat: acceptor, thread nhận tin, unread, `/leave`, xử lý khi peer tắt đột ngột.
6. `ui.py` - gõ dở mà tin đến không mất chữ.
7. `filetransfer.py` - gửi/nhận file ở thread riêng.
8. `state.py` (phần lock) và `docs/PROTOCOL.md` - ôn lại luồng và giao thức.

## 3. Luồng từng chức năng

### 3.1 Khởi động `python lanchat.py --name Quan --port 5000`
```
main() -> kiểm tra tên/cổng -> ui.init_terminal() -> state.set_identity()
       -> tcp_chat.start_acceptor(port)        mở cổng TCP, tạo thread acceptor
       -> discovery.find_name_owner()          nghe 3.5 s xem tên đã có ai dùng chưa
       -> discovery.start_discovery()          thread phát HELLO + thread nghe HELLO
       -> ui.input_loop(handle_line)           main thread ở đây tới khi /quit
```

### 3.2 Phát hiện người dùng (UDP)
```
[Máy A] _broadcaster_loop:  HELLO|Quan|5000|online  --broadcast-->  cổng 9999   (mỗi 3 s)
[Máy B] _listener_loop: recvfrom -> parse_hello -> state.update_peer
        -> "new" thì in "[*] Quan is online"      (mỗi vòng còn dọn người im quá 10 s -> "went offline")
[B gõ /list] cmd_list -> discovery.format_peer_list() -> "  1. Quan  (192.168.1.12)  online"
[A gõ /status away] discovery.set_status -> state + đánh thức broadcaster gửi HELLO ngay
```

### 3.3 `/chat Minh` rồi gõ tin
```
cmd_chat -> discovery.find_peer("Minh") -> tcp_chat.open_chat
   chưa có kết nối: connect_to -> protocol.connect_and_introduce (connect + HI|Quan|chat|)
                    -> state.add_connection -> bật thread chat-receiver (_receive_loop)
   rồi state.set_partner("Minh") -> in "[*] Connected to Minh (ip:port)"
gõ "hello" -> handle_line -> tcp_chat.send_text -> protocol.send_msg -> in "[Quan] hello"

[Máy Minh] _accept_loop -> handle_connection: đọc HI|Quan|chat| -> state.add_connection -> _receive_loop
        read_frame -> MSG -> state.record_incoming
           partner là Quan?  CÓ: in "[Quan] hello"     KHÔNG: unread+1, in "[*] New message from Quan (1 unread)"
```

### 3.4 Tin đến lúc đang gõ dở (đề mục 4.3)
```
Người dùng đã gõ "you can che"  ->  ui._buffer = "you can che"
Thread nhận tin gọi ui.show_message("[Minh] ok"), trong _screen_lock:
   1. ghi "\r\033[K"          xóa dòng nhập
   2. ghi "[Minh] ok\n"       in tin
   3. ghi "> you can che"     vẽ lại dấu nhắc + chữ đang gõ dở
Người dùng gõ tiếp "cked" như chưa có chuyện gì xảy ra.
```
Khi bấm Enter: `_take_line()` lấy dòng ra **trong lock**, rồi `on_line(line)` chạy **ngoài lock**
(nếu chạy trong lock, lệnh gọi `show_message` sẽ xin lock lần nữa và treo vĩnh viễn).

### 3.5 `/send slides.pdf`
```
cmd_send -> filetransfer.send_file_async: kiểm tra có partner, file tồn tại -> tạo THREAD _send_file_worker, trả về ngay
worker: connect + HI|Quan|file| -> FILE|slides.pdf|2516582| -> vòng lặp đọc 64 KB, sendall, mỗi 10% in "... 30%"
[Máy nhận] handle_connection: HI kind=file -> đọc FILE -> filetransfer.receive_file:
         _open_download (tên an toàn, không ghi đè) -> recv(min(64KB, còn lại)) -> ghi
         đủ size: "[*] Received ..."   |   đứt giữa chừng: xóa file dở + báo lỗi
```
Main thread không bị chặn nên vẫn gõ và nhận tin trong lúc gửi file.

### 3.6 Lỗi thường gặp và nơi xử lý
| Tình huống | Xử lý ở |
|---|---|
| Peer tắt đột ngột giữa chat | `tcp_chat._receive_loop` bắt `ConnectionError` -> `_cleanup` |
| `/chat` người vừa offline | `tcp_chat.connect_to` bắt `OSError` (timeout 3 s) |
| Gõ lệnh sai | `lanchat.handle_line` in "Unknown command" + danh sách lệnh |
| File không tồn tại | `filetransfer.send_file_async` (kiểm tra trước khi tạo thread) |
| File đứt giữa chừng | `filetransfer.receive_file`: xóa file dở |
| Gói UDP rác | `discovery.parse_hello` trả `None` -> bỏ qua |
| Lỗi bất ngờ trong một lệnh | `lanchat.handle_line` bắt `Exception`, báo `[!] Error` |
| Trùng tên | `discovery.find_name_owner` + `lanchat.start_network` từ chối khởi động |

## 4. Bảng thread (đề mục 5.1)

| Thread | Tạo ở | Đang chờ gì | Việc làm |
|---|---|---|---|
| Main | `lanchat.main` | bàn phím | `ui.input_loop` -> `handle_line` |
| udp-broadcaster | `discovery.start_discovery` | đồng hồ 3 s | gửi HELLO |
| udp-listener | `discovery.start_discovery` | gói UDP (tối đa 1 s) | cập nhật người online, dọn người hết hạn |
| tcp-acceptor | `tcp_chat.start_acceptor` | `accept()` | mỗi kết nối mới tạo thread tcp-receiver |
| tcp-receiver | `tcp_chat._accept_loop` | frame HI rồi frame đầu | chat -> vòng nhận tin; file -> `receive_file` |
| chat-receiver | `tcp_chat.connect_to` | `recv()` trên socket của peer | hiện tin, báo unread |
| file-sender | `filetransfer.send_file_async` | đọc đĩa / `sendall` | gửi file, báo % |

## 5. Bảng lock

| Lock | Nằm ở | Bảo vệ | Ai tranh nhau |
|---|---|---|---|
| `_data_lock` | `state.py` | tên mình, người online, kết nối, partner, unread, lịch sử | udp-listener và các thread nhận tin ghi; main đọc/ghi |
| `_screen_lock` | `ui.py` | màn hình + chữ đang gõ | MỌI thread in ra |

Không bao giờ giữ hai lock cùng lúc, nên không thể có deadlock kiểu "A chờ B, B chờ A".

## 6. Muốn tìm chức năng trong đề -> mở file nào

| Đề (điểm) | File chính |
|---|---|
| UDP discovery, online list, status (15) | `discovery.py`, `state.py` (peers) |
| TCP chat, nhiều peer, unread (20) | `tcp_chat.py`, `state.py` (chat), `protocol.py` |
| File transfer, tiến độ, downloads/ (15) | `filetransfer.py` |
| Console UI (15) | `ui.py` |
| Protocol, framing (10) | `protocol.py`, `discovery.py` (HELLO), `docs/PROTOCOL.md` |
| Lỗi và ổn định (10) | `tcp_chat._cleanup`, `tcp_chat.connect_to`, `filetransfer.receive_file`, `lanchat.handle_line` |
