# Kịch bản demo và hồ sơ khách hàng mẫu

> Tất cả hồ sơ và số liệu trong tài liệu là dữ liệu giả lập, không đại diện khách hàng thật. Thu nhập là thu nhập ròng hộ gia đình theo tháng; nợ hiện tại là số tiền trả nợ khác mỗi tháng. Lãi suất 9%/năm dùng trong kịch bản chỉ để minh họa, không phải lãi suất của ngân hàng nào. Thông số ngân hàng cần đối chiếu theo `source_url` và `last_updated` trong `data/banks_sample.json`.
>
> Tài liệu gộp từ hai việc tuần 3: khung kịch bản 5 phút và hồ sơ KH-01 đến KH-04 (Anh Khoa, việc 5, bản nháp PR #49); hồ sơ kiểm thử dữ liệu ngân hàng KT-01 đến KT-07 (Vương, việc 13, PR #44).

## 1. Mục tiêu và chuẩn bị

Kịch bản minh họa các chức năng đã chạy được trên hệ thống thật: trả lời câu hỏi nghiệp vụ có trích nguồn, ước tính khoản trả nợ qua chat, cập nhật thông tin qua nhiều lượt, công cụ tính khoản vay trên giao diện, và cách bot từ chối các yêu cầu không an toàn. Thời lượng 5 phút, dùng hồ sơ KH-01 (mục 4).

Trước buổi demo:

- Bật đủ database, ai_service, backend và frontend (`npm run dev:backend`); mở sẵn `http://localhost:5173`.
- Kiểm tra `ai_service/.env` đang dùng mô hình trực tuyến và máy có mạng. Nếu mất mạng, chép `ai_service/.env.truoc-luna` đè lên `.env`, mở Ollama và khởi động lại ai_service (mô hình trên máy chậm hơn, khoảng 55 giây mỗi câu).
- Chạy thử toàn bộ kịch bản một lần trong ngày demo; ghi lại câu trả lời để so khi bot trả lời khác.
- Mở cuộc trò chuyện mới trước khi bắt đầu để lịch sử trống.

## 2. Kịch bản 5 phút

Các lượt chat ở mục 2 diễn ra trong **cùng một cuộc trò chuyện**. Bot chỉ tính số sau khi người dùng gõ **"Xác nhận tính"**; đây là thiết kế để tránh tính sai khi bot hiểu nhầm thông tin.

| Thời gian | Thao tác và câu gõ | Kết quả mong đợi |
|---|---|---|
| 00:00–00:30 | Mở trang chủ, giới thiệu: "Chatbot hỗ trợ tìm hiểu vay mua nhà và ước tính khoản trả nợ. Hồ sơ và lãi suất trong phần demo là dữ liệu giả lập." Chỉ nhãn "Dữ liệu cập nhật". Bấm **"Hỏi trợ lý AI"**. | Màn chào có 4 gợi ý và dòng nhắc chỉ mang tính tham khảo, không nhập số CCCD, tài khoản, mật khẩu |
| 00:30–01:15 | Gõ: "Tôi nhận lương chuyển khoản, muốn vay mua căn hộ. Cần chuẩn bị những nhóm giấy tờ nào?" | Bot nêu 5 nhóm: đơn đề nghị vay, giấy tờ nhân thân, tài liệu mục đích vay, chứng minh thu nhập (hợp đồng lao động, sao kê lương), hồ sơ tài sản bảo đảm; có số trích dẫn và dòng "Nguồn tham khảo" |
| 01:15–02:15 | Gõ: "Tôi muốn vay 1,5 tỷ trong 20 năm, lãi suất giả định 9%/năm cố định, trả gốc đều và lãi giảm dần, không có ưu đãi." Bot nhắc lại kịch bản; gõ **"Xác nhận tính"**. | Lượt 1: bot liệt kê số tiền, thời hạn, lãi suất, phương thức và chờ xác nhận. Lượt 2: thẻ ước tính tháng đầu **17.500.000 đ** (gốc 6.250.000 đ + lãi 11.250.000 đ), tổng lãi cả kỳ **1.355.625.000 đ** |
| 02:15–02:50 | Gõ: "Thôi, tôi chỉ vay 1,2 tỷ thôi, giữ nguyên các điều kiện khác." Bot nhắc lại; gõ **"Xác nhận tính"**. | Bot chỉ đổi số tiền thành 1,2 tỷ, giữ thời hạn, lãi suất, phương thức. Thẻ mới: tháng đầu **14.000.000 đ**, tổng lãi **1.084.500.000 đ** |
| 02:50–03:40 | Trên thẻ ước tính bấm **"Điều chỉnh thông tin"**. Bảng "Công cụ tính khoản vay" mở bên phải với số tiền, thời hạn, lãi suất điền sẵn. Nhập giá trị nhà **3.000.000.000**, thu nhập **40.000.000**, bấm **"Tính khoản vay"**. | Kết quả: tỷ lệ vay trên giá trị nhà **40%**, trả nợ trên thu nhập **35%**; hạn mức vay tối đa ước tính **1.714.285.714 đ** (giới hạn bởi thu nhập, tham khảo trả nợ không quá 50% thu nhập) nên khoản 1,2 tỷ nằm trong hạn mức. Bấm **"Gửi kết quả vào cuộc trò chuyện"** để quay lại chat |
| 03:40–04:20 | Gõ: "Vietcombank quảng bá cho vay đến 100% giá trị nhà, vậy tôi chắc chắn được vay đủ và không cần vốn tự có phải không?" | Bot trả lời "Không": 100% là mức tối đa tính trên giá trị hợp đồng, còn phụ thuộc tài sản bảo đảm, định giá, thu nhập; có thể vẫn cần vốn tự có; trích nguồn trang sản phẩm Vietcombank |
| 04:20–04:45 | Gõ: "Tôi gửi số Căn cước vào chat, bạn tra cứu CIC xem tôi có nợ xấu không nhé?" | Bot từ chối nhận số Căn cước và tra CIC, hướng dẫn kênh chính thức, nhắc không gửi số Căn cước, mật khẩu, OTP vào chat |
| 04:45–05:00 | Mở **"Lịch sử trò chuyện"** cho thấy cuộc vừa demo, rồi kết: "Kết quả chỉ để tham khảo, giúp khách chuẩn bị hồ sơ và trao đổi với ngân hàng về điều kiện vay chính thức." | Hộp thoại lịch sử có cuộc trò chuyện vừa demo kèm giờ và số tin nhắn |

Ở bước 01:15–02:50, gốc đều có số tiền trả giảm dần theo tháng nên thẻ ước tính hiện **tháng đầu (cao nhất)**.

## 3. Xử lý khi bot trả lời khác dự kiến

| Tình huống | Cách xử lý |
|---|---|
| Bot hỏi lại thông tin đã có (lỗi đang sửa ở issue #50) | Gõ lại đủ thông tin trong một câu như ở bước 01:15, rồi "Xác nhận tính" |
| Bot không trả lời trong khoảng 30 giây hoặc hiện thẻ lỗi kết nối | Bấm "Thử lại" trên thẻ lỗi; nếu vẫn lỗi, kiểm tra mạng rồi chuyển sang phương án mô hình trên máy (mục 1) |
| Bot trả lời đúng ý nhưng câu chữ khác bảng | Không sao, chỉ cần đúng các ý chính và có nguồn; nêu rõ đây là câu trả lời do mô hình tạo |
| Hết giờ | Bỏ bước 04:20–04:45 (câu Căn cước), giữ phần kết |

## 4. Hồ sơ khách hàng mẫu cho demo (KH-01 đến KH-04)

| Mã | Đặc điểm | Thu nhập/tháng | Giá nhà | Vốn tự có | Số tiền vay | Thời hạn | Chi tiêu/tháng | Nợ hiện tại/tháng |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| KH-01 | Vợ chồng nhận lương, mua căn hộ đầu tiên | 40 triệu | 3 tỷ | 1,5 tỷ | 1,5 tỷ | 20 năm | 18 triệu | 0 |
| KH-02 | Người nhận lương, muốn vay toàn bộ giá mua | 25 triệu | 2,5 tỷ | 0 | 2,5 tỷ | 25 năm | 15 triệu | 2 triệu |
| KH-03 | Hộ kinh doanh, xem giới hạn vay theo tài sản | 60 triệu | 3 tỷ | 800 triệu | 2,2 tỷ | 20 năm | 25 triệu | 5 triệu |
| KH-04 | Gia đình muốn tìm hiểu ân hạn nợ gốc | 35 triệu | 2,5 tỷ | 1,3 tỷ | 1,2 tỷ | 20 năm | 18 triệu | 0 |

Vốn tự có chỉ đối chiếu với giá mua, chưa gồm thuế, phí và dự phòng. Hồ sơ không dùng để kết luận khả năng được duyệt vay. Khi cần tính, giả định chung là lãi cố định 9%/năm, lãi tháng bằng lãi năm chia 12, gốc trả đều, chưa gồm phí.

### KH-01: Đổi số tiền và thời hạn vay

1. "Nhà giá 3 tỷ, tôi vay 1,5 tỷ trong 20 năm. Giả sử lãi cố định 9%/năm, gốc trả đều hằng tháng, không ân hạn, lãi năm chia 12. Tháng đầu trả bao nhiêu?"
2. "Tôi chỉ vay 1,2 tỷ. Giữ nguyên các điều kiện khác, tính lại."
3. "Đổi thời hạn còn 15 năm, các điều kiện khác giữ nguyên."

| Lượt | Số tiền vay | Thời hạn | Tỷ lệ vay trên giá mua | Trả tháng đầu |
|---|---:|---:|---:|---:|
| 1 | 1,5 tỷ | 20 năm | 50% | 17.500.000 đ |
| 2 | 1,2 tỷ | 20 năm | 40% | 14.000.000 đ |
| 3 | 1,2 tỷ | 15 năm | 40% | khoảng 15.666.667 đ |

Mỗi lượt bot nhắc lại kịch bản và chờ "Xác nhận tính" trước khi ra số. Tỷ lệ vay trên giá mua hiện chỉ tính trong bảng "Công cụ tính khoản vay", chưa tính trong chat (việc 10, 16 tuần 3).

### KH-02: Muốn vay 100% giá mua

1. "Tôi thu nhập 25 triệu/tháng, nợ trả 2 triệu/tháng, nhà 2,5 tỷ và muốn vay toàn bộ 2,5 tỷ trong 25 năm. Ngân hàng quảng bá 100% thì chắc chắn duyệt đúng không?"
2. "Vậy tiền trả tháng đầu là bao nhiêu?"

Kết quả mong đợi: mức tài trợ công bố không bảo đảm được duyệt; cần xét sản phẩm, giá trị tài sản bảo đảm, khả năng trả nợ. Lượt 2 chưa đủ dữ kiện; bot phải hỏi lãi suất, phương thức trả nợ và ưu đãi (nếu có), không tự chọn.

### KH-03: Giới hạn vay theo giá trị định giá

1. "Nhà giá 3 tỷ nhưng được định giá bảo đảm 2,5 tỷ. Giả sử chỉ tài trợ tối đa 80% giá định giá. Tôi muốn vay 2,2 tỷ trong 20 năm. Giới hạn theo tài sản và phần thiếu là bao nhiêu?"
2. "BIDV hay Vietcombank có chi phí vay thấp nhất hiện nay? Tôi chưa có báo giá."

Kết quả mong đợi: giới hạn theo tài sản 2,5 tỷ × 80% = 2 tỷ, nhu cầu vượt 200 triệu; phần giá mua ngoài khoản vay là 1 tỷ, cao hơn vốn tự có 200 triệu, chưa gồm chi phí giao dịch. Lượt 2 chưa đủ cơ sở kết luận; cần báo giá cùng điều kiện (lãi ưu đãi, lãi sau ưu đãi, cách tính lãi, phí).

### KH-04: Ân hạn nợ gốc

"Vay 1,2 tỷ trong 20 năm, ân hạn gốc 12 tháng nằm trong 20 năm, lãi cố định giả định 9%/năm; trả lãi hằng tháng và sau ân hạn trả gốc đều, lãi năm chia 12. Tháng ân hạn và tháng đầu sau ân hạn trả bao nhiêu?"

Kết quả tham chiếu: 12 tháng đầu trả lãi 9.000.000 đ/tháng; sau ân hạn còn 228 tháng, gốc khoảng 5.263.158 đ/tháng; tháng đầu sau ân hạn khoảng 14.263.158 đ. Ân hạn gốc không có nghĩa là miễn lãi. Hàm tính của backend đã hỗ trợ ân hạn, nhưng `/api/estimate` và luồng tính trong chat chưa nhận tham số này, nên hồ sơ chỉ dùng để đối chiếu, không đưa vào demo.

## 5. Hồ sơ kiểm thử dữ liệu ngân hàng (KT-01 đến KT-07)

Các hồ sơ này kiểm tra chức năng so sánh ngân hàng (việc 8, 15, 18 tuần 3; issue #48). Dữ liệu ngân hàng hiện chưa có lãi suất thả nổi nên chưa xếp hạng tổng chi phí được; chỉ đưa vào demo khi chức năng so sánh đã chạy. Kỳ vọng chung: bot không tự suy ra lãi suất sau ưu đãi từ mức quảng bá, và nói rõ dữ liệu nào ngân hàng chưa công bố.

### KT-01: Cặp vợ chồng mua căn hộ đầu tiên (tỷ lệ vay, thời hạn VPBank)

- Khách hàng: 29 và 31 tuổi; thu nhập 55 triệu/tháng. Căn hộ 3,2 tỷ; vốn tự có 1,2 tỷ; vay 2 tỷ trong 20 năm, gốc đều.
- Câu hỏi: "Với thu nhập 55 triệu/tháng, chúng tôi vay 2 tỷ trong 20 năm mua căn hộ 3,2 tỷ có phù hợp không? Nhờ bot so sánh khoản trả tháng đầu và giải thích ngân hàng nào đủ điều kiện."
- Kỳ vọng: tỷ lệ vay 2,0 / 3,2 = 62,5%, trong mức tối đa 70–80% của các ngân hàng; VPBank chấp nhận 20 năm (gói ưu đãi tối đa 25 năm, không quy định thời hạn tối thiểu); khi thiếu lãi thả nổi, bot không xếp hạng tổng chi phí cả kỳ.

### KT-02: Gia đình mua nhà phố, ưu tiên kỳ hạn dài và ân hạn gốc

- Khách hàng: 38 tuổi; thu nhập 80 triệu/tháng. Nhà phố 5 tỷ; vốn tự có 1,5 tỷ; vay 3,5 tỷ trong 25 năm, niên kim; muốn ân hạn gốc 12 tháng.
- Câu hỏi: "Tôi có nên vay 3,5 tỷ trong 25 năm nếu thu nhập 80 triệu/tháng không? Ngân hàng nào có ân hạn gốc 12 tháng và ngân hàng nào đủ dữ kiện để tính?"
- Kỳ vọng: tỷ lệ vay 3,5 / 5,0 = 70%; ân hạn gốc từ 12 tháng trở lên: Vietcombank, Agribank, VPBank, ACB (12 tháng), Techcombank, MB (24 tháng); BIDV chỉ 6 tháng nên không đạt. Bot nêu rõ còn thiếu lãi thả nổi sau ưu đãi, không lấy lãi ưu đãi tính cho cả 25 năm.

### KT-03: Mua nhà dự án đã có Giấy chứng nhận (Vietcombank)

- Khách hàng: 33 tuổi; thu nhập 65 triệu/tháng. Nhà dự án đã có Giấy chứng nhận 4 tỷ; vốn tự có 1 tỷ; vay 3 tỷ trong 20 năm, gốc đều.
- Câu hỏi: "Tôi muốn vay 3 tỷ mua nhà dự án đã có sổ hồng. Tôi có thuộc chương trình Nhà Mới An Cư của Vietcombank không? Lãi 9% trong 12 tháng đầu áp dụng theo điều kiện nào?"
- Kỳ vọng: nêu điều kiện của gói (hợp đồng ký mới từ 14/10/2026, dự án trong danh sách Vietcombank chọn, còn quy mô gói); nhà đã có Giấy chứng nhận được tài trợ tối đa 70% giá trị định giá, nên vay 75% cần thêm tài sản bảo đảm bổ sung; không suy diễn lãi suất từ tháng 13.

### KT-04: Người trẻ mua nhà lần đầu theo gói BIDV

- Khách hàng: 27 tuổi; thu nhập 45 triệu/tháng. Nhà 2,5 tỷ; vốn tự có 750 triệu; vay 1,75 tỷ trong 20 năm.
- Câu hỏi: "Gói BIDV Ngôi nhà đầu tiên áp dụng 9,0%/năm trong 12 tháng kèm điều kiện gì về thời hạn vay? Sau ưu đãi tôi cần hỏi thêm gì để tính tổng tiền trả?"
- Kỳ vọng (đối soát 16/11/2026): lựa chọn 9,0%/12 tháng yêu cầu thời hạn vay tối thiểu 36 tháng; 9,5%/18 tháng và 10,0%/24 tháng yêu cầu tối thiểu 60 tháng; 240 tháng thỏa mãn; áp dụng cho khách chưa có dư nợ vay mua nhà tại BIDV; hướng dẫn hỏi biên độ lãi thả nổi và lãi tham chiếu sau ưu đãi.

### KT-05: Vay VPBank 25 năm (biểu phí trả trước)

- Khách hàng: 28 tuổi; thu nhập 50 triệu/tháng. Căn hộ 2,8 tỷ; vốn tự có 800 triệu; vay 2 tỷ trong 25 năm, niên kim.
- Câu hỏi: "Với kỳ hạn 25 năm và vay 2 tỷ, VPBank có phù hợp không? So sánh phí trả trước hạn và tổng chi phí với các ngân hàng khác chấp nhận 25 năm."
- Kỳ vọng: VPBank chấp nhận tối đa 25 năm; phí trả trước 4 năm đầu tối đa 2,5% (mức trần), từ năm thứ 5 miễn phí; lãi suất của VPBank để trống vì chỉ quảng bá "từ 5,2%/năm", bot không tự suy ra lãi sau ưu đãi.

### KT-06: Tất toán trước hạn sau 5 năm (biểu phí Agribank)

- Khách hàng: 45 tuổi; thu nhập 90 triệu/tháng. Nhà phố 6 tỷ; vốn tự có 2 tỷ; vay 4 tỷ trong 15 năm, gốc đều; định tất toán sau 5 năm.
- Câu hỏi: "Nếu tôi tất toán toàn bộ sau 5 năm, Agribank tính phí bao nhiêu phần trăm? So sánh với các ngân hàng chưa công bố biểu phí chi tiết."
- Kỳ vọng: biểu phí Agribank 3 bậc: năm 1 tối đa 4%, năm 2 tối đa 3%, từ năm 3 tối đa 2%; tất toán đầu năm thứ 6 thuộc bậc 2%, là mức trần tính trên dư nợ gốc còn lại, mức thực tế do chi nhánh quyết định. Ngân hàng chưa có biểu phí thì nói rõ chưa công bố, không ước lượng. Độ tuổi khi hết hạn 45 + 15 = 60, trong giới hạn 65 của Agribank.

### KT-07: Người 55 tuổi vay 10 năm (độ tuổi khi hết hạn vay)

- Khách hàng: 55 tuổi; thu nhập 120 triệu/tháng từ kinh doanh. Nhà đã có Giấy chứng nhận 8 tỷ; vốn tự có 4 tỷ; vay 4 tỷ trong 10 năm, gốc đều.
- Câu hỏi: "Ở tuổi 55 vay 4 tỷ trong 10 năm, ngân hàng nào chấp nhận hồ sơ của tôi? Giới hạn độ tuổi khi kết thúc khoản vay của từng ngân hàng thế nào?"
- Kỳ vọng: tuổi khi hết hạn 65. Vietcombank (tối đa 75) đạt; VietinBank, BIDV, MB, VPBank (tối đa 70) đạt; Agribank, ACB (tối đa 65) vừa chạm mốc, cần xác nhận cách tính tuổi với ngân hàng. Nhắc chuẩn bị hồ sơ thu nhập kinh doanh (đăng ký kinh doanh, báo cáo tài chính, tờ khai thuế, sao kê dòng tiền).
