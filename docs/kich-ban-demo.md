# Kịch bản khách hàng mẫu cho demo và test case

> Tất cả hồ sơ dưới đây là dữ liệu giả lập, không đại diện khách hàng thật. Thu nhập là thu nhập ròng hộ gia đình/tháng. Thông số ngân hàng cần được đối chiếu theo `last_updated` và `source_url` trong `data/banks_sample.json`.
>
> **Lưu ý demo:** 4 hồ sơ đầu tiên (Hồ sơ 1 đến 4) là các kịch bản cốt lõi được chọn lọc phục vụ kịch bản demo 5 phút và kiểm thử tự động. Hồ sơ 5 đến 7 là các trường hợp kiểm thử nâng cao bổ sung để đối soát chuyên sâu về điều kiện biên (phí trả trước hạn và giới hạn độ tuổi).

---

## 1. Bốn hồ sơ cốt lõi cho kịch bản demo (5 phút)

### Hồ sơ 1 — Cặp vợ chồng mua căn hộ đầu tiên (Test LTV & Thời hạn VPBank)

- **Thông tin khách hàng:** Tuổi 29 và 31; thu nhập ròng hộ gia đình 55 triệu đồng/tháng.
- **Phương án vay:** Căn hộ 3,2 tỷ đồng; vốn tự có 1,2 tỷ đồng; dự kiến vay 2 tỷ đồng.
- **Thời hạn & phương thức:** 20 năm (240 tháng); trả gốc đều, lãi trên dư nợ giảm dần (`reducing_balance`); chưa dự kiến trả trước hạn.
- **Câu hỏi demo:** *"Với thu nhập 55 triệu/tháng, chúng tôi vay 2 tỷ trong 20 năm mua căn hộ 3,2 tỷ có phù hợp không? Nhờ bot so sánh khoản trả tháng đầu tiên và giải thích ngân hàng nào đủ điều kiện."*
- **Test case & Kỳ vọng hệ thống:**
  - Kiểm tra LTV yêu cầu: $2,0 / 3,2 = 62,5\%$ (đáp ứng điều kiện LTV tối đa của cả 8 ngân hàng, thường từ 70% đến 80%).
  - Kiểm tra điều kiện thời hạn vay: Khoản vay 20 năm hợp lệ với VPBank vì gói vay ưu đãi áp dụng thời hạn tối đa 25 năm và không quy định thời hạn tối thiểu (trước đây bị lỗi nhầm `min_loan_term_years = 25` dẫn đến loại sai).
  - Kiểm tra tính đầy đủ của dữ liệu: Do các ngân hàng chưa công bố lãi suất thả nổi sau ưu đãi nên chatbot phải thông báo minh bạch, không tự ý xếp hạng tổng chi phí toàn kỳ khi thiếu dữ liệu thả nổi.

---

### Hồ sơ 2 — Gia đình mua nhà phố, ưu tiên kỳ hạn dài & ân hạn gốc

- **Thông tin khách hàng:** Tuổi người vay 38; thu nhập ròng hộ gia đình 80 triệu đồng/tháng.
- **Phương án vay:** Nhà phố 5 tỷ đồng; vốn tự có 1,5 tỷ đồng; dự kiến vay 3,5 tỷ đồng.
- **Thời hạn & phương thức:** 25 năm (300 tháng); trả theo niên kim cố định (`annuity`); yêu cầu ân hạn nợ gốc 12 tháng đầu.
- **Câu hỏi demo:** *"Tôi có nên vay 3,5 tỷ trong 25 năm nếu thu nhập 80 triệu/tháng không? Hãy nêu rõ ngân hàng nào có chính sách ân hạn gốc 12 tháng và ngân hàng nào đủ dữ kiện để tính toán."*
- **Test case & Kỳ vọng hệ thống:**
  - LTV yêu cầu: $3,5 / 5,0 = 70,0\%$ (đáp ứng trần LTV của Vietcombank, VietinBank, Agribank và các ngân hàng TMCP).
  - Kiểm tra chính sách ân hạn gốc (`grace_period_months`): Vietcombank (12T), Agribank (12T), Techcombank (24T), MB Bank (24T), VPBank (12T), ACB (12T) đều đáp ứng; BIDV chỉ ân hạn 6 tháng nên không thỏa mãn điều kiện 12 tháng.
  - Chatbot chỉ rõ dữ kiện còn thiếu (lãi suất thả nổi sau ưu đãi) và khuyến nghị khách hàng kiểm tra với chuyên viên tín dụng thay vì tự lấy lãi suất ưu đãi để tính toàn bộ 25 năm.

---

### Hồ sơ 3 — Khách hàng mua nhà dự án có Giấy chứng nhận (Vietcombank)

- **Thông tin khách hàng:** Tuổi 33; thu nhập ròng hộ gia đình 65 triệu đồng/tháng.
- **Phương án vay:** Nhà tại dự án bất động sản đã có Giấy chứng nhận: 4 tỷ đồng; vốn tự có 1 tỷ đồng; dự kiến vay 3 tỷ đồng.
- **Thời hạn & phương thức:** 20 năm (240 tháng); trả gốc đều lãi giảm dần (`reducing_balance`); chưa dự kiến trả trước hạn.
- **Câu hỏi demo:** *"Tôi muốn vay 3 tỷ mua nhà dự án đã có sổ hồng. Tôi có thuộc phạm vi chương trình Nhà Mới An Cư của Vietcombank không? Lãi suất 9% trong 12 tháng đầu áp dụng theo những điều kiện nào?"*
- **Test case & Kỳ vọng hệ thống:**
  - Nhắc đầy đủ các điều kiện ràng buộc của gói Nhà Mới An Cư: Áp dụng cho hợp đồng ký mới từ ngày 14/10/2026, dự án nằm trong danh sách được Vietcombank lựa chọn và còn quy mô gói tín dụng.
  - Tỷ lệ tài trợ: Nhà có sẵn GCN hỗ trợ tối đa 70% giá trị định giá ($3,0 / 4,0 = 75\%$ cần có thêm tài sản độc lập bổ sung để đạt mức 75%).
  - Tuyệt đối không tự suy diễn lãi suất từ tháng thứ 13 trở đi khi ngân hàng chưa công bố biên độ thả nổi chính thức cho chương trình này.

---

### Hồ sơ 4 — Người trẻ mua nhà lần đầu theo gói ưu đãi BIDV

- **Thông tin khách hàng:** Tuổi 27; thu nhập ròng 45 triệu đồng/tháng.
- **Phương án vay:** Căn hộ/nhà đất 2,5 tỷ đồng; vốn tự có 750 triệu đồng; dự kiến vay 1,75 tỷ đồng.
- **Thời hạn & phương thức:** 20 năm (240 tháng); cân nhắc gói lãi suất cố định 12 tháng của BIDV.
- **Câu hỏi demo:** *"Gói BIDV Ngôi nhà đầu tiên áp dụng mức 9,0%/năm trong 12 tháng kèm điều kiện gì về thời hạn vay? Sau thời gian ưu đãi tôi cần hỏi thêm thông tin gì để tính tổng tiền trả?"*
- **Test case & Kỳ vọng hệ thống:**
  - Nêu chính xác điều kiện gắn với các phương án lựa chọn lãi suất của BIDV (đối soát tại 16/11/2026): Lựa chọn 9,0%/12 tháng yêu cầu thời hạn vay tối thiểu 36 tháng; lựa chọn 9,5%/18 tháng và 10,0%/24 tháng yêu cầu thời hạn vay tối thiểu 60 tháng. Khoản vay 20 năm (240 tháng) hoàn toàn thỏa mãn.
  - Điều kiện đối tượng: Áp dụng cho khách hàng cá nhân chưa từng có dư nợ vay mua nhà tại BIDV.
  - Hướng dẫn khách hàng hỏi chi nhánh về biên độ lãi suất thả nổi sau ưu đãi và lãi suất tiền gửi tham chiếu 24 tháng trả sau để biết chi phí thực tế các năm tiếp theo.

---

## 2. Các hồ sơ kiểm thử nâng cao bổ sung (Edge Cases)

### Hồ sơ 5 — Khách hàng trẻ vay VPBank kỳ hạn 25 năm (Test Tiers phí trả trước)

- **Thông tin khách hàng:** Tuổi 28; thu nhập ròng hộ gia đình 50 triệu đồng/tháng.
- **Phương án vay:** Căn hộ 2,8 tỷ đồng; vốn tự có 800 triệu đồng; dự kiến vay 2 tỷ đồng.
- **Thời hạn & phương thức:** 25 năm (300 tháng); trả theo niên kim cố định (`annuity`); không ân hạn gốc.
- **Câu hỏi demo:** *"Với kỳ hạn 25 năm và vay 2 tỷ, VPBank có phù hợp không? So sánh phí trả trước hạn và tổng chi phí giữa VPBank và các ngân hàng khác chấp nhận kỳ hạn 25 năm."*
- **Test case & Kỳ vọng hệ thống:**
  - Kiểm tra thời hạn: VPBank chấp nhận thời hạn tối đa 25 năm (đáp ứng đúng thời hạn mong muốn).
  - Phí trả nợ trước hạn theo biểu `tiers`: 4 năm đầu tối đa 2,5% trên số tiền nợ gốc trả trước (mức trần); từ năm thứ 5 trở đi được miễn phí (0,0%).
  - Lãi suất: Trường `interest_rate` của VPBank là `null` do ngân hàng chỉ quảng bá "từ 5,2%/năm" mà không công bố kỳ ưu đãi cụ thể và lãi sau ưu đãi. Chatbot không được tự suy ra lãi suất thả nổi từ mức quảng bá này.

---

### Hồ sơ 6 — Gia đình trung niên ưu tiên trả trước hạn (Test Tiers Agribank)

- **Thông tin khách hàng:** Tuổi 45; thu nhập ròng hộ gia đình 90 triệu đồng/tháng.
- **Phương án vay:** Nhà phố 6 tỷ đồng; vốn tự có 2 tỷ đồng; dự kiến vay 4 tỷ đồng.
- **Thời hạn & phương thức:** 15 năm (180 tháng); trả gốc đều lãi giảm dần (`reducing_balance`); dự định tất toán toàn bộ sau 5 năm (tháng thứ 60).
- **Câu hỏi demo:** *"Nếu tôi muốn tất toán toàn bộ khoản vay sau 5 năm, Agribank tính phí phạt bao nhiêu phần trăm? So sánh với các ngân hàng chưa công bố biểu phí chi tiết."*
- **Test case & Kỳ vọng hệ thống:**
  - Agribank công bố biểu phí phạt tất toán trung/dài hạn theo 3 bậc (`tiers`): Năm 1 trần 4,0%, Năm 2 trần 3,0%, Từ năm 3 đến hết kỳ hạn trần 2,0%.
  - Trả nợ trước hạn sau 5 năm (bắt đầu năm thứ 6) thuộc bậc `from_year = 3, to_year = 35, rate_percent = 2.0` → mức phí phạt trần là 2,0% nhân với dư nợ gốc còn lại tại thời điểm tất toán.
  - Chatbot nêu rõ 2,0% là mức trần theo quy định chung của Agribank, mức thực tế do chi nhánh quyết định. Các ngân hàng có `tiers = []` phải thông báo chưa có biểu phí chi tiết công khai, không tự ước lượng.
  - Điều kiện độ tuổi: 45 + 15 = 60 tuổi ≤ 65 tuổi (đáp ứng điều kiện của Agribank).

---

### Hồ sơ 7 — Người lớn tuổi vay ngắn hạn (Test Điều kiện độ tuổi khi đáo hạn)

- **Thông tin khách hàng:** Tuổi 55; thu nhập ròng 120 triệu đồng/tháng (thu nhập từ hoạt động sản xuất kinh doanh).
- **Phương án vay:** Nhà đã có Giấy chứng nhận (Sổ đỏ): 8 tỷ đồng; vốn tự có 4 tỷ đồng; dự kiến vay 4 tỷ đồng.
- **Thời hạn & phương thức:** 10 năm (120 tháng); trả gốc đều lãi giảm dần (`reducing_balance`); không trả trước hạn.
- **Câu hỏi demo:** *"Ở tuổi 55 vay 4 tỷ trong 10 năm, ngân hàng nào chấp nhận hồ sơ của tôi? Giới hạn độ tuổi kết thúc khoản vay của từng ngân hàng quy định như thế nào?"*
- **Test case & Kỳ vọng hệ thống:**
  - Kiểm tra tiêu chí độ tuổi khi kết thúc khoản vay: Khách hàng đạt 55 + 10 = 65 tuổi tại thời điểm đáo hạn.
  - Đối chiếu `max_age_at_loan_end`:
    - Vietcombank (tối đa 75 tuổi): Đủ điều kiện ($65 \le 75$).
    - VietinBank, BIDV, MB Bank, VPBank (tối đa 70 tuổi): Đủ điều kiện ($65 \le 70$).
    - Agribank, ACB (quy định tối đa 65 tuổi): Đạt mốc giới hạn tối đa; chatbot cần lưu ý khách hàng xác nhận lại với phòng giao dịch về cách tính tròn tháng sinh nhật.
  - Thu nhập kinh doanh: Nhắc khách hàng chuẩn bị hồ sơ chứng minh thu nhập phi lương (đăng ký kinh doanh, báo cáo tài chính, tờ khai thuế, sao kê dòng tiền).
