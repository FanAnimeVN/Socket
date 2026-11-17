# Socket

Đồ án socket mạng máy tính — **LAN Chat & File Sharing** (command-line, Python, TCP + UDP).

- **UDP**: phát hiện người dùng trong mạng LAN (broadcast mỗi 3 giây) + trạng thái online/away.
- **TCP**: chat và gửi file giữa các peer, mỗi kết nối có thread nhận riêng.
- **Giao diện console**: tin nhắn đến không phá dòng đang gõ.

**Nhóm:** Lê Nhật Huy · Trần Nguyễn Hồng Ngọc · Trịnh Minh Phong

> ⚠️ Repo này hiện là **bộ khung**: mỗi file có ghi chú chức năng + việc cần làm + bẫy cần tránh,
> phần code các thành viên **tự viết** (đồ án vấn đáp từng chức năng). Hàm chưa viết sẽ ném
> `NotImplementedError("TODO: ...")` để biết chỗ nào còn thiếu.

## Cấu trúc thư mục

```
Socket/
├─ lanchat.py        Chương trình chính: tham số, khởi động thread, xử lý lệnh      (Huy - lead)
├─ config.py         Hằng số dùng chung (cổng, chu kỳ, timeout...)                   (cả nhóm)
├─ state.py          Dữ liệu dùng chung giữa các thread + lock                       (cả nhóm)
├─ protocol.py       Đóng/mở gói tin TCP: framing HI/MSG/FILE/BYE                    (Huy)
├─ tcp_chat.py       Acceptor, receiver, /chat, /leave, gửi tin, unread              (Huy)
├─ discovery.py      UDP broadcaster + listener, danh sách online, /status           (Ngọc)
├─ ui.py             Dòng nhập ở cuối, in tin phía trên, đọc từng phím               (Phong)
├─ filetransfer.py   Gửi/nhận file, tiến độ %, thư mục downloads/                    (Phong)
├─ downloads/        File nhận được
├─ exercises/        Bài tập Milestone 1 (TCP echo, UDP send/recv) - cả 3 người tự làm
├─ tests/            Test tự động cho protocol.py (socketpair, không cần mạng)
└─ docs/
   ├─ KE_HOACH.md    Kế hoạch 13 ngày, phân công, bẫy kỹ thuật, ngân hàng câu vấn đáp, kịch bản demo
   ├─ PROTOCOL.md    Thiết kế giao thức (cả nhóm chốt, code phải khớp)
   ├─ WIRESHARK.md   Hướng dẫn chụp UDP broadcast + TCP 3-way handshake
   └─ NHAT_KY.md     Nhật ký lỗi gặp phải (nguyên liệu cho báo cáo)
```

## Bắt đầu từ đâu (theo thứ tự)

1. Đọc `docs/KE_HOACH.md` (mục 0-5) và chốt `docs/PROTOCOL.md` cùng nhau (Day 0).
2. **Mỗi người** tự làm 4 bài trong `exercises/` (Day 1-2) → Milestone 1.
3. Mỗi người mở file module của mình, đọc docstring ở đầu file rồi từng hàm, và viết lần lượt từng hàm.
   Thứ tự gợi ý: `protocol.py` → `tests/test_protocol.py` (Huy); `discovery.py` (Ngọc); `ui.py` (Phong).
4. Tích hợp ở `lanchat.py` (Day 6), rồi tới chat TCP hoàn chỉnh, gửi file, xử lý lỗi.

## Cài đặt & chạy

Yêu cầu: **Python 3.10+** (chỉ dùng thư viện chuẩn, không cần `pip install`). *TODO: nhóm ghi lại phiên bản Python đang dùng.*

```bash
# Một máy, nhiều instance (mỗi instance: tên khác nhau + cổng TCP khác nhau)
python lanchat.py --name Huy  --port 5001
python lanchat.py --name Ngoc --port 5002
python lanchat.py --name Phong --port 5003
```

Hai máy cùng mạng: chạy lệnh tương tự trên mỗi máy với `--name` khác nhau.
*TODO: ghi chú cách chạy khi phải đổi địa chỉ broadcast (`--bcast`).*

### Lưu ý mạng (rủi ro lớn nhất khi demo)
- **Windows Firewall**: cho phép Python truy cập mạng Private; đặt mạng đang dùng là *Private*, nếu không gói bị chặn.
- **Wi-Fi trường / ký túc xá** thường bật *client isolation* (các máy không thấy nhau). Demo bằng hotspot điện thoại hoặc router riêng.
- Test trên 2 máy thật **sớm** (xem lịch Day 6), đừng để sát ngày nộp.

## Lệnh trong chương trình

| Lệnh | Mô tả |
|---|---|
| `/list` | Hiện người online (số, tên, IP, trạng thái) |
| `/chat <tên\|số>` | Mở chat với người đó (kết nối TCP) |
| `<văn bản>` | Gửi tin cho người đang chat |
| `/send <file>` | Gửi file cho người đang chat |
| `/leave` | Đóng chat hiện tại |
| `/status <online\|away>` | Đổi trạng thái |
| `/help` | Liệt kê lệnh |
| `/quit` | Thoát |

## Kiểm thử

```bash
python -m unittest -v tests.test_protocol     # test framing, không cần mạng
```
*TODO: bổ sung cách test 1 máy / 2 máy và bảng test lỗi (xem `docs/KE_HOACH.md`, mục 9).*

## Tiến độ (tick khi xong)

- [ ] **M1** TCP echo + UDP send/recv (`exercises/`)
- [ ] **M2** UDP discovery, `/list`, `/status` — peer hiện/mất trên 2+ máy
- [ ] **M3** TCP chat hai chiều: `/chat`, `/leave`, framing, nhiều peer, unread
- [ ] **M4** Typing-while-receiving UI + gửi file có tiến độ trong lúc chat
- [ ] **M5** Xử lý lỗi, test, báo cáo, Wireshark, demo 2 máy

## Làm việc nhóm với Git (cho người mới)

Mỗi người **sở hữu file riêng** (xem bảng cấu trúc) nên hiếm khi bị xung đột. Quy trình mỗi lần làm việc:

```bash
git pull                              # 1. luôn lấy bản mới nhất TRƯỚC khi sửa
# ... viết code, chạy thử ...
git add <các file bạn đã sửa>         # 2. thêm đúng file của mình (tránh "git add ." khi chưa xem lại)
git commit -m "discovery: parse HELLO"   # 3. thông điệp ngắn, nói rõ làm gì
git pull                              # 4. lấy thay đổi của bạn bè (nếu có)
git push                              # 5. đẩy lên GitHub
```

- Commit nhỏ, thường xuyên (mỗi hàm chạy được là một commit).
- Muốn sửa file của người khác? Nhắn họ trước.
- Gặp "conflict": đừng hoảng, nhắn nhóm, mở file thấy `<<<<<<<` và sửa tay; không chắc thì hỏi.
