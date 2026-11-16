# Kịch bản khách hàng mẫu cho demo và test case

> Tất cả hồ sơ dưới đây là dữ liệu giả lập, không đại diện khách hàng thật. Thu nhập là thu nhập ròng hộ gia đình/tháng. Thông số ngân hàng cần được đối chiếu theo `last_updated` và `source_url` trong `data/banks_sample.json`.

## Hồ sơ 1 — Cặp vợ chồng mua căn hộ đầu tiên

- Tuổi: 29 và 31; thu nhập ròng hộ gia đình: 55 triệu đồng/tháng.
- Căn hộ: 3,2 tỷ đồng; vốn tự có: 1,2 tỷ đồng; dự kiến vay: 2 tỷ đồng.
- Thời hạn mong muốn: 20 năm; trả gốc đều, lãi trên dư nợ giảm dần; chưa dự kiến trả trước hạn.
- Câu hỏi demo: “Với thu nhập 55 triệu/tháng, vay 2 tỷ trong 20 năm mua căn hộ 3,2 tỷ có phù hợp không? So sánh khoản trả tháng đầu và tổng lãi.”
- Test case: kiểm tra LTV yêu cầu 62,5%; không đưa VPBank vào kết quả 20 năm nếu sản phẩm yêu cầu kỳ hạn tối thiểu 25 năm. Không xếp hạng ngân hàng thiếu lãi suất sau ưu đãi.

## Hồ sơ 2 — Gia đình mua nhà phố, ưu tiên kỳ hạn dài

- Tuổi người vay: 38; thu nhập ròng: 80 triệu đồng/tháng.
- Nhà phố: 5 tỷ đồng; vốn tự có: 1,5 tỷ đồng; dự kiến vay: 3,5 tỷ đồng.
- Thời hạn mong muốn: 25 năm; trả theo niên kim; cần ân hạn gốc 12 tháng.
- Câu hỏi demo: “Tôi có nên vay 3,5 tỷ trong 25 năm nếu thu nhập 80 triệu/tháng? Hãy nêu rõ ngân hàng nào đủ dữ kiện để so sánh và dữ kiện nào còn thiếu.”
- Test case: LTV yêu cầu 70%; kiểm tra mức ân hạn và điều kiện gói vay, không tự lấy lãi suất quảng bá làm lãi suất sau ưu đãi.

## Hồ sơ 3 — Khách hàng mua nhà đã có giấy chứng nhận

- Tuổi: 33; thu nhập ròng: 65 triệu đồng/tháng.
- Nhà tại dự án đã có Giấy chứng nhận: 4 tỷ đồng; vốn tự có: 1 tỷ đồng; dự kiến vay: 3 tỷ đồng.
- Thời hạn mong muốn: 20 năm; phương thức trả gốc đều; chưa dự kiến trả trước hạn.
- Câu hỏi demo: “Tôi có thuộc phạm vi chương trình Nhà Mới An Cư của Vietcombank không? Lãi suất 9% trong 12 tháng đầu áp dụng điều kiện nào?”
- Test case: nhắc điều kiện về dự án do ngân hàng lựa chọn, địa bàn và thời gian chương trình; không suy ra mức lãi suất sau tháng 12.

## Hồ sơ 4 — Người trẻ mua nhà theo chương trình BIDV

- Tuổi: 27; thu nhập ròng: 45 triệu đồng/tháng.
- Nhà/đất: 2,5 tỷ đồng; vốn tự có: 750 triệu đồng; dự kiến vay: 1,75 tỷ đồng.
- Thời hạn mong muốn: 20 năm; cân nhắc gói lãi suất 9% cố định 12 tháng.
- Câu hỏi demo: “Gói BIDV Ngôi nhà đầu tiên áp dụng mức 9%/năm trong 12 tháng với điều kiện kỳ hạn nào? Sau ưu đãi cần hỏi thêm thông tin gì?”
- Test case: nhắc kỳ hạn tối thiểu 36 tháng của lựa chọn 9%/12 tháng, cập nhật lãi suất 17/09/2026 và việc chưa có dữ liệu lãi suất thả nổi để tính tổng chi phí dài hạn.

## Hồ sơ 5 — Khách hàng trẻ vay VPBank kỳ hạn 25 năm

- Tuổi: 28; thu nhập ròng hộ gia đình: 50 triệu đồng/tháng.
- Căn hộ: 2,8 tỷ đồng; vốn tự có: 800 triệu đồng; dự kiến vay: 2 tỷ đồng.
- Thời hạn mong muốn: 25 năm; trả theo niên kim (annuity); không có ân hạn.
- Câu hỏi demo: "Với kỳ hạn 25 năm và vay 2 tỷ, VPBank có phù hợp không? So sánh phí trả trước hạn và tổng chi phí giữa VPBank và các ngân hàng khác chấp nhận kỳ hạn 25 năm."
- Test case: VPBank chỉ công bố phí trả trước tối đa 2,5% (mức trần 4 năm đầu) và miễn phí từ năm thứ 5, nhưng lãi suất có cấu trúc để null (không có kỳ ưu đãi/lãi sau ưu đãi đủ dữ liệu) → chatbot không thể xếp hạng VPBank theo chi phí đầy đủ toàn kỳ, chỉ có thể nêu điều kiện phí trả trước tham khảo; kiểm tra rằng chatbot không tự suy ra lãi suất sau ưu đãi từ mức "từ 5,2%/năm" được quảng bá.

## Hồ sơ 6 — Gia đình trung niên ưu tiên trả trước hạn (Agribank tiers)

- Tuổi: 45; thu nhập ròng hộ gia đình: 90 triệu đồng/tháng.
- Nhà phố: 6 tỷ đồng; vốn tự có: 2 tỷ đồng; dự kiến vay: 4 tỷ đồng.
- Thời hạn mong muốn: 15 năm; trả gốc đều, lãi trên dư nợ giảm dần (reducing_balance); dự định trả trước toàn bộ dư nợ còn lại sau năm thứ 5.
- Câu hỏi demo: "Nếu tôi muốn trả hết nợ sau 5 năm, Agribank tính phí tất toán sớm bao nhiêu phần trăm? So sánh với các ngân hàng chưa công bố biểu phí chi tiết."
- Test case: Agribank có biểu phí tiers công khai: năm 1 (trần 4%), năm 2 (trần 3%), từ năm 3 trở đi (trần 2%); trả trước hạn vào đầu năm thứ 6 (after_year=5) ứng với bậc `from_year=3, to_year=35, rate_percent=2.0` → phí tối đa 2,0% × dư nợ còn lại; chatbot phải nêu rõ đây là mức trần, mức thực thu do chi nhánh quyết định theo hợp đồng. Kiểm tra điều kiện tuổi: 45 + 15 = 60 ≤ 65 (Agribank max_age_at_loan_end) → đủ điều kiện. Các ngân hàng chưa công bố tiers phải được ghi rõ là "chưa có thông tin chi tiết", không tự ước lượng.

## Hồ sơ 7 — Người lớn tuổi vay ngắn hạn, kiểm tra điều kiện độ tuổi

- Tuổi: 55; thu nhập ròng: 120 triệu đồng/tháng (thu nhập từ kinh doanh).
- Nhà đã có Giấy chứng nhận (sổ đỏ): 8 tỷ đồng; vốn tự có: 4 tỷ đồng; dự kiến vay: 4 tỷ đồng.
- Thời hạn mong muốn: 10 năm; trả gốc đều, lãi trên dư nợ giảm dần (reducing_balance); không dự kiến trả trước hạn.
- Câu hỏi demo: "Ở tuổi 55 vay 4 tỷ trong 10 năm, ngân hàng nào trong danh sách chấp nhận hồ sơ của tôi? Tiêu chí độ tuổi kết thúc khoản vay của từng ngân hàng là bao nhiêu?"
- Test case: Kiểm tra `max_age_at_loan_end` với 55 + 10 = 65 tuổi khi đáo hạn — VietinBank (max_age=70 → ✅ OK), BIDV (max_age=70 → ✅ OK), Agribank (max_age=65 → ✅ OK, bằng đúng giới hạn), ACB (max_age=65 → ✅ OK, bằng đúng giới hạn), Vietcombank (max_age=75 → ✅ OK); chatbot phải nêu rõ trường hợp bằng đúng giới hạn (=65) là đủ điều kiện hay không tùy theo quy định "không quá" hay "dưới" của từng ngân hàng; kiểm tra `min_loan_term_years` không loại bất kỳ ngân hàng nào với kỳ hạn 10 năm (120 tháng); với thu nhập kinh doanh, nhắc yêu cầu hồ sơ chứng minh thu nhập phi lương (sao kê doanh thu, báo cáo tài chính, hợp đồng kinh doanh) của từng ngân hàng.
