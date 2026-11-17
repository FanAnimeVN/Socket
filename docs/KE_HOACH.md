# Kế hoạch đồ án LAN Chat & File Sharing (Python, TCP + UDP)

**Nhóm:** Lê Nhật Huy · Trần Nguyễn Hồng Ngọc · Trịnh Minh Phong
**Lập ngày:** Chủ nhật 15/11/2026 · **Hạn nội bộ:** Thứ Bảy 28/11/2026 (hạn thật ~29/11 coi như ngày dự phòng khẩn cấp)
**Giả định thời gian:** thứ 2–6 ≈ 2 giờ/người/ngày, cuối tuần ≈ 3–4 giờ/người/ngày → tổng ≈ 30–35 giờ/người. Nếu ngày nào bận thi/bài tập môn khác, ghi vào Day 0 và dời việc sang ngày khác, **không dồn sang D12–D13**.

---

## 0. Nguyên tắc làm việc (để vấn đáp được)

1. **Tự gõ từng dòng, giải thích được từng dòng.** File demo của đề (`udp_broadcast_demo.py`, `option_a/b`, `chat_redraw.cpp`) là tài liệu được cung cấp: dùng để học, gõ lại, chú thích bằng lời của mình, rồi sửa/mở rộng. Không dán vào mà chưa hiểu. Nếu không chắc quy định "tự code" cho phép dùng demo đến đâu, hỏi giảng viên.
2. **Mỗi module có 1 người viết + 1 người "teach-back"** (xem mục 4): người viết giảng lại cho người review nghe, người review phải giải thích ngược lại được. Vấn đáp sẽ hỏi bất kỳ ai về bất kỳ chức năng nào.
3. **Tích hợp sớm, test 2 máy thật sớm** (D6), đừng để đến cuối.
4. **Feature freeze D11** (Thứ Năm 26/11): sau đó chỉ sửa lỗi nghiêm trọng, luyện vấn đáp và làm tài liệu.
5. **Ưu tiên theo trọng số điểm:** TCP chat 20 > UDP 15 = File 15 = UI 15 > Protocol 10 = Lỗi/ổn định 10 = Report 10 > Demo/code 5.

---

## 1. Tóm tắt yêu cầu của đề (checklist chấm điểm)

| Hạng mục | Điểm | Những ý dễ bỏ sót |
|---|---|---|
| UDP discovery, online list, status | 15 | Broadcast mỗi **3 s** trên cổng cố định (9999); không nghe thấy **10 s** → xoá; **thông báo** khi user online/offline; status online/away nằm trong gói broadcast |
| TCP chat | 20 | Mở TCP tới peer đã chọn; gõ tin bất kỳ lúc nào; tin tới hiện ngay; **tin của người không phải partner hiện tại phải được lưu + thông báo "(N unread)"**; nhiều peer cùng lúc |
| File transfer | 15 | `/send <file>`; **tiến độ %**; lưu vào `downloads/`; chat vẫn chạy trong lúc gửi (thread riêng) |
| Console UI | 15 | Dòng cuối luôn là dòng nhập; tin tới chèn lên trên; **giữ nguyên chữ đang gõ dở**; có lock bảo vệ màn hình |
| Protocol & framing | 10 | Tự thiết kế; mọi frame có header (loại + độ dài); nhận **đúng N byte** (vòng lặp `recv`) |
| Error handling | 10 | Peer đóng/crash; connect tới người đã offline; file không tồn tại/đứt giữa chừng → **xoá file dở**; lệnh sai → hiện help ngắn |
| Report | 10 | 5–10 trang: kiến trúc, thread model, protocol, vấn đề gặp & cách giải; **Wireshark**: UDP broadcast + TCP 3-way handshake kèm giải thích |
| Demo & code quality | 5 | 10 phút, **≥ 2 máy**; README (cài đặt, chạy, test) |

**Cập nhật 09/11/2026 của đề:** cho phép "TCP receiver (one per connection)" → mỗi kết nối TCP có thread nhận riêng; kết nối chat chỉ hiện tin, **kết nối file chỉ lưu file**. Đây là gợi ý chính thức để gửi file bằng **kết nối riêng** (đơn giản hơn nhiều, xem mục 3).

**Mốc của đề (M1→M5)** map vào lịch của mình: M1 = D2, M2 = D5–D6, M3 = D7, M4 = D9, M5 = D10–D13. Nếu giảng viên có hạn trung gian cho từng mốc, hãy đối chiếu và dời lịch cho khớp.

---

## 2. Kiến trúc đề xuất

### 2.1 Thread model (khớp bảng 5.1 của đề)

```
Shared state (có lock): peers{}  connections{}  unread{}  history{}  my_status  current_partner

Main thread        : đọc phím, chạy lệnh, gửi MSG
UDP broadcaster    : mỗi 3 s gửi  HELLO|name|tcp_port|status
UDP listener       : nhận HELLO, cập nhật peers, xoá peer im quá 10 s, báo online/offline
TCP acceptor       : accept() -> mỗi kết nối mới tạo 1 receiver thread
TCP receiver (mỗi kết nối): recv đủ byte, hiện MSG / lưu FILE
File sender (mỗi lần gửi) : gửi file qua kết nối riêng, không chặn chat

Mọi thread muốn in ra màn hình đều gọi ui.show_message()  (giữ screen_lock)
```

### 2.2 Cấu trúc file (mỗi người sở hữu file riêng → ít xung đột khi ghép)

```
Socket/                  (thư mục gốc của repo, cấu trúc PHẲNG để `python lanchat.py` chạy từ gốc)
  lanchat.py        # main: argparse (--name --port --bcast), khởi động thread, vòng lặp lệnh   (Huy)
  config.py         # hằng số dùng chung
  state.py          # dữ liệu dùng chung + lock
  protocol.py       # đóng/mở frame, recv_exact                                                 (Huy)
  tcp_chat.py       # acceptor, receiver, connect_to, /chat, /leave                             (Huy)
  discovery.py      # UDP broadcaster + listener + timeout                                      (Ngọc)
  filetransfer.py   # send_file (thread), receive_file, tiến độ                                 (Phong)
  ui.py             # screen_lock, show_message, đọc phím                                       (Phong)
  downloads/  exercises/  tests/  docs/  README.md
```

Tên hàm gợi ý (để 3 người code song song mà ghép được): `show_message(line)`, `recv_exact(sock, n)`, `send_msg(sock, text)`, `read_frame(sock)`, `start_discovery(...)`, `get_peers()`, `set_status(s)`, `start_acceptor(port)`, `connect_to(name)`, `send_file_async(name, path)`.

---

## 3. Quyết định phải chốt ở Day 0 ("hợp đồng thiết kế")

| # | Quyết định | Đề xuất | Lý do |
|---|---|---|---|
| 1 | Định danh peer | Khóa theo `name` (bắt buộc duy nhất); lọc broadcast của chính mình bằng tên | Chạy nhiều instance trên **1 máy** thì IP giống hệt nhau, không dùng IP làm khóa được |
| 2 | Người nhận biết ai đang kết nối | Frame đầu tiên của **mọi** kết nối TCP: `HI|<name>|` | `accept()` chỉ thấy (IP, cổng ngẫu nhiên), không biết tên. Cần tên để đếm unread/hiện `[Minh]` |
| 3 | Định dạng frame | `HI|name|` · `MSG|<len>|<text>` · `FILE|<filename>|<size>|<bytes>` · `BYE|` ; `len` = **số byte UTF-8** | Đúng gợi ý đề, dễ giải thích; xem bẫy #1 |
| 4 | Gửi file | **Kết nối TCP riêng** cho mỗi lần gửi (theo cập nhật 09/11) | Tránh 2 thread cùng `sendall` trên một socket làm trộn dữ liệu (bẫy #5) |
| 5 | Một cặp A–B có mấy kết nối chat? | Một. Nếu đã có kết nối (kể cả do đối phương mở tới) thì `/chat` **dùng lại**, không mở thêm | `/chat` lúc đó = "chọn partner", tin chưa đọc được hiển thị ra |
| 6 | Quy tắc lock | Một `screen_lock` cho màn hình + một lock cho dữ liệu; **không in khi đang giữ lock dữ liệu**, **không gọi hàm lấy lock dữ liệu khi đang giữ screen_lock** | Tránh deadlock |
| 7 | Cờ dòng lệnh | `--name`, `--port` (TCP), `--bcast` (mặc định 255.255.255.255) | Khớp ví dụ 4.2 và gợi ý test 1 máy |
| 8 | Ngôn ngữ report/README | Hỏi giảng viên (đề viết tiếng Anh) | Tránh viết lại |

Chọn UI: **Option B** (đọc từng phím + vẽ lại thủ công, chỉ thư viện chuẩn) để hiểu cơ chế và trả lời được "vì sao `\r\033[K`". Phương án dự phòng: **Option A** (`prompt_toolkit` + `patch_stdout`) nếu D8 vẫn còn lỗi hiển thị nghiêm trọng. Cả hai đều được đề chấp nhận.

---

## 4. Phân công

| Người | Vai trò | Module chính | Điểm phụ trách |
|---|---|---|---|
| **Huy** | TCP + Protocol, lead tích hợp | `protocol.py`, `tcp_chat.py`, `lanchat.py` | TCP chat 20 + Protocol 10 |
| **Ngọc** | UDP + QA/Tài liệu | `discovery.py`, test matrix, Wireshark, README, ghép report | UDP 15 + (Lỗi 10, Report 10 cùng góp) |
| **Phong** | UI + File | `ui.py`, `filetransfer.py` | UI 15 + File 15 |

Code của Ngọc nhẹ hơn nên Ngọc nhận thêm test/Wireshark/README/ghép report; Huy nặng code nhất nên ít việc report nhất. Có thể đổi vai sau D7, miễn mỗi module vẫn có người viết rõ ràng.

**Vòng review chéo (teach-back):**
- Code UDP của Ngọc ← **Huy** review
- Code UI + File của Phong ← **Ngọc** review
- Code TCP + Protocol của Huy ← **Phong** review

Cách review: người viết giảng 15–20 phút (dòng nào chạy khi nào, thread nào, khóa nào); người review đóng vai "giám khảo" hỏi "nếu X xảy ra thì sao?", rồi **tự giải thích lại**. Vòng 1 ở D5–D7, vòng 2 (đổi cặp) ở D11.

---

## 5. Lộ trình theo ngày

Quy ước: ✔ = checkpoint cuối ngày.

| Ngày | Ngày tháng | Giờ/người | Huy | Ngọc | Phong |
|---|---|---|---|---|---|
| **D0** | CN 15/11 | ~3 | **Cả 3:** đọc kỹ đề (mỗi người tóm tắt 1 phần cho nhóm), chạy thử 4 file demo (3 terminal cho `udp_broadcast_demo.py`), vẽ thread model ra giấy, chốt mục 3, tạo thư mục + `PROTOCOL.md`, thống nhất giờ họp | ↑ cả nhóm | ↑ cả nhóm |
| **D1** | T2 16/11 | 2 | **Cả 3 (mỗi người tự làm):** TCP echo server + client (1 client). Học: `socket/bind/listen/accept/connect/send/recv`, `str` vs `bytes` | ↑ cả nhóm | ↑ cả nhóm |
| **D2** | T3 17/11 | 2 | **Cả 3:** UDP gửi/nhận + broadcast (từ demo), echo server nhiều client bằng thread. Tối: 20 phút demo cho nhau ✔ **M1** | ↑ cả nhóm | ↑ cả nhóm |
| **D3** | T4 18/11 | 2 | `protocol.py`: `recv_exact`, `send_msg`, `read_frame`; test qua echo, **có tiếng Việt** | `discovery.py` v1: broadcaster + listener, parse `HELLO`, lọc gói của chính mình | `ui.py` v1: gõ lại option B, `show_message`, parser lệnh; **thử gõ tiếng Việt (Unikey/Telex)** |
| **D4** | T5 19/11 | 2 | Acceptor + receiver thread (in tin nhận được kèm tên người gửi) | `peers{}` + lock, `last_seen`, timeout 10 s, thông báo online/offline, `/list`, `/status` | Dispatcher lệnh (`/help`, `/quit`, lệnh sai), Ctrl+C; script độc lập gửi file qua socket |
| **D5** | T6 20/11 | 2 | Review `discovery.py` của Ngọc (teach-back); `connect_to` + `HI` | Chạy 3 instance/1 máy (`--name`, `--port`), sửa lỗi | `send_file` độc lập: thread, đọc theo khối, tính % ✔ **M2 (1 máy)** |
| **D6** | T7 21/11 | 4 | **Tích hợp #1 (cả nhóm):** ghép UI + Discovery vào `lanchat.py`. **Test 2 máy thật** (hotspot/router riêng): firewall, broadcast. Huy thêm `/chat` + MSG hai chiều | ↑ cả nhóm | ↑ cả nhóm |
| **D7** | CN 22/11 | 4 | `/leave`, `BYE`, nhiều peer, unread + history, xử lý peer crash ✔ **M3** | Bắt đầu README + dàn bài report; tập dùng Wireshark (filter `udp.port==9999`, `tcp.flags.syn==1`) | `/send` qua kết nối riêng; receiver `FILE` → `downloads/`; review `tcp_chat.py` của Huy |
| **D8** | T2 23/11 | 2 | **Tích hợp #2:** chat + UI + discovery; 3 instance: A↔B chat, C nhắn A → unread | Test kịch bản 3 instance, ghi bug | Tiến độ % in theo mốc qua `show_message`; sửa hiển thị khi tin tới lúc đang gõ |
| **D9** | T3 24/11 | 2 | Sửa bug tích hợp; hỗ trợ file | Test file: nhỏ/lớn/nhị phân, **so hash** | Gửi file lớn **trong lúc chat** ✔ **M4**; trùng tên file; tên file nguy hiểm (`..\`) |
| **D10** | T4 25/11 | 2 | Sửa bug theo danh sách của Ngọc | **Chạy test matrix lỗi** (mục 9); chụp Wireshark trên 2 máy | Xoá file dở khi đứt; lỗi file không tồn tại |
| **D11** | T5 26/11 | 2 | **FEATURE FREEZE.** Review chéo vòng 2; **mock vấn đáp #1**; nộp bản nháp phần report của mình | ↑ cả nhóm | ↑ cả nhóm |
| **D12** | T6 27/11 | 3 | **Diễn tập demo 2 máy, bấm giờ** (mục 8); README chạy thử trên thư mục sạch bởi người **không** viết nó; mock vấn đáp #2; ghép report + ảnh Wireshark | ↑ cả nhóm | ↑ cả nhóm |
| **D13** | T7 28/11 | 3 | **Dự phòng + nộp.** Chỉ sửa lỗi nghiêm trọng; kiểm tra gói nộp (mục 11) | ↑ cả nhóm | ↑ cả nhóm |


---

## 6. Bản đồ kiến thức Python/socket "học đến đâu dùng đến đó"

| Chủ đề | Cần lúc | Tự kiểm tra: bạn giải thích được... |
|---|---|---|
| `str` vs `bytes`, `encode/decode`, `split("\|")`, f-string | D1 | Vì sao `len("Việt")` ≠ `len("Việt".encode("utf-8"))`? |
| TCP: `socket, bind, listen, accept, connect, send/sendall, recv, close` | D1 | `accept()` trả về gì? Vì sao socket nghe ≠ socket nói chuyện? |
| UDP: `SOCK_DGRAM, sendto, recvfrom, SO_BROADCAST, SO_REUSEADDR` | D2 | Vì sao 3 instance bind chung cổng 9999 được? Bind `""` nghĩa là gì? |
| `threading.Thread(target, args, daemon=True)`, `Lock`, `with lock` | D2–D3 | Daemon thread khác thread thường thế nào? Lock bảo vệ cái gì? |
| `try/except`: `ConnectionResetError`, `socket.timeout`, `OSError` | D4 | `recv()` trả `b""` nghĩa là gì? |
| `argparse` | D3 | Chạy nhiều instance bằng cờ nào? |
| File nhị phân `open(p,"rb"/"wb")`, `os.path.getsize/basename`, đọc theo khối | D4 | Vì sao không đọc cả file vào RAM? |
| `time.time()`, `settimeout` | D4 | Timeout 10 s của peer được kiểm tra ở đâu? |
| `msvcrt.getwch`, mã ANSI `\r\033[K` | D3 | 3 bước vẽ lại dòng nhập là gì? Vì sao cần `buffer` và lock? |

---

## 7. Bẫy kỹ thuật thường gặp (và hay bị hỏi)

1. **`len(text)` ≠ số byte.** Tiếng Việt có dấu là nhiều byte trong UTF-8 → header phải ghi `len(text.encode("utf-8"))`, nhận đúng ngần ấy **byte** rồi mới `decode`.
2. **`recv(n)` có thể trả về ít hơn `n`.** Phải lặp trong `recv_exact`. `recv` trả `b""` = peer đã đóng → thoát vòng lặp, báo ngắt kết nối.
3. **`threading.Lock` không reentrant.** Trong `option_b`, xử lý phím nằm trong `with screen_lock`; khi mở rộng thành app thật, nếu bên trong khối đó chạy lệnh mà lệnh lại gọi `show_message` (cũng lấy `screen_lock`) → **treo vĩnh viễn**. Hãy lấy dòng nhập ra, **nhả lock**, rồi mới chạy lệnh.
4. **Thứ tự lock:** không in màn hình khi đang giữ lock dữ liệu, và ngược lại, để tránh deadlock chéo giữa hai thread.
5. **Hai thread cùng `sendall` trên một socket** (gửi chat + gửi file) có thể làm byte của hai frame trộn lẫn → hỏng stream. Giải pháp: kết nối riêng cho file (đề xuất) hoặc lock riêng cho từng socket.
6. **Biết ai đang gửi:** acceptor chỉ thấy IP + cổng ngẫu nhiên; trên 1 máy mọi peer cùng IP → cần frame `HI|name|` đầu mỗi kết nối.
7. **Tự nhận gói broadcast của chính mình:** phải lọc (so tên; đảm bảo tên duy nhất).
8. **`255.255.255.255` trên Windows nhiều card mạng** (VPN, WSL, Hyper-V, VirtualBox) có thể đi sai card → thêm `--bcast`, hoặc tính địa chỉ broadcast của subnet. Cần test thật.
9. **Windows Firewall:** mạng "Public" chặn kết nối vào → cho phép Python hoặc đặt mạng là Private. **Wi-Fi trường/KTX thường bật "client isolation"** (các máy không thấy nhau) → demo bằng **hotspot điện thoại** hoặc router riêng; thử sớm ở D6.
10. **Tên file nhận được** phải làm sạch (`os.path.basename`) để không ghi ra ngoài `downloads/`; xử lý trùng tên.
11. **File dở:** đếm byte đã nhận; thiếu/đứt → đóng file và xoá. Kiểm tra toàn vẹn bằng hash: `certutil -hashfile <file> SHA256` (Windows).
12. **Tiến độ %:** đừng in mỗi khối; in theo mốc (mỗi 10% hoặc mỗi ~0.5 s) qua `show_message` để không làm vỡ dòng nhập.
13. **Giới hạn của vẽ lại thủ công:** dòng gõ dài hơn chiều rộng cửa sổ (xuống dòng), ký tự rộng/emoji, phím mũi tên/Home/End bị bỏ qua. Chấp nhận và ghi vào report, hoặc chuyển Option A. *Gõ tiếng Việt có dấu bằng Unikey/Telex với `getwch` là điều mình chưa kiểm chứng — thử ở D3.*
14. **Kết thúc êm:** thread nền dùng `daemon=True`; `/quit` gửi `BYE` và đóng socket.
15. **TCP listen:** đặt `SO_REUSEADDR` để chạy lại ngay cùng cổng; `connect` dùng timeout (~3 s) để kết nối tới người đã offline không treo.

---

## 8. Chuẩn bị vấn đáp & demo

### 8.1 Ngân hàng câu hỏi (luyện ở D11, D12: bốc ngẫu nhiên một hàm/chức năng, người được hỏi phải giải thích)

**UDP / discovery**
- Vì sao dùng UDP cho phát hiện peer? Mất gói thì sao?
- Broadcast là gì? `SO_BROADCAST`, `SO_REUSEADDR` để làm gì? Vì sao bind `""`?
- Làm sao biết một peer offline? (`last_seen`, 10 s) Kiểm tra ở thread nào?
- Vì sao phải lọc gói của chính mình? Nếu hai người trùng tên thì sao?
- `/status away` đến người khác bằng cách nào, trễ tối đa bao lâu?

**TCP / protocol**
- TCP là byte stream, không có ranh giới tin nhắn → bạn xử lý bằng gì? (framing)
- Vì sao cần `recv_exact`? `sendall` khác `send` ra sao?
- Vì sao `len` tính bằng byte? Điều gì xảy ra nếu tính bằng ký tự?
- Frame nào có trong giao thức? Giải thích từng trường. Nếu nội dung tin có ký tự `|` thì sao?
- Bắt tay 3 bước: trong ảnh Wireshark gói nào là SYN, SYN-ACK, ACK?
- Peer tắt đột ngột: bên còn lại phát hiện thế nào? (`recv` trả `b""` / `ConnectionResetError`)

**Thread / đồng bộ**
- Liệt kê các thread, mỗi thread đang chờ gì? Vì sao cần thread cho mỗi kết nối?
- Dữ liệu nào dùng chung? Lock nào bảo vệ gì? Nếu bỏ lock thì lỗi gì có thể xảy ra?
- Deadlock là gì, nhóm tránh thế nào? Vì sao gửi file dùng thread riêng?

**UI**
- 3 bước vẽ lại khi có tin đến. Vì sao cần `screen_lock`? Biến `buffer` để làm gì?
- Backspace hoạt động ra sao (`"\b \b"`)? Hạn chế của cách này?

**File**
- Tiến độ % tính thế nào? Kích thước khối? Vì sao không đọc cả file?
- File đứt giữa chừng xử lý ra sao? Lưu ở đâu? Trùng tên thì sao?

### 8.2 Kịch bản demo 10 phút (diễn tập ở D12, bấm giờ)

| Phút | Nội dung |
|---|---|
| 0:00–1:00 | Sơ đồ kiến trúc + thread model (1 trang) |
| 1:00–2:30 | Mở 2 máy: `/list`, thông báo online, `/status away` hiện bên kia |
| 2:30–5:00 | `/chat` hai chiều; máy/instance thứ 3 nhắn → thông báo unread; **gõ dở khi tin tới** |
| 5:00–7:00 | `/send` file lớn có tiến độ, **vẫn chat trong lúc gửi**; mở file đã nhận kiểm tra |
| 7:00–8:30 | Lỗi: tắt đột ngột 1 peer → thông báo offline; `/chat` người offline; `/send` file không tồn tại; lệnh sai |
| 8:30–9:30 | Ảnh Wireshark: UDP broadcast + TCP 3-way handshake |
| 9:30–10:00 | Dự phòng / hỏi đáp |

Chuẩn bị sẵn: 2 máy cùng mạng đã thử, file demo (vài MB), danh sách lệnh, **bản dự phòng chạy trên 1 máy** nếu mạng sự cố.

---

## 9. Test matrix lỗi (Ngọc chạy ở D10; đánh dấu Đạt/Lỗi)

| # | Tình huống | Kết quả mong đợi |
|---|---|---|
| 1 | Peer thoát bằng `/quit` | Bên kia báo ngắt kết nối + offline, quay về prompt |
| 2 | Peer bị tắt đột ngột (đóng cửa sổ/rút mạng) | Báo lỗi, không crash; hết hạn 10 s thì offline |
| 3 | `/chat` tới người vừa offline | Báo lỗi (timeout/refused), không crash |
| 4 | `/chat` tên không tồn tại / số ngoài phạm vi | Báo lỗi rõ ràng |
| 5 | `/send` file không tồn tại | Báo lỗi, không gửi gì |
| 6 | Ngắt giữa lúc gửi/nhận file | Báo lỗi, **xoá file dở** ở bên nhận |
| 7 | `/send` khi chưa `/chat` ai | Nhắc chọn partner |
| 8 | Lệnh sai / thiếu tham số | Hiện help ngắn |
| 9 | Nhận tin từ người không phải partner | Thông báo + đếm unread; mở `/chat` thì thấy tin cũ |
| 10 | Tin có tiếng Việt, emoji, dòng rất dài, chứa `\|` | Hiển thị đúng, không lệch frame |
| 11 | Hai instance trùng `--name` | Cảnh báo hoặc từ chối rõ ràng |
| 12 | `/chat` với chính mình | Từ chối |
| 13 | Gửi file lớn trong lúc chat hai chiều | Chat không đứng; hash trước/sau trùng nhau |
| 14 | Tin tới trong lúc đang gõ dở | Chữ đang gõ giữ nguyên |

---

## 10. Rủi ro & phương án dự phòng

| Rủi ro | Mức | Phòng ngừa / dự phòng |
|---|---|---|
| Mạng trường chặn broadcast/P2P (client isolation) | **Cao** | Test 2 máy từ D6; demo bằng hotspot điện thoại; có bản demo 1 máy |
| Firewall Windows chặn | Cao | Cho phép Python, đặt mạng Private, ghi vào README |
| Treo do deadlock lock | Cao | Quy tắc lock (mục 3 #6); review chéo; mô tả trong report |
| UI vỡ (option B) | Trung bình | Dự phòng sang Option A ở D8 nếu vẫn lỗi |
| Chỉ một người hiểu một module | **Cao (vấn đáp)** | Teach-back, mock vấn đáp D11–D12 |
| Trễ lịch do bài môn khác | Trung bình | Báo ngày bận ở D0; D13 là đệm; cắt "Could" |
| Dồn việc cuối | Trung bình | Freeze D11, họp ngắn 10–15 phút mỗi tối |

**Phân loại phạm vi** — *Must:* mọi hạng mục trong rubric. *Should:* replay lịch sử khi `/chat`, xử lý trùng tên file, `--bcast`. *Could (cắt nếu trễ):* màu sắc, lịch sử lệnh/mũi tên, GUI, mã hoá, hash trong protocol.

---

## 11. Gói nộp & dàn ý report

**Gói nộp:** source (chạy được từ thư mục sạch) · README (cài đặt, chạy 1 máy, chạy 2 máy, lưu ý firewall, danh sách lệnh) · report PDF 5–10 trang · ảnh Wireshark (UDP broadcast + TCP handshake, có chú thích) · chuẩn bị demo.

**Dàn ý report (≈ 5–10 trang):**
1. Giới thiệu & mục tiêu (0.5 trang)
2. Kiến trúc tổng thể + sơ đồ (1)
3. Thread model — bảng thread, chờ gì, làm gì, dữ liệu chung + lock (1)
4. Giao thức: UDP `HELLO`, TCP `HI/MSG/FILE/BYE`, vì sao có framing (1.5)
5. Chi tiết module: discovery, chat, file transfer, UI (2–3)
6. Wireshark: ảnh + giải thích (1–1.5)
7. Vấn đề gặp & cách giải quyết (1) — dùng chính các bẫy ở mục 7
8. Hướng dẫn test, hạn chế còn lại (0.5)

Mỗi người viết phần của module mình; Ngọc ghép và thống nhất văn phong.

---

## 12. Dùng trợ giúp từ Claude đúng cách (theo yêu cầu "tự code")

Phù hợp: giải thích khái niệm, giải thích traceback, đặt câu hỏi vấn đáp thử, chỉ ra điểm đáng ngờ trong code **do nhóm viết** (không viết lại hộ). Không phù hợp: nhờ viết hộ module rồi chép.
