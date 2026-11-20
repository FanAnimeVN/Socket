# Socket — LAN Chat & File Sharing

Đồ án socket mạng máy tính: ứng dụng chat và gửi file trong mạng LAN, chạy trên console, viết bằng Python
(**chỉ thư viện chuẩn, không cần `pip install`**).

- **UDP**: tự phát hiện người dùng trong mạng LAN (broadcast mỗi 3 giây), trạng thái online/away, báo ai vào/ra.
- **TCP**: chat nhiều người (tin của người khác thành "unread") và gửi file có tiến độ %, mỗi kết nối một thread nhận.
- **Console**: tin nhắn đến lúc đang gõ dở không phá dòng đang gõ.

**Nhóm:** Lê Nhật Huy · Trần Nguyễn Hồng Ngọc · Trịnh Minh Phong

## Tình trạng hiện tại

| Hạng mục | Tình trạng |
|---|---|
| Chương trình (UDP, chat TCP, gửi file, UI, xử lý lỗi) | **Đã xong**, chạy được; 61 test tự động đều đạt (xem `docs/evidence/test_results.txt`) |
| Báo cáo kỹ thuật, không có code, kèm 9 hình | **Bản đầy đủ**: [`docs/BAO_CAO.md`](docs/BAO_CAO.md) — nhóm đọc lại, bổ sung rồi xuất PDF |
| Minh chứng chạy thật (phiên chat, byte trên dây, console thật) | **Đã có** trong `docs/evidence/` |
| Test trên **2 máy thật** (tường lửa, Wi-Fi) | **Chưa làm — nhóm phải làm** (xem mục "Chạy trên 2 máy") |
| Ảnh **Wireshark** (UDP broadcast + bắt tay 3 bước TCP) | **Chưa có — nhóm phải chụp** trên 2 máy thật, làm theo `docs/WIRESHARK.md` |
| Demo trực tiếp 10 phút trên ≥ 2 máy | Nhóm diễn tập theo kịch bản trong `docs/KE_HOACH.md` mục 8.2 |

## Cấu trúc thư mục

Cấu trúc **phẳng**: mỗi file một việc, chạy được ngay `python lanchat.py` từ thư mục gốc. Không file nào quá 300 dòng.

```
Socket/
├─ lanchat.py        Chương trình chính: tham số, khởi động thread, bảng lệnh
├─ config.py         Hằng số dùng chung (cổng, chu kỳ 3 giây, timeout 10 giây...)
├─ state.py          Dữ liệu dùng chung giữa các thread + lock (người online, kết nối, unread)
├─ protocol.py       Khung tin TCP: HI / MSG / FILE / BYE, đọc đúng N byte
├─ discovery.py      UDP: phát/nghe HELLO, danh sách online, /status
├─ tcp_chat.py       TCP chat: acceptor, thread nhận tin, /chat, gửi tin, /leave
├─ filetransfer.py   Gửi/nhận file, tiến độ %, thư mục downloads/
├─ ui.py             Dòng nhập ở cuối, in tin phía trên, đọc từng phím
├─ downloads/        File nhận được
├─ exercises/        Bài tập Milestone 1 (TCP echo, UDP gửi/nhận) - chạy được
├─ tests/            Test tự động + công cụ dựng minh chứng
└─ docs/
   ├─ BAO_CAO.md              Báo cáo kỹ thuật (không có code) kèm hình và minh chứng
   ├─ HUONG_DAN_DOC_CODE.md   Thứ tự đọc code + luồng từng chức năng (ĐỌC ĐẦU TIÊN)
   ├─ PROTOCOL.md             Đặc tả giao thức
   ├─ WIRESHARK.md            Hướng dẫn chụp UDP broadcast + TCP 3-way handshake
   ├─ KE_HOACH.md             Kế hoạch, phân công, ngân hàng câu vấn đáp, kịch bản demo
   ├─ NHAT_KY.md              Nhật ký vấn đề đã gặp và thí nghiệm
   ├─ img/                    Hình dùng trong báo cáo (sơ đồ + hình dựng từ log thật)
   └─ evidence/               Log chạy thật: kết quả test, phiên chat, byte trên dây, console thật
```

Mỗi file Python mở đầu bằng khung chú thích: **việc của file / luồng chạy / bẫy hay gặp / đọc tiếp ở đâu**.
Người mới nên đọc theo `docs/HUONG_DAN_DOC_CODE.md`. Luật giữ cho dự án dễ đọc nằm ở `CLAUDE.md`.

## Cài đặt

Chỉ cần **Python 3.8+** (đã chạy thử trên 3.11.9). Không cần cài thư viện nào.

```
python --version
```

Nếu báo "Python was not found": cài từ python.org và tick ô **Add python.exe to PATH**.

## Chạy

**Một máy, nhiều chương trình** (mỗi chương trình: tên khác nhau + cổng TCP khác nhau), mỗi dòng ở một cửa sổ:

```
python lanchat.py --name Huy   --port 5001
python lanchat.py --name Ngoc  --port 5002
python lanchat.py --name Phong --port 5003
```

Mỗi lần khởi động mất khoảng 3,5 giây vì chương trình nghe xem tên đã có ai dùng chưa (trùng tên sẽ bị từ chối).
Máy **không có mạng** (offline): thêm `--bcast 127.255.255.255` vào cả ba lệnh.

| Tham số | Ý nghĩa |
|---|---|
| `--name` | Tên hiển thị, bắt buộc, duy nhất, không dấu cách, không có `\|`, tối đa 20 ký tự |
| `--port` | Cổng TCP của mình (mặc định 5000) |
| `--bcast` | Địa chỉ broadcast UDP (mặc định 255.255.255.255) |

### Chạy trên 2 máy (rủi ro lớn nhất khi demo — thử SỚM)

1. Hai máy cùng một mạng (nên dùng **hotspot điện thoại** hoặc router riêng).
2. Mỗi máy chạy `python lanchat.py --name <tên khác nhau>`; không cần `--port` vì hai máy khác nhau.
3. Vài giây sau mỗi máy phải thấy `[*] <tên kia> is online`. Gõ `/list`, `/chat <tên>`, rồi chat.

Nếu **không thấy nhau**:
- **Windows Firewall**: lần đầu chạy Windows hỏi quyền → bấm **Allow** cho mạng **Private**; và đặt mạng đang dùng là *Private*.
- **Wi-Fi trường / ký túc xá** thường bật *client isolation* (các máy không thấy nhau) → dùng hotspot điện thoại.
- Máy có nhiều card mạng (VPN, WSL, Hyper-V): thêm `--bcast <địa chỉ broadcast của mạng>`, ví dụ `--bcast 192.168.1.255`
  (mạng 192.168.1.x). Xem địa chỉ IP bằng lệnh `ipconfig`.

## Lệnh trong chương trình

| Lệnh | Mô tả |
|---|---|
| `/list` | Hiện người online (số, tên, IP, trạng thái, số tin chưa đọc) |
| `/chat <tên\|số>` | Mở chat với người đó (kết nối TCP); chuyển người khác không đóng kết nối cũ |
| `<văn bản>` | Gửi tin cho người đang chat |
| `/send <file>` | Gửi file cho người đang chat (đường dẫn có dấu cách cũng được) |
| `/leave` | Đóng chat hiện tại |
| `/status <online\|away>` | Đổi trạng thái (gửi qua UDP) |
| `/help` | Liệt kê lệnh |
| `/quit` | Thoát |

Ví dụ phiên chạy thật: `docs/evidence/session_TestA.txt`. File nhận được nằm trong `downloads/`.

## Kiểm thử

```
python -m unittest discover -s tests -t . -v
```

Lệnh trên chạy 61 test: giao thức, gói HELLO, kho dữ liệu, tên file an toàn, nhận file đứt giữa chừng, vẽ lại dòng nhập,
các luật tổ chức dự án, và **4 test chạy chương trình thật** (cần UDP cổng 9999 rảnh; ~25 giây). Chỉ chạy phần không cần mạng:

```
set SKIP_NETWORK_TESTS=1
python -m unittest discover -s tests -t . -v
```

Lưu lại minh chứng mới (log, byte trên dây) rồi dựng lại hình trong báo cáo:

```
set SAVE_EVIDENCE_TO=docs/evidence
python -m unittest discover -s tests -t .
python tests/manual_console_check.py
python tests/make_terminal_figures.py
```

`tests/manual_console_check.py` (chỉ Windows) bơm phím thật vào một console thật để kiểm tra "gõ dở mà tin vẫn đến".

**Kiểm thử bằng tay trên 2 máy thật** (nhóm làm, ghi kết quả vào `docs/NHAT_KY.md`): bảng 14 tình huống lỗi ở
`docs/KE_HOACH.md` mục 9; riêng gửi file nên so mã băm bằng `certutil -hashfile <file> SHA256`.

## Sản phẩm cần nộp (đối chiếu mục 7 của đề)

| Sản phẩm | Nơi có | Tình trạng |
|---|---|---|
| Source code + README (cài đặt, chạy, test) | repo này | Xong |
| Báo cáo 5–10 trang: kiến trúc, mô hình thread, giao thức, khó khăn và giải pháp | `docs/BAO_CAO.md` | Bản đầy đủ; cần nhóm đọc lại, thêm ảnh Wireshark rồi xuất PDF |
| Ảnh Wireshark: UDP broadcast + bắt tay 3 bước TCP, kèm giải thích | `docs/WIRESHARK.md` hướng dẫn | **Nhóm chụp** (cần 2 máy thật) |
| Demo trực tiếp 10 phút, ≥ 2 máy | `docs/KE_HOACH.md` mục 8.2 | Nhóm diễn tập (đề yêu cầu demo trực tiếp, không phải video) |

## Tiến độ

- [x] **M1** TCP echo + UDP gửi/nhận (`exercises/`)
- [x] **M2** UDP discovery, `/list`, `/status` — đã chạy nhiều chương trình trên 1 máy; **2 máy thật: chưa thử**
- [x] **M3** TCP chat hai chiều, `/leave`, nhiều người, unread
- [x] **M4** Gõ dở mà tin vẫn đến; gửi file có tiến độ trong lúc chat
- [ ] **M5** Xử lý lỗi và test đã xong; **còn: test 2 máy thật, ảnh Wireshark, đọc lại báo cáo, diễn tập demo**

## Hạn chế đã biết

Dòng gõ dài hơn bề rộng cửa sổ, emoji (ký tự rộng) và phím mũi tên/Home/End chưa hỗ trợ; nhánh đọc phím Linux/macOS chưa chạy
thử; "Done" khi gửi file nghĩa là đã đưa hết byte cho TCP. Danh sách đầy đủ: `docs/BAO_CAO.md` mục 9.

## Làm việc nhóm với Git (cho người mới)

```
git pull                                 # 1. luôn lấy bản mới nhất TRƯỚC khi sửa
git add <các file bạn đã sửa>            # 2. thêm đúng file của mình (tránh "git add ." khi chưa xem lại)
git commit -m "discovery: sửa thông báo"  # 3. thông điệp ngắn, nói rõ làm gì
git pull                                 # 4. lấy thay đổi của bạn bè (nếu có)
git push                                 # 5. đẩy lên GitHub
```

Commit nhỏ, thường xuyên. Muốn sửa file của người khác thì nhắn họ trước. Gặp "conflict": đừng hoảng, mở file thấy
`<<<<<<<` và sửa tay; không chắc thì hỏi nhóm.
