# BÁO CÁO NGHIỆP VỤ CHATBOT TƯ VẤN VAY MUA NHÀ

## 1. Bài toán

Thông tin về vay mua nhà bao gồm nhiều nội dung như điều kiện cấp tín dụng, hồ sơ, hạn mức, thời hạn, lãi suất, phí và bảo hiểm. Các nội dung này được công bố theo từng ngân hàng và sản phẩm, đồng thời có thể thay đổi theo thời điểm. Việc tiếp cận thông tin từ nhiều nguồn làm phát sinh khó khăn trong quá trình tổng hợp, so sánh và xác định phương án vay phù hợp.

Chatbot tư vấn vay mua nhà được xây dựng nhằm hỗ trợ người dùng tra cứu thông tin bằng tiếng Việt, giải thích các khái niệm nghiệp vụ và mô phỏng khoản trả nợ theo dữ liệu được cung cấp. Thông qua đó, hệ thống hỗ trợ người dùng chuẩn bị thông tin và hồ sơ trước khi làm việc với ngân hàng.

## 2. Đối tượng và phạm vi tư vấn

Đối tượng sử dụng là cá nhân có nhu cầu tìm hiểu khoản vay mua nhà tại Việt Nam. Phạm vi dữ liệu gồm hai phần:

- **Kho tri thức để trả lời câu hỏi** (60 câu hỏi thường gặp và tài liệu quy trình vay): dựa trên văn bản pháp luật và trang sản phẩm của Vietcombank, BIDV, Techcombank.
- **Dữ liệu sản phẩm có cấu trúc** dùng cho công cụ tính và so sánh: 8 ngân hàng Vietcombank, BIDV, Techcombank, VietinBank, Agribank, MB, VPBank, ACB. Thông tin ngân hàng không công bố (ví dụ lãi suất sau ưu đãi) được để trống, không ước lượng.

| Nhóm nội dung | Phạm vi tư vấn |
|---|---|
| Điều kiện vay | Giải thích điều kiện chung và yêu cầu của từng sản phẩm theo nguồn dữ liệu |
| Hồ sơ vay | Hướng dẫn các nhóm giấy tờ về nhân thân, mục đích vay, nguồn trả nợ và tài sản bảo đảm |
| Hạn mức và thời hạn | Giải thích giới hạn sản phẩm; phân biệt giá mua với giá trị tài sản được thẩm định |
| Lãi suất và chi phí | Giải thích lãi suất ưu đãi, lãi suất điều chỉnh, phí trả trước hạn và bảo hiểm liên quan |
| Quy trình vay | Trình bày các bước từ chuẩn bị hồ sơ đến tất toán |
| So sánh sản phẩm | Đối chiếu các tiêu chí tương đương trên cơ sở nguồn và thời điểm công bố |
| Mô phỏng khoản vay | Ước tính khoản trả nợ theo số tiền vay, thời hạn, lãi suất và phương thức trả nợ được xác định |
| Hội thoại nhiều lượt | Tiếp nhận thông tin bổ sung, cập nhật số tiền hoặc thời hạn vay theo yêu cầu của người dùng |

Các nội dung phê duyệt tín dụng, xác định xác suất được vay, tra cứu CIC cá nhân, tiếp nhận thông tin xác thực ngân hàng, nộp hồ sơ và giải ngân thay khách hàng nằm ngoài phạm vi của hệ thống.

## 3. Quy trình vay và quy trình tư vấn

### 3.1. Quy trình vay mua nhà

Quy trình vay mua nhà được khái quát thành 5 giai đoạn, triển khai thành 9 bước:

| Giai đoạn | Các bước |
|---|---|
| 1. Chuẩn bị và đăng ký hồ sơ vay | Bước 1. Xác định nhu cầu và đánh giá điều kiện ban đầu; Bước 2. Chuẩn bị bộ hồ sơ vay vốn (nhân thân, mục đích sử dụng vốn, nguồn trả nợ, tài sản bảo đảm); Bước 3. Nộp hồ sơ và đăng ký vay vốn |
| 2. Tiếp nhận và thẩm định khoản vay | Bước 4. Thẩm định tín dụng và định giá tài sản bảo đảm |
| 3. Phê duyệt và thông báo kết quả | Bước 5. Phê duyệt tín dụng và thông báo kết quả |
| 4. Ký kết, hoàn thiện thủ tục bảo đảm và giải ngân | Bước 6. Ký hợp đồng và đăng ký biện pháp bảo đảm; Bước 7. Hoàn tất điều kiện trước giải ngân và giải ngân |
| 5. Trả nợ, theo dõi sau giải ngân và tất toán | Bước 8. Trả nợ định kỳ và theo dõi lãi suất; Bước 9. Trả nợ trước hạn hoặc tất toán và giải chấp tài sản |

Cách phân chia này phục vụ hệ thống hóa nghiệp vụ, không phải quy trình bắt buộc giống nhau ở mọi ngân hàng.

Nội dung chi tiết được trình bày trong [Tài liệu quy trình vay mua nhà](quy-trinh-vay.md).

### 3.2. Quy trình tư vấn của chatbot

Quy trình tư vấn bắt đầu bằng việc xác định nhu cầu của người dùng, bao gồm tra cứu kiến thức, so sánh sản phẩm hoặc mô phỏng khoản vay. Hệ thống tiếp tục làm rõ các thông tin cần thiết, tra cứu tài liệu hoặc sử dụng công cụ tính toán phù hợp, sau đó trình bày kết quả kèm nguồn dữ liệu và các giả định liên quan.

Đối với hội thoại nhiều lượt, thông tin thay đổi được cập nhật theo yêu cầu mới nhất của người dùng. Các dữ kiện đã xác nhận được duy trì trong cùng tình huống; những thông tin còn thiếu hoặc mâu thuẫn cần được làm rõ trước khi đưa ra kết quả. Kết thúc quá trình tư vấn, hệ thống hướng dẫn người dùng chuẩn bị hồ sơ hoặc xác nhận điều kiện khoản vay trực tiếp với ngân hàng.

### 3.3. Nguyên tắc bảo đảm độ tin cậy của câu trả lời

- **Trả lời có căn cứ:** với câu hỏi kiến thức, hệ thống tìm các đoạn tài liệu liên quan trong kho tri thức; mô hình ngôn ngữ chỉ viết câu trả lời dựa trên các đoạn đó, ghi số trích dẫn và danh sách nguồn ở cuối. Không tìm thấy tài liệu phù hợp thì trả lời là chưa đủ căn cứ, không suy đoán.
- **Không để mô hình ngôn ngữ tính số tiền:** khi người dùng muốn ước tính khoản vay, chatbot hỏi đủ số tiền, thời hạn, lãi suất, phương thức trả nợ và ưu đãi (nếu có), nhắc lại để người dùng xác nhận, rồi mới gọi hàm tính của backend. Chatbot không tự chọn lãi suất thay người dùng.
- **Không nhận thông tin nhạy cảm:** chatbot không yêu cầu, không lưu và không xử lý số Căn cước, số tài khoản, mật khẩu, mã OTP; không tra cứu CIC.
- **Luôn ghi rõ tính tham khảo:** câu trả lời có lưu ý cần xác nhận với ngân hàng và ngày cập nhật dữ liệu; không hứa phê duyệt, không đưa xác suất được duyệt.

### 3.4. Mô phỏng khoản vay

Hàm tính của backend hỗ trợ:

| Nội dung | Cách tính |
|---|---|
| Trả đều gốc và lãi (niên kim) | Số tiền trả mỗi tháng = P × r / (1 − (1 + r)^−n), với P là số tiền vay, n là số tháng, r là lãi suất năm chia 12 |
| Gốc trả đều, lãi giảm dần | Gốc mỗi tháng = P / n; lãi tính trên dư nợ còn lại nên tháng đầu trả nhiều nhất |
| Lãi ưu đãi rồi lãi thả nổi | Dùng lãi ưu đãi trong số tháng ưu đãi, sau đó tính lại số tiền trả trên dư nợ còn lại với lãi thả nổi người dùng nhập (giả định giữ nguyên đến hết kỳ) |
| Ân hạn nợ gốc | Trong thời gian ân hạn chỉ trả lãi; sau đó trả gốc trong số tháng còn lại |
| Hạn mức vay tối đa | Mức thấp hơn giữa giới hạn theo giá trị nhà (tỷ lệ vay tối đa, mặc định tham khảo 80%) và giới hạn theo thu nhập (tổng trả nợ không quá 50% thu nhập, tính theo tháng phải trả cao nhất) |

Ví dụ vay 1,5 tỷ đồng trong 20 năm, lãi giả định 8,5%/năm cố định: trả niên kim 13.017.349 đồng/tháng, tổng lãi 1.624.163.639 đồng; trả gốc đều thì tháng đầu 16.875.000 đồng, tổng lãi 1.280.312.507 đồng. Các ngưỡng 80% và 50% chỉ là mức tham khảo, mỗi ngân hàng có quy định riêng.

## 4. Nguồn dữ liệu

Dữ liệu nghiệp vụ được tổng hợp từ các trang sản phẩm chính thức của ngân hàng và văn bản pháp luật được dẫn chiếu trong kho tri thức. Các tài liệu trong dự án được sử dụng như sau:

| Tài liệu | Nội dung sử dụng |
|---|---|
| [Kho câu hỏi thường gặp](../data/faq.json) | 60 câu hỏi và câu trả lời về nghiệp vụ vay mua nhà; mỗi mục có thông tin nguồn và ngày cập nhật |
| [Quy trình vay mua nhà](quy-trinh-vay.md) | Các giai đoạn thực hiện khoản vay và nghĩa vụ liên quan |
| [Dữ liệu ngân hàng](../data/banks_sample.json) | Thông số sản phẩm vay của 8 ngân hàng (lãi suất, hạn mức, thời hạn, phí trả trước hạn, điều kiện), mỗi bản ghi có đường dẫn nguồn và ngày rà soát |
| [Danh sách ngân hàng](danh-sach-ngan-hang.md) | Tiêu chí chọn 8 ngân hàng, nguồn đã xem và lý do để trống các trường ngân hàng không công bố |
| [Lược đồ dữ liệu](schema.md) | Cấu trúc và quy ước dữ liệu sản phẩm vay |

Thông tin nguồn và trường `last_updated` phục vụ truy xuất, đối chiếu dữ liệu. Ngày cập nhật dữ liệu được phân biệt với ngày hiệu lực của văn bản hoặc thời gian áp dụng của sản phẩm. Điều kiện khoản vay thực tế cần được xác nhận theo thông tin chính thức của ngân hàng tại thời điểm giao dịch.

## 5. Giới hạn và giá trị tham khảo

Kết quả tư vấn của chatbot có tính chất cung cấp thông tin và hỗ trợ chuẩn bị phương án vay. Hệ thống không thay thế hoạt động thẩm định, quyết định cấp tín dụng hoặc tư vấn pháp lý của cơ quan, tổ chức có thẩm quyền. Hạn mức quảng bá của sản phẩm không đồng nghĩa với số tiền được phê duyệt cho từng khách hàng.

Kết quả mô phỏng phụ thuộc vào dữ liệu đầu vào, phương thức trả nợ và giả định tính toán. Số tiền thực tế có thể khác do phương pháp tính lãi theo ngày, biến động lãi suất, phí và các điều khoản của hợp đồng. Các tỷ lệ hoặc mức lãi suất giả định trong tình huống minh họa không được xem là chính sách chung của ngân hàng.

Phạm vi trình diễn được giới hạn theo chức năng hiện có. Hàm tính của backend đã hỗ trợ ân hạn nợ gốc, nhưng API ước tính `/api/estimate` và nhánh ước tính trong chat chưa nhận tham số này. Riêng nhánh so sánh ngân hàng đã nhận số tháng ân hạn và gọi công cụ xếp hạng backend. Khi thiếu lãi sau ưu đãi, bot hỏi người dùng mức lãi giả định để so sánh; nếu đã có lãi cơ sở thì backend có thể kết hợp với biên độ công bố. Không tự thay dữ liệu ngân hàng để trống bằng lãi suất được xem là chính thức. Tổng chi phí so sánh gồm tiền lãi và phí trả trước hạn, chưa gồm mọi chi phí; công cụ chưa đánh giá tuổi, thu nhập hoặc khả năng được duyệt vay.

Lời so sánh do LLM diễn đạt từ kịch bản và kết quả backend, được giữ lại để kiểm tra số trước khi gửi. Số ngoài tập cho phép làm hệ thống chuyển về câu trả lời dựng sẵn. Cơ chế này chưa phát hiện được mọi trường hợp dùng số có thật nhưng sai ngân hàng, chỉ tiêu hoặc đơn vị; không được xem là bảo đảm tuyệt đối về nội dung định lượng. Kịch bản trình diễn và hồ sơ mẫu được trình bày tại [Kịch bản demo](kich-ban-demo.md); chi tiết kỹ thuật và giới hạn xem [Thiết kế chatbot](chatbot-design.md).

## 6. Kiểm thử chất lượng câu trả lời

Chất lượng được đo bằng [bộ câu hỏi kiểm thử](eval-questions.md) có đáp án chuẩn, gồm 10 câu gài (đưa lãi suất, phí hoặc xác suất duyệt bịa đặt; đòi số Căn cước, OTP; yêu cầu ngoài phạm vi) và các câu hội thoại nhiều lượt.

| Lần chạy | Mô hình | Số câu | Đúng | Một phần | Sai | Lỗi | Thời gian trả lời |
|---|---|---:|---:|---:|---:|---:|---|
| Lần 1 (15/11/2026) | Qwen 2.5 7B chạy trên máy | 40 | 24 | 7 | 8 | 1 | khoảng 55 giây/câu |
| Lần 2 (18/11/2026) | Mô hình trực tuyến, sau các bản sửa lỗi | 50 | 44 | 5 | 1 | 0 | trung bình 12 giây/câu |

Ở lần 2, các câu gài đều đạt: chatbot không xác nhận số liệu bịa và không nhận thông tin nhạy cảm. Các lỗi còn lại là chatbot nhận một yêu cầu ngoài phạm vi và quên thông tin khoản vay khi chuyển từ luồng tra cứu sang luồng tính (đang sửa). Kết quả lần 1 xem tại [eval-results.md](eval-results.md); kết quả lần 2 do trợ lý AI chấm sơ bộ theo cùng thang điểm, nhóm rà lại trước khi đưa vào báo cáo cuối kỳ.
