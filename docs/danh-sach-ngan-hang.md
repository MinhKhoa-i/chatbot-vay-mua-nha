# Danh sách 8 ngân hàng thương mại và nguồn dữ liệu vay mua nhà

> **Tài liệu phục vụ Dự án:** Chatbot Tư vấn Vay Mua Nhà  
> **Người thực hiện:** Vương (Nhóm Dữ liệu)  
> **Ngày rà soát & cập nhật:** 31/10/2026  
> **Trạng thái:** Hoàn thành nhiệm vụ chọn 5–8 ngân hàng và xác định nguồn dữ liệu website (Task 11)

---

## 1. Tiêu chí lựa chọn ngân hàng

Để phục vụ đối tượng khách hàng cá nhân có nhu cầu vay mua nhà ở (nhà phố, căn hộ dự án, đất ở) tại Việt Nam, danh sách 8 ngân hàng được lựa chọn dựa trên 4 tiêu chí cốt lõi:

1. **Thị phần & Uy tín tín dụng bất động sản:** Gồm nhóm 4 ngân hàng thương mại có vốn Nhà nước (Big 4: Vietcombank, BIDV, VietinBank, Agribank) và nhóm 4 ngân hàng TMCP tư nhân hàng đầu có quy mô gói vay bán lẻ lớn (Techcombank, MB Bank, VPBank, ACB).
2. **Tính công khai & Minh bạch của nguồn dữ liệu:** Ngân hàng có cổng thông tin điện tử chính thức, đăng tải công khai biểu mẫu, quy trình, điều kiện vay, hạn mức, thời hạn và lãi suất các gói vay mua nhà.
3. **Đa dạng về chính sách vay:** Bao gồm các gói vay với đa dạng phương thức trả nợ (gốc đều lãi giảm dần, niên kim cố định), thời hạn vay từ 20 đến 35-45 năm, tỷ lệ tài trợ LTV từ 70% đến 100%.
4. **Sự tương thích với dữ liệu hiện có của dự án:** Kết nối liền mạch với các tài liệu quy trình vay ([quy-trinh-vay.md](quy-trinh-vay.md)) và bộ câu hỏi thường gặp ([faq.json](../data/faq.json)).

---

## 2. Bảng tổng hợp danh sách 8 ngân hàng và nguồn dữ liệu

| STT | Mã NH | Tên thương mại | Tên đầy đủ | Tên sản phẩm / Gói vay | Nguồn website chính thức (Trang sản phẩm) | Lãi suất ưu đãi tham khảo* | LTV tối đa | Thời hạn tối đa |
|:---:|:---:|:---|:---|:---|:---|:---:|:---:|:---:|
| 1 | **VCB** | Vietcombank | Ngân hàng TMCP Ngoại thương Việt Nam | Vay mua nhà ở, đất ở *(Gói Nhà Mới Thành Đạt / Nhà Mới An Cư)* | [vietcombank.com.vn](https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Vay-mua-nha-dat) | Từ 5.2% – 7.5%/năm | 100% HĐMB / 70% TSBĐ | 30 năm |
| 2 | **BIDV** | BIDV | Ngân hàng TMCP Đầu tư và Phát triển Việt Nam | Vay nhu cầu nhà ở *(Gói Ngôi nhà đầu tiên)* | [bidv.com.vn](https://bidv.com.vn/bidv/privatecustomer/dichvunganhang/tindung/vaynhucaunhao) | Từ 5.5% – 7.0%/năm | 100% phương án / 80% TSBĐ | 30 năm |
| 3 | **TCB** | Techcombank | Ngân hàng TMCP Kỹ Thương Việt Nam | Vay mua bất động sản có Giấy chứng nhận | [techcombank.com](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o) | Từ 3.99% – 6.8%/năm | 80% TSBĐ | 35 – 45 năm |
| 4 | **CTG** | VietinBank | Ngân hàng TMCP Công Thương Việt Nam | Cho vay mua, xây dựng, sửa chữa nhà ở | [vietinbank.vn](https://www.vietinbank.vn/vn/ca-nhan/cho-vay/mua-xay-dung-sua-chua-nha-o-nhan-chuyen-nhuong-qsd-dat-20150529141014.html) | Từ 5.8% – 7.2%/năm | 80% TSBĐ | 30 năm |
| 5 | **VBA** | Agribank | Ngân hàng Nông nghiệp và PTNT Việt Nam | Cho vay mua nhà ở, chuyển nhượng QSDĐ ở | [agribank.com.vn](https://www.agribank.com.vn/vn/ca-nhan/san-pham/vay-von-tin-dung/cho-vay-mua-nha-o) | Từ 6.0% – 7.5%/năm | 85% TSBĐ | 25 – 30 năm |
| 6 | **MB** | MB Bank | Ngân hàng TMCP Quân Đội | Cho vay mua nhà đất, căn hộ dự án | [mbbank.com.vn](https://www.mbbank.com.vn/ca-nhan/vay/vay-mua-nha-dat/4) | Từ 6.5% – 7.9%/năm | 80% TSBĐ | 30 năm |
| 7 | **VPB** | VPBank | Ngân hàng TMCP Việt Nam Thịnh Vượng | Vay mua nhà đất, nhà phố, chung cư | [vpbank.com.vn](https://www.vpbank.com.vn/ca-nhan/vay/vay-mua-nha) | Từ 5.9% – 7.5%/năm | 80% – 85% TSBĐ | 30 – 35 năm |
| 8 | **ACB** | ACB | Ngân hàng TMCP Á Châu | Vay mua nhà, đất ở | [acb.com.vn](https://acb.com.vn/khach-hang-ca-nhan/vay/vay-mua-nha-dat) | Từ 6.5% – 8.0%/năm | 80% TSBĐ | 25 – 30 năm |

*\*Lưu ý: Lãi suất ưu đãi chỉ áp dụng trong kỳ đầu (từ 3, 6, 12, 24 hoặc 36 tháng tùy gói); sau ưu đãi lãi suất sẽ được điều chỉnh theo quy định của từng ngân hàng.*

---

## 3. Chi tiết từng ngân hàng và phương thức khai thác dữ liệu

### 3.1. Vietcombank (VCB)
* **Đặc điểm chính:** Lãi suất cạnh tranh, quy trình thẩm định chặt chẽ, hỗ trợ thời hạn vay dài đến 30 năm, hạn mức vay tối đa 50 tỷ đồng/khoản vay. Hỗ trợ cho vay mua nhà cho người thân (bố, mẹ, vợ, chồng, con).
* **Nguồn dữ liệu trực tiếp:**
  * Trang giới thiệu sản phẩm: [Vietcombank Vay mua nhà đất](https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Vay-mua-nha-dat)
  * Trang chương trình ưu đãi "Nhà Mới Thành Đạt": [Nhà Mới Thành Đạt VCB](https://www.vietcombank.com.vn/vi-VN/KHCN/SPDV/Vay/Nha-moi-thanh-dat)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 5.2%/năm (cố định 12 tháng) hoặc 6.5%/năm (cố định 24 tháng).
  * Biên độ thả nổi sau ưu đãi: Khoảng 3.2% – 3.5%/năm cộng lãi suất cơ sở VCB.
  * Hạn mức: Tối đa 70% giá trị tài sản bảo đảm (TSBĐ), lên đến 100% nếu có thêm TSBĐ bổ sung.
  * Phí trả trước hạn: Năm 1: 1.5%; Năm 2–3: 1.0%; Năm 4–5: 0.5%; Từ năm thứ 6: 0%.

---

### 3.2. BIDV (BIDV)
* **Đặc điểm chính:** Gói vay đa dạng, mốc thời gian thẩm định phê duyệt công bố tối đa 05 ngày làm việc (khi đủ hồ sơ hợp lệ tại chi nhánh). Chương trình nổi bật: "Ngôi nhà đầu tiên".
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [BIDV Vay nhu cầu nhà ở](https://bidv.com.vn/bidv/privatecustomer/dichvunganhang/tindung/vaynhucaunhao)
  * Thông báo gói ưu đãi: [BIDV Gói vay ưu đãi Ngôi nhà đầu tiên](https://bidv.com.vn/bidv/ca-nhan/khuyen-mai/san-pham-vay/bidv-trien-khai-goi-vay-uu-dai-ngoi-nha-dau-tien-danh-cho-khach-hang-ca-nhan)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: 5.5%/năm (cố định 6 tháng) hoặc 6.2%/năm (cố định 12 tháng), 7.0%/năm (cố định 24 tháng).
  * Lãi suất sau ưu đãi: Lãi suất tiết kiệm 24 tháng + biên độ từ 3.5% – 4.0%/năm.
  * Hạn mức: Tối đa 100% nhu cầu vốn vay (phụ thuộc giá trị tài sản bảo đảm).
  * Thời hạn vay: Tối đa 30 năm (360 tháng).

---

### 3.3. Techcombank (TCB)
* **Đặc điểm chính:** Đón đầu công nghệ phê duyệt trực tuyến, thời hạn vay lên tới 35 năm (bất động sản thổ cư đủ điều kiện có thể lên đến 45 năm), ân hạn nợ gốc lên tới 24 tháng, minh bạch công thức tính gốc/lãi theo ngày thực tế.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Techcombank Vay mua bất động sản có GCN](https://techcombank.com/khach-hang-ca-nhan/vay/vay-mua-nha/vay-mua-nha-o)
  * Hướng dẫn thủ tục: [Techcombank Blog Thủ tục vay ngân hàng mua nhà](https://techcombank.com/thong-tin/blog/thu-tuc-vay-ngan-hang-mua-nha)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi tiêu chuẩn: 6.8%/năm (cố định 12 tháng). Mức từ 3.99%/năm là gói ưu đãi kỳ hạn ngắn (3 tháng) dành riêng cho nhóm khách hàng ưu tiên (Techcombank Priority/Private) hoặc dự án liên kết chỉ định, không áp dụng phổ thông.
  * Biên độ thả nổi sau ưu đãi: Lãi suất cơ sở Techcombank + biên độ 3.5%/năm.
  * Hạn mức: Tối đa 80% giá trị định giá tài sản bảo đảm.
  * Độ tuổi: Từ đủ 18 tuổi và không quá 70 tuổi tại thời điểm kết thúc thời hạn vay (đáo hạn).
  * Phí trả nợ trước hạn: Từ 1.0% trong 5 năm đầu, miễn phí (0%) từ năm thứ 6 trở đi.

---

### 3.4. VietinBank (CTG)
* **Đặc điểm chính:** Ngân hàng quốc doanh mạng lưới rộng lớn, lãi suất ổn định, điều kiện giải ngân linh hoạt cho các phương án nhà ở hình thành trong tương lai hoặc có sẵn Sổ đỏ/Sổ hồng.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [VietinBank Cho vay mua, xây dựng, sửa chữa nhà ở](https://www.vietinbank.vn/vn/ca-nhan/cho-vay/mua-xay-dung-sua-chua-nha-o-nhan-chuyen-nhuong-qsd-dat-20150529141014.html)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Từ 5.8%/năm (cố định 12 tháng) hoặc 6.8%/năm (cố định 24 tháng).
  * Hạn mức: Tối đa 80% tổng nhu cầu vốn hoặc 70% giá trị tài sản bảo đảm.
  * Thời hạn: Tối đa 30 năm (nhà ở xây dựng/mua mới), 15 năm (sửa chữa).

---

### 3.5. Agribank (VBA)
* **Đặc điểm chính:** Thế mạnh mạng lưới phủ kín từ thành thị đến nông thôn, mức độ an toàn cao, lãi suất ổn định, thủ tục đơn giản cho hộ gia đình và khách hàng cá nhân.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [Agribank Cho vay mua nhà ở](https://www.agribank.com.vn/vn/ca-nhan/san-pham/vay-von-tin-dung/cho-vay-mua-nha-o)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Từ 6.0%/năm đến 7.5%/năm tùy theo thời hạn cố định ưu đãi.
  * Hạn mức: Tối đa 85% giá trị định giá TSBĐ hoặc chi phí thực tế.
  * Thời hạn: Lên tới 25–30 năm.

---

### 3.6. MB Bank (MB)
* **Đặc điểm chính:** Ứng dụng ngân hàng số mạnh mẽ, thủ tục giải ngân nhanh, có các gói liên kết chủ đầu tư uy tín (Vinhomes, Novaland, Masterise...).
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [MBBank Vay mua nhà đất](https://www.mbbank.com.vn/ca-nhan/vay/vay-mua-nha-dat/4)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Khởi điểm từ 6.5%/năm (kỳ hạn ưu đãi 12 tháng).
  * Biên độ sau ưu đãi: Khoảng 3.5% – 3.8%/năm trên lãi suất tham chiếu.
  * Hạn mức: Tối đa 80% giá trị TSBĐ.
  * Thời hạn: Tối đa 30 năm (360 tháng).

---

### 3.7. VPBank (VPB)
* **Đặc điểm chính:** Phê duyệt nhanh, tiêu chí chứng minh thu nhập linh hoạt (chấp nhận thu nhập từ kinh doanh, cho thuê, góp vốn), hạn mức vay cao.
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [VPBank Vay mua nhà](https://www.vpbank.com.vn/ca-nhan/vay/vay-mua-nha)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Từ 5.9%/năm (ưu đãi 6 tháng) hoặc 7.5%/năm (ưu đãi 12 tháng).
  * Hạn mức: Tối đa 80% – 85% giá trị tài sản bảo đảm.
  * Thời hạn vay: Lên đến 35 năm.

---

### 3.8. ACB (ACB)
* **Đặc điểm chính:** Dịch vụ chăm sóc khách hàng cá nhân chu đáo, lãi suất minh bạch, hỗ trợ đa dạng phương thức trả gốc linh hoạt (theo tháng hoặc theo quý).
* **Nguồn dữ liệu trực tiếp:**
  * Trang sản phẩm: [ACB Vay mua nhà, đất ở](https://acb.com.vn/khach-hang-ca-nhan/vay/vay-mua-nha-dat)
* **Các trường dữ liệu trích xuất:**
  * Lãi suất ưu đãi: Từ 6.5%/năm (ưu đãi 12 tháng).
  * Thả nổi sau ưu đãi: Lãi suất cơ sở ACB + biên độ 3.5%/năm.
  * Hạn mức: Tối đa 80% giá trị tài sản bảo đảm.
  * Thời hạn: Tối đa 25 – 30 năm.

---

## 4. Khuyến cáo và nguyên tắc cập nhật nguồn dữ liệu

1. **Tính biến động của lãi suất:** Các mức lãi suất ưu đãi, biên độ thả nổi và chính sách chương trình tín dụng của ngân hàng thường thay đổi theo từng tháng/quý căn cứ vào định hướng điều hành của Ngân hàng Nhà nước và thanh khoản thị trường.
2. **Xác thực trực tiếp:** Mọi thông số thu thập từ website ngân hàng có giá trị tham khảo tại thời điểm cập nhật (`last_updated`). Chatbot cần hiển thị rõ ngày cập nhật và khuyến nghị khách hàng kiểm tra lại với chi nhánh/phòng giao dịch ngân hàng trước khi ký kết hồ sơ tín dụng chính thức.
3. **Tuân thủ quy định pháp luật:** Tuyệt đối không đưa các điều kiện ép mua bảo hiểm nhân thọ vào điều kiện bắt buộc, đảm bảo phù hợp với **Khoản 5 Điều 15 Luật Các tổ chức tín dụng số 32/2024/QH15** (có hiệu lực từ ngày 01/07/2024), nghiêm cấm: *"Tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, người quản lý, người điều hành, nhân viên của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài gắn việc bán sản phẩm bảo hiểm không bắt buộc với việc cung ứng sản phẩm, dịch vụ ngân hàng dưới mọi hình thức."* Chatbot cần trích dẫn chính xác nguyên văn điều khoản này khi tư vấn cho người dùng.
