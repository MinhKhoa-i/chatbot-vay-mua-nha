# Khảo sát khả năng tư vấn vay mua nhà của Gemini

## 1. Phạm vi khảo sát

Báo cáo phân tích bản chép hội thoại và ảnh chụp Gemini do người thực hiện cung cấp. Dữ liệu gồm năm lượt hỏi liên tiếp, có sử dụng ngữ cảnh và điều chỉnh tham số từ lượt trước. Nội dung được đánh giá theo các khía cạnh: phép tính, rủi ro, phương án, nguồn dữ liệu và giới hạn tư vấn.

Đây là khảo sát hội thoại được cung cấp, không quy đổi thành kết quả chạy bộ EVAL-51–70. Nguyên văn bản chép được lưu tại Phụ lục A. Các nhãn nguồn trong bản chép được giữ nguyên, không tự bổ sung URL hoặc điều kiện sản phẩm thay cho phản hồi gốc. Số liệu được đọc từ bản chép; ảnh hỗ trợ nhận diện trình tự và biểu đồ.

## 2. Nội dung hội thoại

| Mã | Nội dung hỏi | Đặc điểm phản hồi |
|---|---|---|
| KS-01 | Bắt đầu vay mua nhà thế nào? | Trình bày quy trình, hồ sơ và các tỷ lệ tài chính tham khảo |
| KS-02 | Tính giúp mình khoản vay mỗi tháng | Tự chọn ví dụ 2 tỷ, 20 năm, 8%/năm; có ghi rõ là giả định |
| KS-03 | Tính giúp mình khoản vay mỗi tháng | Dùng 500 triệu, 5 năm, 4%/năm theo thao tác thanh trượt được nhắc trong phản hồi; bản chép không ghi nhật ký thao tác |
| KS-04 | So sánh lãi suất các ngân hàng | Có bảng số liệu và tên nguồn, nhận định ưu nhược điểm các nhóm ngân hàng |
| KS-05 | Mua căn hộ 7,5 tỷ, vay 5 tỷ/20 năm tại Techcombank, gốc đều, lãi giả định cố định 8,5%/năm | Tính khoản trả, tổng lãi, kịch bản tăng lãi và phần vốn cần bổ sung theo giả định định giá |

## 3. Đối chiếu số liệu

Số chuẩn được tính bằng `backend/finance/calculator.py` tại commit nền `dddc523`, phương thức `reducing_balance`, lãi năm chia 12, chưa gồm phí. Kết quả chỉ xác nhận phép tính theo giả định, không xác nhận lịch trả thực tế hoặc điều kiện sản phẩm của ngân hàng.

| Trường hợp | Gemini nêu | Số chuẩn | Đánh giá |
|---|---:|---:|---|
| KS-02: tháng đầu | Khoảng 21,67 triệu | 21.666.667 đồng | Phù hợp làm tròn |
| KS-03: tháng đầu | 10 triệu | 10.000.000 đồng | Đúng |
| KS-03: tổng lãi | Khoảng 50,83 triệu | 50.833.334 đồng | Phù hợp làm tròn |
| KS-05: tháng đầu | 56,25 triệu | 56.250.000 đồng | Đúng |
| KS-05: tháng 121 | Khoảng 38,54 triệu | 38.541.667 đồng | Phù hợp làm tròn |
| KS-05: tháng cuối | Khoảng 20,98 triệu | 20.980.902 đồng | Phù hợp làm tròn |
| KS-05: tổng lãi | Khoảng 4,27 tỷ | 4.267.708.333 đồng | Phù hợp làm tròn |
| KS-05: lãi 12% từ tháng 25 | Khoảng 65,83 triệu | 65.833.333 đồng | Phù hợp làm tròn |

Tỷ lệ 5 tỷ/7,5 tỷ xấp xỉ 66,7% là tỷ lệ theo giá mua. Phép tính 6,5 tỷ × 70% = 4,55 tỷ và phần thiếu 450 triệu đúng theo giả định, nhưng không xác nhận tỷ lệ cho vay thực tế của ngân hàng.

## 4. Đánh giá nội dung tư vấn

| Khía cạnh | Bằng chứng | Nhận xét |
|---|---|---|
| Khả thi tài chính | KS-05 đề xuất thu nhập 125–140 triệu/tháng | Có ước tính theo tỷ lệ tự nêu; chưa hỏi thu nhập, chi tiêu và nợ thực tế để đánh giá hồ sơ |
| Rủi ro | KS-05 nêu tăng lãi và giá trị thẩm định thấp hơn giá mua | Có ít nhất hai rủi ro và ví dụ số; cần phân biệt giả định với điều kiện sản phẩm |
| Phương án | Đề xuất xem tiếp tất toán năm 6 hoặc kéo dài kỳ hạn | Có định hướng nhưng chưa tính đầy đủ một phương án thay thế để so sánh trực tiếp |
| Tính toán | Các số liệu tại mục 3 | Những số đã kiểm tra phù hợp giả định và mức làm tròn; không đánh giá mã của biểu đồ |
| Nguồn | KS-04 có tên ngân hàng, báo chí và nền tảng; nhiều số về lãi, phí, bảo hiểm, định giá | Bản chép thiếu URL, ngày và điều kiện của nhiều số liệu nên chưa đủ căn cứ kiểm chứng; không kết luận các số này là bịa |
| Giới hạn | KS-05 chuyển từ lãi giả định cố định cả kỳ sang bàn về ưu đãi và lãi thả nổi | Cần tách rõ giả định đề bài, kịch bản bổ sung và điều kiện thực tế của ngân hàng |

Việc đề xuất tải bảng lương hoặc hồ sơ tài chính cần được xem xét về quyền riêng tư trước khi áp dụng cho chatbot nhóm. Nhận định về mua bảo hiểm nhân thọ và lãi suất chưa đủ căn cứ để kết luận có hành vi ép mua; hệ thống của nhóm cần phân biệt bảo hiểm tự nguyện và bảo hiểm tài sản.

## 5. Nhận xét tổng hợp

Gemini thể hiện khả năng hướng dẫn quy trình, tạo mô phỏng khoản vay và đề cập các rủi ro tài chính. Các phép tính được kiểm tra phù hợp với giả định. Hạn chế quan sát được là thiếu dữ liệu để đánh giá khả thi theo hồ sơ, thiếu thông tin truy xuất cho nhiều số liệu thị trường và chưa tính đầy đủ phương án thay thế.

Khảo sát này không đủ để kết luận chatbot nhóm tốt hơn Gemini. Kết quả phải được hiểu trong phạm vi năm lượt trao đổi được cung cấp.

## Phụ lục A. Nguyên văn bản chép

Các nhận định và số liệu trong khối dưới là phản hồi Gemini được cung cấp, không phải thông tin đã được báo cáo xác nhận.

SHA-256 của tệp gốc: `2b1f36d9d17b54efab0124c6a8ef8020659a9b47a2d4ca06d0babae03a97d306`.

```text
Bắt đầu vay mua nhà thế nào?

Quy trình vay mua nhà tại Việt Nam thường trải qua 5 bước cơ bản, kèm theo một số nguyên tắc an toàn tài chính bạn cần nắm rõ trước khi đặt cọc.

1. Xác định năng lực tài chính (Quan trọng nhất)
Trước khi đi xem nhà, bạn cần tự đánh giá khả năng chi trả của mình qua hai quy tắc thực tế:

Vốn tự có tối thiểu 30%: Ngân hàng thường cho vay tối đa 70% giá trị tài sản định giá. Bạn cần có sẵn ít nhất 30% giá trị căn nhà, cộng thêm khoảng 5% chi phí phát sinh (thuế, phí công chứng, phí thẩm định, nội thất cơ bản).

Quy tắc 40% thu nhập: Tổng số tiền trả nợ gốc và lãi hàng tháng không nên vượt quá 40% tổng thu nhập ổn định của gia đình để đảm bảo mức sống và dự phòng rủi ro.

2. Khảo sát lãi suất và chọn ngân hàng
Đừng chỉ nhìn vào lãi suất ưu đãi năm đầu (thường rất thấp, khoảng 6% - 8%/năm) mà hãy hỏi kỹ biên độ lãi suất thả nổi sau thời gian ưu đãi (thường bằng lãi suất tiết kiệm 12 tháng cộng thêm biên độ 3% - 4%).
Ngoài ra, cần kiểm tra phí phạt trả nợ trước hạn (thường dao động 1% - 3% trong 3-5 năm đầu) nếu bạn có ý định tất toán sớm.

3. Chuẩn bị hồ sơ vay vốn
Bạn nên nhờ ngân hàng thẩm định sơ bộ khả năng vay (ra thông báo cấp tín dụng nguyên tắc) trước khi xuống tiền đặt cọc mua nhà. Hồ sơ cơ bản gồm:

Hồ sơ pháp lý: CCCD, giấy xác nhận tình trạng hôn nhân (giấy đăng ký kết hôn hoặc giấy xác nhận độc thân).

Hồ sơ chứng minh thu nhập: Hợp đồng lao động, sao kê lương 3-6 tháng gần nhất; hoặc giấy phép kinh doanh, sổ sách thu chi nếu kinh doanh tự do.

Hồ sơ tài sản đảm bảo: Sổ hồng/sổ đỏ hoặc hợp đồng mua bán (nếu mua dự án hình thành trong tương lai).

4. Thẩm định và phê duyệt khoản vay
Sau khi nhận đủ hồ sơ và bạn đã đặt cọc mua nhà, ngân hàng sẽ tiến hành:

Kiểm tra lịch sử tín dụng (CIC) của bạn.

Thẩm định giá trị thực tế của bất động sản (lưu ý giá ngân hàng định giá thường thấp hơn giá giao dịch thị trường khoảng 10% - 15%).

Ra thông báo cho vay chính thức nêu rõ số tiền được duyệt, thời hạn vay và điều kiện giải ngân.

5. Công chứng, đăng ký giao dịch bảo đảm và giải ngân
Hai bên mua bán ra phòng công chứng ký hợp đồng mua bán và sang tên sổ hồng.

Ngân hàng tiến hành thủ tục đăng ký thế chấp tài sản (giao dịch bảo đảm) tại văn phòng đăng ký đất đai.

Ngân hàng giải ngân phần tiền vay trực tiếp vào tài khoản của bên bán (hoặc phong tỏa tài khoản chờ hoàn tất sang tên tùy thỏa thuận ba bên).

Để tính toán cụ thể số tiền bạn có thể vay và lịch trả nợ hàng tháng, bạn có thể chia sẻ thêm vài thông tin cơ bản bên dưới.

Bạn muốn bắt đầu từ đâu để tính toán kế hoạch vay?
Step 1/4
Chọn một phương án

Tải lên bảng lương hoặc file tính toán tài chính cá nhân

Trả lời nhanh vài câu hỏi về thu nhập và giá nhà dự kiến
Tính giúp mình khoản vay mỗi tháng

Để ước tính nhanh, mình giả định một kịch bản phổ biến: vay 2 tỷ đồng trong 20 năm với lãi suất trung bình 8%/năm (tính theo dư nợ giảm dần — cách tính tiêu chuẩn của hầu hết ngân hàng tại Việt Nam).

Với kịch bản này:

Tiền gốc trả cố định mỗi tháng: ~8,33 triệu đồng (2 tỷ / 240 tháng).

Tiền lãi tháng cao nhất (tháng đầu): ~13,33 triệu đồng (2 tỷ × 8% / 12), sau đó giảm dần theo dư nợ còn lại.

Tổng gốc + lãi tháng đầu tiên: ~21,67 triệu đồng (để an toàn theo quy tắc 40%, tổng thu nhập của bạn nên từ 54 triệu/tháng trở lên).

Bạn có thể kéo các thanh trượt dưới đây để điều chỉnh lại số tiền vay, lãi suất và thời hạn theo đúng nhu cầu thực tế của mình:

Mô phỏng dư nợ vay mua nhà

Nếu bạn muốn mình tính chi tiết bảng lịch trả nợ từng năm (tách riêng phần ưu đãi năm đầu và phần thả nổi các năm sau), bạn có thể nhập nhanh các con số thực tế dưới đây:

Bạn muốn nhập thông tin theo cách nào?
Step 1/4
Chọn cách cung cấp thông tin

Tải lên bảng tính hoặc file thông tin tài chính

Nhập trực tiếp số tiền vay, thời hạn và lãi suất
Tính giúp mình khoản vay mỗi tháng

Ở trên bạn đã điều chỉnh thanh trượt trên bảng mô phỏng về mức vay 500 triệu đồng trong 5 năm với lãi suất 4%/năm. Với các thông số mới này, số tiền trả hàng tháng theo phương pháp dư nợ giảm dần như sau:

Tiền gốc cố định mỗi tháng: 8,33 triệu đồng (500 triệu / 60 tháng).

Tiền lãi tháng đầu tiên (cao nhất): 1,67 triệu đồng (500 triệu × 4% / 12), sau đó giảm khoảng 27.800 đồng mỗi tháng.

Tổng gốc + lãi tháng đầu tiên: 10 triệu đồng.

Tổng gốc + lãi tháng cuối cùng: 8,36 triệu đồng.

Tổng tiền lãi cả kỳ 5 năm: 50,83 triệu đồng (tổng gốc + lãi phải trả là 550,83 triệu đồng).

Nếu bạn muốn xem cụ thể số tiền phải trả từng tháng (thay vì tổng lũy kế theo năm), biểu đồ dưới đây mô phỏng chi tiết khoản thanh toán hàng tháng cho thông số 500 triệu – 5 năm – 4%/năm (bạn vẫn có thể kéo thanh trượt để thử các mức khác):

Chi tiết khoản trả nợ hàng tháng

So sánh lãi suất các ngân hàng

Mặt bằng lãi suất vay mua nhà trong năm 2026 đã tăng đáng kể so với giai đoạn trước. Mức lãi suất cụ thể trên thị trường hiện chia thành 3 nhóm ngân hàng với đặc điểm và ưu nhược điểm riêng:   
VPBank
+ 1

1. Nhóm ngân hàng quốc doanh (Big 4)   
Thời báo Tài chính Việt Nam
Nhóm này có lãi suất thả nổi sau ưu đãi tương đối ổn định, ít nhảy vọt bất ngờ, nhưng điều kiện chứng minh thu nhập khá chặt chẽ.   
CafeF

Ngân hàng	Lãi suất cố định 12 tháng đầu	Tỷ lệ vay tối đa	Kỳ hạn tối đa
Agribank	~9,5%/năm	100% nhu cầu vốn	40 năm
Vietcombank	~9,9%/năm	70% - 100%	30 - 40 năm
VietinBank	~10,0%/năm	80%	20 năm
BIDV	~10,8%/năm	100% nhu cầu vốn	30 năm
(Lưu ý: Nếu chọn gói cố định dài hạn 18 - 24 tháng tại nhóm này, lãi suất có thể lên mức 13,5% - 13,9%/năm).   
TOPI

2. Nhóm ngân hàng thương mại cổ phần (TMCP)
Nhóm này linh hoạt trong việc xét duyệt nguồn thu (đặc biệt phù hợp với người kinh doanh tự do) và thường có gói lãi suất thấp ở 3 - 6 tháng đầu để kích cầu, nhưng biên độ thả nổi sau ưu đãi thường cao hơn Big 4.   
TOPI

Ngân hàng	Lãi suất ưu đãi khởi điểm	Thời gian ưu đãi phổ biến	Kỳ hạn tối đa
Techcombank	6,0% - 8,5%/năm	6 - 24 tháng	35 năm
BVBank	5,99% - 8,6%/năm	6 - 24 tháng	25 năm
SHB	7,0% - 8,5%/năm	12 - 60 tháng	35 năm
OCB	7,99% - 8,99%/năm	6 - 12 tháng	30 năm
HDBank	~9,8%/năm	6 - 12 tháng	35 năm
ACB / MBBank / MSB	11,0% - 12,0%/năm	12 tháng	20 - 35 năm
3. Nhóm ngân hàng nước ngoài
Phù hợp nếu bạn nhận lương chuyển khoản qua ngân hàng, hồ sơ pháp lý nhà rõ ràng (đã có sổ hồng) và muốn cố định lãi suất trong 2 - 3 năm đầu để tránh biến động.   
Wiki BĐS - Batdongsan.com

Ngân hàng	Lãi suất cố định 12 tháng đầu	Tỷ lệ vay tối đa	Kỳ hạn tối đa
UOB	6,24% - 8,0%/năm	75%	30 năm
Woori Bank	~9,3%/năm	80%	30 năm
Hong Leong Bank	9,8% - 9,9%/năm	80%	25 năm
Shinhan Bank	~10,0%/năm	70%	30 năm
Những điểm cần lưu ý trước khi chốt ngân hàng
Cảnh giác với lãi suất "mồi" 3 - 6 tháng: Các gói lãi suất 5% - 6%/năm thường chỉ áp dụng trong 3 đến 6 tháng đầu. Sau thời gian này, lãi suất thả nổi trên thị trường hiện dao động quanh mức 12% - 15%/năm. Với khoản vay 500 triệu trong 5 năm bạn đang cân nhắc, nếu lãi suất thả nổi tăng lên 12%/năm, tiền lãi tháng cao nhất sẽ tăng từ 1,67 triệu lên khoảng 5 triệu đồng/tháng.   
Dân trí

Định giá tài sản: Ngân hàng thương mại thường định giá bất động sản sát giá thị trường hơn so với nhóm Big 4, giúp bạn vay được hạn mức cao hơn nếu cần.

Điều kiện hồ sơ: Lãi suất thực tế bạn nhận được sẽ phụ thuộc vào loại tài sản (nhà phố có sổ hay căn hộ dự án liên kết), nguồn thu nhập (lương chuyển khoản hay kinh doanh) và việc bạn có mua kèm bảo hiểm nhân thọ hay không.

Mình định mua căn hộ chung cư ở TP. Hồ Chí Minh giá khoảng 7,5 tỷ và vay 5 tỷ trong 20 năm tại Techcombank, thế chấp chính căn hộ này. Giả định lãi suất cố định 8,5%/năm, trả gốc đều và lãi giảm dần, bạn tính giúp mình số tiền trả hàng tháng và tư vấn thêm nhé.

Với phương án mua căn hộ 7,5 tỷ đồng tại TP.HCM và vay 5 tỷ đồng (tương đương 66,7% giá trị căn hộ) trong 20 năm (240 tháng) tại Techcombank, giả định lãi suất cố định 8,5%/năm theo phương pháp trả gốc đều, lãi tính trên dư nợ giảm dần:

1. Chi tiết dòng tiền trả nợ hàng tháng
Tiền gốc cố định mỗi tháng: 20,83 triệu đồng (5 tỷ / 240 tháng).

Tiền lãi tháng đầu tiên (cao nhất): 35,42 triệu đồng (5 tỷ × 8,5% / 12), sau đó giảm đều khoảng 147.570 đồng sau mỗi tháng.

Tổng gốc + lãi tháng đầu tiên: 56,25 triệu đồng.

Tổng gốc + lãi tại năm thứ 10 (tháng 121): 38,54 triệu đồng.

Tổng gốc + lãi tháng cuối cùng: 20,98 triệu đồng.

Tổng tiền lãi cả kỳ 20 năm: 4,27 tỷ đồng (tổng gốc + lãi phải trả là 9,27 tỷ đồng).

Để duy trì mức sống an toàn và dự phòng biến động lãi suất, tổng thu nhập ròng hàng tháng của gia đình bạn nên đạt tối thiểu 125 - 140 triệu đồng/tháng (tỷ lệ trả nợ chiếm 40% - 45% thu nhập).

Biểu đồ dưới đây mô phỏng biến động tiền gốc, tiền lãi và tổng số tiền phải trả hàng tháng suốt 240 tháng (bạn có thể kéo thanh trượt để kiểm tra kịch bản nếu lãi suất tăng lên 11% - 12%/năm sau thời gian ưu đãi):

Lịch trả nợ hàng tháng - Khoản vay 5 tỷ

2. Bốn điểm thực tế cần lưu ý khi vay 5 tỷ tại Techcombank
Rủi ro sau thời gian cố định lãi suất: Mức 8,5%/năm thường chỉ áp dụng cố định trong 12 đến 24 tháng đầu. Sau giai đoạn này, lãi suất chuyển sang thả nổi theo công thức lãi suất cơ sở của Techcombank cộng biên độ (thường quanh mức 11% - 12,5%/năm). Nếu lãi suất tăng lên 12%/năm vào năm thứ 3 (khi dư nợ gốc còn 4,5 tỷ), tiền lãi tháng sẽ nhảy từ ~31,8 triệu lên 45 triệu đồng, đẩy tổng trả hàng tháng lên 65,83 triệu đồng.

Định giá tài sản và tỷ lệ cho vay thực tế: Bạn đang tính vay 5 tỷ / 7,5 tỷ (tỷ lệ 66,7%, nằm dưới trần 70% - 75% của ngân hàng). Tuy nhiên, ngân hàng sẽ định giá căn hộ dựa trên khung giá thẩm định nội bộ (thường thấp hơn giá giao dịch thực tế khoảng 10% - 15%). Nếu căn hộ chỉ được định giá 6,5 tỷ, hạn mức vay tối đa 70% sẽ chỉ đạt 4,55 tỷ đồng — bạn cần chuẩn bị thêm khoảng 450 triệu tiền mặt dự phòng cho tình huống này.

Phí trả nợ trước hạn và lộ trình tất toán: Với khoản vay lớn 5 tỷ trong 20 năm, tổng tiền lãi lên tới 4,27 tỷ đồng. Phần lớn người vay mua nhà tại TP.HCM sẽ tất toán trong vòng 5 - 7 năm đầu. Techcombank thường áp dụng phí phạt trả nợ trước hạn khoảng 1% - 2% trên số tiền trả trước trong 3 - 5 năm đầu và miễn phí từ năm thứ 6 trở đi. Bạn nên hỏi rõ biểu phí này để lên kế hoạch gom tiền trả bớt gốc sau năm thứ 5.

Chi phí ngoài khoản vay (khoảng 300 - 450 triệu đồng): Ngoài 2,5 tỷ vốn tự có để thanh toán cho chủ nhà, bạn cần dự trù thêm:

Lệ phí trước bạ (0,5% giá trị hợp đồng), phí công chứng, phí thẩm định và đăng ký giao dịch bảo đảm (~40 - 50 triệu đồng).

Bảo hiểm cháy nổ bắt buộc cho căn hộ thế chấp (khoảng 0,1% - 0,15%/năm giá trị tài sản, đóng hàng năm suốt thời gian vay).

Chi phí hoàn thiện nội thất cơ bản và phí quản lý chung cư (thường từ 15.000 - 25.000đ/m²/tháng tại TP.HCM).

Bạn muốn phân tích tiếp kịch bản nào cho căn hộ 7,5 tỷ này?

Mô phỏng kịch bản lãi thả nổi 12% từ năm thứ 3

Kế hoạch tất toán sớm vào năm thứ 6

So sánh phương án kéo dài kỳ hạn lên 30 năm
```
