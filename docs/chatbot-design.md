# Thiết kế chatbot tư vấn vay mua nhà — LLM + RAG

> **Kiến trúc:** sử dụng LLM + Retrieval-Augmented Generation (RAG), kết hợp các quy tắc an toàn và dịch vụ nghiệp vụ xác định.
>
> **Phạm vi:** trợ lý cung cấp thông tin, giải thích và mô phỏng tham khảo về vay mua nhà tại Việt Nam; không phải hệ thống phê duyệt tín dụng, không đại diện ngân hàng đưa ra cam kết cho vay.

## 1. Mục tiêu và giới hạn hệ thống

### 1.1. Hệ thống giải quyết vấn đề gì?

Người chuẩn bị vay mua nhà thường cần biết quy trình, giấy tờ, lãi suất ưu đãi/thả nổi, phí, cách trả nợ và sự khác nhau giữa các sản phẩm ngân hàng. Các câu hỏi thường được diễn đạt tự nhiên, có thông tin bổ sung qua nhiều lượt và phụ thuộc vào nguồn đang còn hiệu lực.

Chatbot cần:

1. Trả lời tiếng Việt tự nhiên, hỗ trợ cách viết có dấu/không dấu và cách nói như “1,5 tỷ”, “trả góp 20 năm”.
2. Trả lời kiến thức từ tài liệu đã được kiểm duyệt, có nguồn và thông tin thời điểm phù hợp.
3. Phân biệt quy định chung, điều kiện của từng sản phẩm ngân hàng và giả định do người dùng cung cấp.
4. Hỏi lại khi câu hỏi thiếu dữ kiện quan trọng; không tự chọn ngân hàng, lãi suất hay điều kiện vay.
5. Lưu hội thoại an toàn, xử lý được mất kết nối, gửi lại và nhiều yêu cầu đồng thời.
6. Ở giai đoạn mở rộng, gọi công cụ tính toán và so sánh trên dữ liệu có cấu trúc thay vì để LLM suy diễn số liệu.

### 1.2. Phạm vi theo giai đoạn

| Nhóm chức năng                       | MVP: hỏi đáp có nguồn                                   | Mở rộng sau MVP                                          |
| ------------------------------------ | ------------------------------------------------------- | -------------------------------------------------------- |
| Quy trình, hồ sơ, thuật ngữ          | Có, dựa trên tài liệu đã duyệt                          | Cá nhân hóa checklist theo sản phẩm                      |
| Điều kiện, lãi suất, phí             | Chỉ trả lời khi có nguồn phù hợp, còn đủ độ mới         | Tra cứu phiên bản sản phẩm có cấu trúc                   |
| Hội thoại nhiều lượt                 | Lịch sử giới hạn và hỏi làm rõ                          | Bộ nhớ nhiệm vụ có kiểu dữ liệu rõ ràng                  |
| Tính khoản trả hàng tháng            | Không để LLM tự tính; dẫn sang công cụ khi đã tích hợp  | Công cụ mô phỏng với lịch trả nợ và giả định minh bạch   |
| So sánh ngân hàng                    | Không tuyên bố “tốt nhất” nếu thiếu dữ liệu tương đương | Bảng so sánh và bộ lọc sản phẩm có thể giải thích        |
| Kết nối nhân viên                    | Hiển thị kênh liên hệ được xác thực                     | Tạo yêu cầu tư vấn khi có đồng ý của người dùng          |
| Hồ sơ vay chính thức, CIC, giải ngân | Không thuộc phạm vi                                     | Chỉ xem xét trong dự án tích hợp được ngân hàng cho phép |

### 1.3. Những điều chatbot không được làm

- Không khẳng định “chắc chắn được duyệt”, tự chấm điểm tín dụng hoặc thay ngân hàng quyết định cấp tín dụng.
- Không bịa lãi suất, phí, thời gian xử lý, yêu cầu bảo hiểm hoặc điều kiện pháp lý.
- Không coi tài liệu cũ là điều kiện sản phẩm hiện tại; ngày tải về không đồng nghĩa với ngày có hiệu lực.
- Không mặc định tỷ lệ vay trên giá mua bằng tỷ lệ vay trên giá trị tài sản do ngân hàng định giá.
- Không yêu cầu OTP, mật khẩu, số thẻ hoặc tải hồ sơ tài chính/giấy tờ định danh lên chat MVP.
- Không coi câu trả lời cũ của mô hình là nguồn chứng minh cho câu trả lời mới.

## 2. So sánh LLM + RAG và Rasa

### 2.1. Cần so sánh đúng đối tượng

**LLM + RAG** là một cách tổ chức hệ thống: tìm bằng chứng liên quan rồi cho mô hình diễn giải. **Rasa** là nền tảng hội thoại. Hai khái niệm không loại trừ nhau: Rasa có thể tích hợp RAG qua custom action hoặc các khả năng của Rasa Pro.

Cần phân biệt:

- **Rasa Open Source theo hướng NLU truyền thống:** intents, entities, slots, forms, rules/stories và custom actions. Cần dữ liệu huấn luyện và bảo trì hành vi hội thoại.
- **Rasa Pro/CALM:** dùng LLM hỗ trợ điều khiển hội thoại theo flows, có khả năng Enterprise Search/RAG tùy phiên bản và giấy phép. Không nên mô tả toàn bộ Rasa là “chỉ chạy rule, không có LLM”.

### 2.2. Đánh giá cho dự án này

| Tiêu chí                              | LLM + RAG tự tổ chức                                                       | Rasa NLU truyền thống                                                         | Rasa Pro/CALM                                                     |
| ------------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Hỏi đáp tài liệu dài, câu hỏi đa dạng | Phù hợp trực tiếp; phụ thuộc retrieval và chất lượng nguồn                 | Cần thiết kế intent/FAQ hoặc tích hợp retrieval riêng                         | Có thể tích hợp tìm kiếm/RAG                                      |
| Kiến thức sản phẩm thay đổi           | Cập nhật tài liệu/index, không cần huấn luyện lại LLM chỉ để đổi kiến thức | Câu trả lời có thể cập nhật độc lập; thay đổi NLU/luồng cần bảo trì tương ứng | Cập nhật kho tri thức và flows theo thay đổi                      |
| Thu thập thông tin theo quy trình     | Cần tự xây state machine/schema validation                                 | Mạnh ở forms, slot validation, rules                                          | Mạnh ở flows và cơ chế quản lý hội thoại                          |
| Kiểm soát câu trả lời                 | Phải bổ sung grounding, từ chối và kiểm tra đầu ra                         | Dễ kiểm soát câu trả lời mẫu; vẫn có lỗi NLU/routing                          | Có kiểm soát theo flows nhưng vẫn phải quản trị rủi ro LLM        |
| Dữ liệu chuẩn bị                      | Kho tài liệu được duyệt + bộ câu hỏi đánh giá                              | Dữ liệu intent/entity + stories/rules + nội dung trả lời                      | Flows, dữ liệu nghiệp vụ, cấu hình mô hình và kho tri thức        |
| Chi phí vận hành                      | Embedding, token suy luận, DB, kiểm duyệt, đánh giá                        | Hạ tầng, huấn luyện/bảo trì NLU; không nhất thiết có token LLM                | Hạ tầng + giấy phép theo điều khoản + chi phí mô hình nếu dùng    |
| Triển khai nội bộ                     | Có thể dùng model nội bộ nếu tài nguyên và chất lượng phù hợp              | Có thể triển khai nội bộ                                                      | Cần kiểm tra điều khoản và cấu hình triển khai của phiên bản chọn |
| Tận dụng code hiện có                 | Cao: đã có FastAPI, RAG, worker, pgvector, hội thoại                       | Phải tích hợp thêm runtime/tracker/actions và quyết định nơi giữ state        | Phải đánh giá migration, license và ranh giới state               |
| Độ phức tạp MVP hiện tại              | Thấp hơn do tiếp tục nền tảng có sẵn                                       | Tăng thêm một tầng quản lý hội thoại                                          | Chưa có nhu cầu đủ rõ để biện minh việc bổ sung nền tảng          |

Đây là đánh giá định tính theo nhu cầu và code của dự án, không phải benchmark chứng minh một công nghệ luôn tốt hơn công nghệ khác.

### 2.3. Quyết định và hệ quả

**Chọn LLM + RAG có kiểm soát**, vì trọng tâm hiện tại là hỏi đáp kiến thức vay mua nhà có nguồn, trong khi repository đã có phần lớn nền tảng này.

Các nguyên tắc đi kèm quyết định:

1. **RAG để tìm và giải thích kiến thức;**
2. **Luồng hỏi đáp MVP là pipeline cố định**, không phải agent tự do gọi công cụ, duyệt web hoặc viết SQL.
3. **PostgreSQL là nguồn trạng thái chính**; không đưa thêm một tracker hội thoại song song trong Rasa.
4. Không fine-tune mô hình chỉ để cập nhật lãi suất hoặc tài liệu. Cập nhật dữ liệu và retrieval trước.
5. Chấp nhận phải đầu tư kiểm duyệt nguồn, đánh giá retrieval, chống prompt injection và quan sát chất lượng.

Chỉ đánh giá lại Rasa khi sản phẩm cần nhiều luồng giao dịch bắt buộc, nhiều kênh hội thoại hoặc công cụ quản trị flows cho đội vận hành, và lợi ích vượt chi phí chuyển đổi. Nếu dùng Rasa Pro/CALM, phải kiểm tra phiên bản, điều khoản và hạn mức giấy phép tại thời điểm triển khai; không mặc định mọi tính năng RAG của Rasa đều thuộc Open Source hoặc miễn phí không giới hạn.

## 3. Kiến trúc tổng thể đề xuất

### 3.1. Luồng kết nối

```text
Người dùng
    |
    v
Frontend React
    | HTTPS; JSON cho CRUD, fetch streaming cho chat SSE
    v
Reverse proxy / API boundary
    | xác thực hoặc anonymous session, giới hạn tốc độ/kích thước
    v
AI Service FastAPI
    |-- Conversation use cases --> PostgreSQL (state, messages, request ledger)
    |-- Chat orchestration
    |      |-- Local response / clarification
    |      |-- Knowledge retrieval --> PostgreSQL + pgvector
    |      |                           --> Embedding adapter
    |      |-- Grounded generation --> Chat model adapter
    |      `-- Business tools (giai đoạn mở rộng)
    |              |-- Loan calculator
    |              `-- Product comparison --> Structured product tables
    |
    `-- Knowledge administration --> Snapshot storage + ingestion jobs
                                            |
                                            v
                                      Ingestion worker
                                            |
                                 Extract -> chunk -> embed -> publish

Nhân sự quản trị/kiểm duyệt --> API quản trị có RBAC --> Knowledge administration
```

Không cho trình duyệt gọi trực tiếp model provider, PostgreSQL hoặc embedding provider. Khóa API chỉ tồn tại ở phía server. Việc tìm kiếm và nạp tài liệu đi theo hai luồng riêng; không OCR/embedding hàng loạt ngay trong request chat.

### 3.2. Trách nhiệm của từng tầng

| Tầng           | Trách nhiệm                                                        | Không được làm                               |
| -------------- | ------------------------------------------------------------------ | -------------------------------------------- |
| Presentation   | HTTP/SSE, validation request, xác thực, mã lỗi, serialize response | Chứa công thức tài chính hay SQL nghiệp vụ   |
| Application    | Điều phối turn, chọn nhánh, gọi ports, kiểm soát timeout/commit    | Phụ thuộc trực tiếp SDK nhà cung cấp         |
| Domain         | Kiểu dữ liệu, điều kiện nghiệp vụ, trạng thái, hợp đồng ports      | Đọc file prompt, gọi HTTP hay truy cập DB    |
| Infrastructure | Repository, pgvector, model/embedding adapters, mã hóa, storage    | Tự quyết định người dùng có được duyệt vay   |
| Worker         | Tác vụ ingestion nền có retry, lease và giới hạn tài nguyên        | Chấp nhận lệnh thực thi từ nội dung tài liệu |

Giữ cấu trúc ports/adapters hiện có. MVP không cần tách thêm nhiều microservice: một API process, một worker process và một PostgreSQL là đủ làm đơn vị triển khai ban đầu.

## 4. Thiết kế luồng hỏi đáp

### 4.1. Luồng xử lý một turn ở MVP

1. Kiểm tra session/chủ sở hữu, body schema, độ dài và rate limit.
2. Claim request bằng `conversation_id`, `client_request_id`, fingerprint và version. Nếu đã hoàn tất thì replay, không gọi model lần nữa.
3. Đọc snapshot lịch sử đã commit; không sử dụng phần trả lời chưa commit của turn lỗi.
4. Phân loại xã giao thuần túy hoặc câu hỏi cần kiến thức. “Chào bạn, lãi suất bao nhiêu?” phải vào nhánh kiến thức.
5. Nếu cần làm rõ phạm vi, hỏi một câu ngắn; không tự chọn ngân hàng hoặc suy đoán “gói đó” khi lịch sử có nhiều gói.
6. Tạo query từ câu hiện tại và ngữ cảnh người dùng liên quan; không đưa câu trả lời cũ của assistant vào kho bằng chứng.
7. Tìm nguồn được duyệt, published, đúng thời điểm và đúng phạm vi.
8. Nếu tìm kiếm thành công nhưng không đủ bằng chứng: trả lời thiếu nguồn/hỏi làm rõ; không gọi LLM để bịa phần còn thiếu.
9. Nếu embedding/retrieval gặp lỗi kỹ thuật: phát lỗi phù hợp, không giả thành “không tìm thấy thông tin”.
10. Nếu đủ bằng chứng: gọi LLM với prompt, lịch sử giới hạn và context có định danh nguồn.
11. Kiểm tra câu trả lời theo mức rủi ro; gắn trích dẫn hợp lệ và giới hạn phạm vi kết luận.
12. Commit atomically cặp message, trạng thái/version và kết quả replay; chỉ sau đó phát `done`.

**Hiện có:** nhánh xã giao/kiến thức, retrieval trước generation, timeout retrieval 15 giây, timeout model ở application 45 giây và cơ chế claim/commit. **Cần bổ sung:** xác thực, hỏi làm rõ có chính sách rõ ràng, kiểm tra phạm vi bằng chứng và kiểm tra phát biểu đầu ra. Timeout tổng phải bao gồm retry của adapter và nhỏ hơn thời hạn lease hoặc có gia hạn lease an toàn.

### 4.2. Hội thoại nhiều lượt

Hiện tại answer model nhận tối đa 20 message đã commit; query builder bổ sung tối đa hai câu hỏi gần đây không phải xã giao. Đây là ngữ cảnh nhẹ, chưa phải bộ nhớ hiểu mọi tham chiếu.

Đề xuất:

- Bổ sung giới hạn **token**, không chỉ số message, và dành ngân sách riêng cho instruction, lịch sử, bằng chứng và đầu ra.
- Khi chuyển chủ đề, không trộn ngân hàng/gói vay của chủ đề cũ vào query mới.
- Chỉ lưu thông tin cần thiết cho nhiệm vụ; không thu thập hồ sơ thu nhập để trả lời câu hỏi kiến thức chung.
- Nếu dùng summary cho hội thoại dài, lưu version; xem summary là ngữ cảnh có thể sai, không là bằng chứng sản phẩm.
- Không suy diễn việc người dùng xác nhận toàn bộ profile chỉ từ một câu “ừ” không rõ đối tượng.

### 4.3. Chính sách thiếu hoặc mâu thuẫn nguồn

| Tình huống                                | Hành vi cần có                                                                               |
| ----------------------------------------- | -------------------------------------------------------------------------------------------- |
| Không có đoạn liên quan                   | Nói rõ chưa đủ nguồn, hỏi bổ sung ngân hàng/sản phẩm hoặc hướng tới kênh chính thức          |
| Có nguồn cho một phần câu hỏi             | Trả lời phần được hỗ trợ; chỉ rõ phần chưa đủ dữ liệu                                        |
| Tài liệu hết hiệu lực                     | Loại khỏi tư vấn hiện tại; chỉ dùng cho câu hỏi lịch sử nếu có chế độ tra cứu theo thời điểm |
| Nguồn thiếu ngày hiệu lực                 | Không tự coi có hiệu lực vô thời hạn; áp dụng chính sách freshness và kiểm duyệt             |
| Hai phiên bản cùng sản phẩm trái nhau     | Áp dụng quy tắc phiên bản đã phê duyệt; nếu chưa xác định được thì không tự ghép giá trị     |
| Hai ngân hàng có điều kiện khác nhau      | Trình bày theo từng ngân hàng, không tổng hợp thành điều kiện chung                          |
| Model trả số liệu không có trong evidence | Chặn/loại phát biểu hoặc chuyển sang phản hồi an toàn                                        |
| Provider hoặc DB lỗi                      | Trả lỗi kỹ thuật có mã, retry có giới hạn; không đánh dấu turn thành công                    |

## 5. Thiết kế kho tri thức và ingestion

### 5.1. Nguồn dữ liệu

Ưu tiên nguồn sơ cấp: văn bản chính thức, trang sản phẩm, biểu phí, điều khoản hoặc thông báo của ngân hàng. Tài liệu nội bộ và bài tổng hợp chỉ dùng khi có người chịu trách nhiệm đối chiếu phạm vi.

Repository có `docs/quy-trinh-vay.md`, `docs/knowledge_base/sources.json` và `data/faq.json`. Đây là đầu vào tham khảo.

### 5.2. Metadata tối thiểu

| Nhóm       | Trường cần lưu                                                                              |
| ---------- | ------------------------------------------------------------------------------------------- |
| Định danh  | `document_id`, `logical_document_id`, `version_no`, `content_sha256`                        |
| Nguồn      | `title`, `source_url`, publisher, loại tài liệu                                             |
| Phạm vi    | `bank_code`, `product_type`, product identifier nếu có, khu vực/đối tượng áp dụng           |
| Thời gian  | `effective_from`, `effective_to`, `last_updated`, `retrieved_at`, thời điểm phải review lại |
| Kiểm duyệt | status, uploader, reviewer, thời điểm, lý do chấp thuận/từ chối                             |
| Xử lý      | ingestion status, parser/chunker version, embedding model/version/dimensions                |
| Truy xuất  | snapshot key, chunk ID, trang/mục, hash nội dung                                            |

Một số trường đã có, các trường publisher/product identifier/review deadline và version parser/chunker cần bổ sung khi triển khai. Quy ước hiệu lực đề xuất là khoảng `[effective_from, effective_to)`, phù hợp truy vấn hiện tại; phải chuyển đổi minh bạch khi nguồn ghi ngày kết thúc theo nghĩa bao gồm ngày đó.

### 5.3. Pipeline ingestion

1. Kiểm tra quyền upload, kích thước, định dạng thực, tên file và tính hợp lệ metadata.
2. Lưu snapshot content-addressed, tính SHA-256 và đăng ký job atomically cùng document metadata.
3. Worker claim job bằng lease; giới hạn CPU, bộ nhớ, số trang và thời gian xử lý.
4. Trích xuất nội dung. Hiện hỗ trợ PDF có text và TXT/Markdown; PDF scan cần OCR riêng hoặc báo không hỗ trợ, không publish tài liệu rỗng.
5. Chuẩn hóa Unicode, giữ heading/trang/bảng và đơn vị tiền/lãi suất. Không tách số khỏi điều kiện áp dụng.
6. Chunk theo cấu trúc. Mặc định hiện tại 500 token, overlap 80 token; đây là điểm bắt đầu để đánh giá, không phải thông số tối ưu đã được chứng minh.
7. Tạo embedding theo batch, kiểm tra số lượng, chiều vector, giá trị hữu hạn và version.
8. Ghi chunks rồi publish atomically. Không để retrieval thấy một document mới chỉ được index một phần.
9. Ghi kết quả, retry với backoff có giới hạn; job hết lượt chuyển dead/failed và được cảnh báo.

Với bảng lãi suất/biểu phí, cần giữ tiêu đề cột và chú thích trong cùng context. Nếu cần tính toán/so sánh, trích xuất thành dữ liệu có cấu trúc rồi kiểm duyệt, không chỉ chia thành đoạn văn.

## 6. Thiết kế retrieval và generation

### 6.1. Retrieval

**Hiện có:** cosine similarity kết hợp full-text tiếng Việt dùng cấu hình PostgreSQL `simple`; score lấy từ `GREATEST(vector_score, LEAST(text_score, 1.0))`, top 5, ngưỡng mặc định 0,15 và context giới hạn theo ký tự. Đây là hybrid search sơ bộ, không phải BM25/RRF hoặc xác suất tin cậy.

### 6.2. Tính tương thích embedding

Hiện adapter Qwen lấy vector nguồn 4096 chiều, cắt còn 1536 và chuẩn hóa; bảng chunks dùng `Vector(1536)`. Vì vậy không thể thay `EMBEDDING_MODEL` tùy ý rồi tiếp tục dùng index cũ.

Thiết kế cần:

- Chứng minh model hỗ trợ cách rút gọn chiều đang dùng hoặc chọn chiều native phù hợp.
- Dùng cùng model, preprocessing, dimensions và version cho query và document.
- Gắn index/corpus generation với embedding version; chỉ tìm trong tập tương thích.
- Khi thay embedding, tạo index generation mới, re-embed và kiểm thử trước khi chuyển traffic; giữ khả năng rollback. Cùng số chiều không đồng nghĩa cùng không gian vector.

### 6.3. Hợp đồng prompt và trích dẫn

Prompt gồm instruction cố định, nhiệm vụ hiện tại, lịch sử giới hạn và evidence được đánh dấu rõ. Nội dung người dùng/tài liệu là **dữ liệu**, không có quyền ghi đè instruction hoặc yêu cầu gọi công cụ.

Đầu ra kiến thức nên có:

1. Trả lời trực tiếp câu hỏi.
2. Điều kiện/phạm vi áp dụng và phần chưa đủ dữ liệu.
3. Trích dẫn đặt cạnh phát biểu quan trọng, đặc biệt với số liệu/phí/lãi suất.
4. Mốc hiệu lực hoặc thời điểm xác minh khi phù hợp.
5. Câu hỏi tiếp theo nếu cần.

Không chỉ nối danh sách tất cả nguồn retrieval vào cuối rồi coi là đã kiểm chứng. Cần lưu document/chunk IDs thực sự hỗ trợ câu trả lời; chỉ hiển thị URL được lấy từ metadata đáng tin cậy. Kiểm tra citation ID tồn tại chưa đủ chứng minh entailment; phát biểu quan trọng cần đối chiếu nội dung và được đánh giá bằng bộ test/người review.

Với nội dung số liệu sản phẩm hoặc pháp lý nhạy cảm, đề xuất **buffer toàn bộ câu trả lời để kiểm tra trước khi phát nội dung**. Streaming trực tiếp phù hợp hơn với nội dung rủi ro thấp; không thể thu hồi điều người dùng đã đọc chỉ bằng việc gửi lỗi sau đó. Kiểm tra nguồn lần nữa trước khi hoàn tất turn nếu document có thể bị thu hồi trong khi model đang trả lời.

## 7. Danh sách thông tin cần hỏi khách hàng

Quy ước mức độ cần thiết:

- **Nền:** hỏi khi bắt đầu tư vấn cá nhân hóa, nếu khách chưa cung cấp.
- **Mô phỏng:** cần cho phép tính tương ứng; có thể dùng giả định được khách xác nhận, nhưng phải gắn nhãn giả định.
- **Có điều kiện:** chỉ hỏi khi phục vụ lọc sản phẩm, đánh giá ngân sách hoặc tình huống cụ thể.
- **Tùy chọn:** khách được bỏ qua; chatbot phải nói rõ ảnh hưởng của thông tin còn thiếu.

| Nhóm               | Thông tin / trường đề xuất                                                      | Khi cần hỏi                                                  | Câu hỏi gợi ý và lưu ý                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mục tiêu           | Nhu cầu hỗ trợ (`consultation_goal`)                                            | Nền                                                          | “Bạn muốn tìm hiểu thủ tục, tính khoản trả hàng tháng hay so sánh gói vay?” Không hỏi thông tin tài chính nếu chỉ cần kiến thức chung.                                     |
| Mục tiêu           | Mục đích vay (`loan_purpose`)                                                   | Nền khi tư vấn sản phẩm                                      | “Bạn vay để mua nhà ở, mua căn hộ, xây/sửa nhà hay chuyển khoản vay hiện tại?” Xây/sửa hoặc tái cấp vốn cần nhánh và nguồn riêng, không áp điều kiện vay mua nhà mặc định. |
| Mục tiêu           | Thời điểm dự kiến mua/vay (`planned_borrowing_time`)                            | Có điều kiện                                                 | “Bạn dự kiến vay ngay hay trong khoảng bao lâu nữa?” Dùng khoảng tháng/quý; ưu đãi hiện tại không được coi là còn áp dụng vào thời điểm tương lai.                         |
| Bất động sản       | Giá mua hoặc ngân sách mua nhà (`purchase_price_vnd`)                           | Có điều kiện: xác định vốn thiếu, tỷ lệ tài trợ hoặc so sánh | “Căn nhà dự kiến có giá khoảng bao nhiêu?” Phân biệt giá chào bán, giá thỏa thuận và ngân sách; cho phép khoảng ước tính.                                                  |
| Bất động sản       | Loại nhà (`property_type`)                                                      | Có điều kiện: tư vấn sản phẩm/hồ sơ                          | “Bạn định mua căn hộ, nhà riêng/nhà đất hay nhà thuộc dự án?” Nếu là nhà ở xã hội, phân nhánh điều kiện/chương trình riêng từ nguồn được duyệt.                            |
| Bất động sản       | Tình trạng hình thành (`property_completion_status`)                            | Có điều kiện                                                 | “Nhà đã hoàn thiện hay đang xây dựng/hình thành trong tương lai?” Không gộp nhà đang xây và nhà đã hình thành vào cùng checklist.                                          |
| Bất động sản       | Khu vực (`property_location`)                                                   | Có điều kiện: phạm vi sản phẩm và tài sản                    | “Nhà ở tỉnh/thành nào? Nếu cần lọc chi tiết hơn, bạn có thể cho biết phường/xã hoặc tên dự án.” Ban đầu không cần địa chỉ chính xác, số căn hay tọa độ.                    |
| Bất động sản       | Tình trạng giấy tờ theo khách tự khai (`property_legal_status`)                 | Có điều kiện: checklist/phạm vi sản phẩm                     | “Bạn biết nhà đã có giấy chứng nhận hay hiện mới có hợp đồng mua bán không?” Chấp nhận “chưa rõ”; không yêu cầu tải bản chụp và không kết luận pháp lý từ mô tả.           |
| Bất động sản       | Giai đoạn mua nhà (`purchase_stage`)                                            | Tùy chọn                                                     | “Bạn đang tìm nhà, đã chọn nhà, đặt cọc hay ký hợp đồng rồi?” Giúp tư vấn bước tiếp theo; không yêu cầu gửi hợp đồng.                                                      |
| Khoản vay          | Số tiền muốn vay (`loan_amount_vnd`)                                            | Mô phỏng; hoặc suy ra sơ bộ từ giá mua và vốn tự có          | “Bạn muốn vay khoảng bao nhiêu?” Nếu suy ra, cần khách xác nhận; không tự gán bằng hạn mức tối đa quảng cáo.                                                               |
| Khoản vay          | Vốn tự có dành cho việc mua (`down_payment_vnd`)                                | Có điều kiện: tính vốn thiếu/khả năng đáp ứng phần trả trước | “Bạn dự kiến dùng bao nhiêu vốn tự có để thanh toán tiền nhà?” Phân biệt khoản này với tiền dự phòng và tiền dành cho thuế/phí.                                            |
| Khoản vay          | Thời hạn vay (`term_months`)                                                    | Mô phỏng                                                     | “Bạn muốn vay trong bao nhiêu năm, hoặc muốn thử vài thời hạn?” Chuẩn hóa về tháng; chưa chọn thì mô phỏng các phương án khách đồng ý.                                     |
| Khoản vay          | Phương thức trả nợ (`repayment_method`)                                         | Mô phỏng                                                     | “Bạn muốn gốc chia đều hay tổng gốc+lãi đều khi lãi suất không đổi?” Giải thích ngắn hai cách trước khi yêu cầu lựa chọn.                                                  |
| Khoản vay          | Ngân hàng/gói vay đang xem (`preferred_bank`, `product_ref`)                    | Có điều kiện                                                 | “Bạn đã có ngân hàng/gói vay muốn tìm hiểu chưa, hay muốn so sánh?” Không bắt buộc chọn ngân hàng để tính kịch bản giả định.                                               |
| Khoản vay          | Lãi suất và các giai đoạn áp dụng (`rate_schedule`)                             | Mô phỏng                                                     | “Bạn đã có mức lãi suất được tư vấn chưa? Mức đó áp dụng bao lâu?” Phân biệt khách tự khai, dữ liệu sản phẩm đã duyệt và giả định.                                         |
| Khoản vay          | Lãi sau ưu đãi (`post_promo_rate_assumption`)                                   | Mô phỏng có ưu đãi                                           | “Sau ưu đãi, bạn muốn thử kịch bản lãi suất nào?” Nếu khách chỉ biết biên độ, chưa thể xác định lãi thực tế khi thiếu lãi tham chiếu và kỳ điều chỉnh.                     |
| Khoản vay          | Ân hạn gốc (`principal_grace_months`)                                           | Có điều kiện                                                 | “Gói vay có ân hạn gốc không, trong bao lâu?” Chỉ đưa vào phép tính khi engine hỗ trợ và biết cách trả lãi/cộng dồn theo điều khoản.                                       |
| Khoản vay          | Dự kiến trả trước hạn (`prepayment_plan`)                                       | Tùy chọn: so sánh chi phí                                    | “Bạn có dự định trả thêm hoặc tất toán sớm không?” Hỏi thời điểm/số tiền ước tính khi cần; không mặc định phí trả trước bằng 0.                                            |
| Dòng tiền          | Thu nhập ròng hàng tháng (`net_monthly_income_vnd`)                             | Có điều kiện: khách muốn phân tích ngân sách trả nợ          | “Sau thuế và các khoản khấu trừ, thu nhập bình quân hàng tháng của bạn khoảng bao nhiêu?” Cho phép khoảng; xác định thu nhập cá nhân hay tổng hộ, tránh cộng trùng.        |
| Dòng tiền          | Nguồn và mức ổn định thu nhập (`income_sources`, `income_stability`)            | Có điều kiện: checklist hoặc kịch bản ngân sách              | “Thu nhập chính từ lương, kinh doanh, cho thuê hay nguồn khác? Có dao động theo tháng không?” Chỉ hỏi mức khái quát, không cần tên công ty, tài khoản hay sao kê.          |
| Dòng tiền          | Người cùng trả nợ (`co_borrower_included`, `co_borrower_income_vnd`)            | Có điều kiện                                                 | “Bạn dự kiến tự trả hay có người cùng trả? Thu nhập của họ đã nằm trong tổng bạn vừa nêu chưa?” Chỉ cần số tổng hợp; không cần tên hoặc giấy tờ người khác.                |
| Dòng tiền          | Tổng khoản trả nợ hiện tại mỗi tháng (`existing_monthly_debt_payments_vnd`)     | Có điều kiện: phân tích tỷ lệ trả nợ                         | “Hiện mỗi tháng bạn đang trả khoảng bao nhiêu cho các khoản vay/trả góp khác?” Hỏi nghĩa vụ trả hàng tháng, không nhầm với tổng dư nợ.                                     |
| Dòng tiền          | Chi phí sinh hoạt và nghĩa vụ cố định (`monthly_living_expenses_vnd`)           | Có điều kiện: ngân sách còn lại                              | “Chi phí sinh hoạt và các khoản cố định mỗi tháng khoảng bao nhiêu, chưa tính khoản vay mới?” Nêu rõ có/không bao gồm nợ hiện tại để tránh trừ hai lần.                    |
| Dòng tiền          | Mức trả hàng tháng mong muốn (`comfortable_monthly_payment_vnd`)                | Có điều kiện: chọn kịch bản                                  | “Mỗi tháng bạn muốn dành tối đa khoảng bao nhiêu để trả khoản vay mới?” Đây là ngân sách khách chọn, không phải hạn mức được ngân hàng phê duyệt.                          |
| Dòng tiền          | Quỹ dự phòng sau khi mua (`remaining_emergency_fund_vnd`)                       | Tùy chọn: phân tích rủi ro ngân sách                         | “Sau phần trả trước và chi phí mua nhà, bạn muốn giữ lại khoảng bao nhiêu tiền dự phòng?” Không đề nghị dùng hết khoản này làm vốn tự có.                                  |
| Tài sản bảo đảm    | Phương án bảo đảm (`collateral_plan`)                                           | Có điều kiện: lọc sản phẩm/hồ sơ                             | “Bạn dự kiến dùng chính căn nhà mua, tài sản khác hay hiện chưa rõ?” Không giả định mọi sản phẩm đều chấp nhận mọi loại tài sản.                                           |
| Tài sản bảo đảm    | Loại và khu vực tài sản (`collateral_type`, `collateral_location`)              | Có điều kiện khi dùng tài sản khác                           | “Tài sản dự kiến bảo đảm là nhà đất, căn hộ, tiền gửi hay loại nào, ở tỉnh/thành nào?” Chỉ hỏi phạm vi cần thiết, không yêu cầu số tài khoản/số giấy chứng nhận.           |
| Tài sản bảo đảm    | Giá trị ước tính/định giá (`collateral_value_vnd`, `valuation_basis`)           | Có điều kiện: minh họa tỷ lệ tài trợ                         | “Giá trị này là bạn ước tính hay đã được ngân hàng định giá?” Lưu riêng giá mua và giá trị bảo đảm; chỉ gọi là LTV tham khảo nếu chưa có định giá phù hợp.                 |
| Tài sản bảo đảm    | Quan hệ sở hữu (`collateral_ownership_category`)                                | Có điều kiện: checklist                                      | “Tài sản thuộc bạn, đồng sở hữu hay bên thứ ba?” Chỉ hỏi loại quan hệ; không yêu cầu danh tính chủ tài sản, không mặc định đã có sự đồng ý của họ.                         |
| Tài sản bảo đảm    | Đang thế chấp hoặc có vướng mắc theo tự khai (`collateral_encumbrance_status`)  | Có điều kiện                                                 | “Tài sản có đang bảo đảm khoản vay khác hoặc có vấn đề bạn đã biết không?” Cho phép không rõ/không chia sẻ; hướng ngân hàng xác minh, không kết luận có thể thế chấp.      |
| Điều kiện sản phẩm | Độ tuổi theo năm (`borrower_age_years`)                                         | Có điều kiện: đối chiếu tiêu chí tuổi của sản phẩm đã chọn   | “Bạn có thể cho biết tuổi hiện tại không? Không cần ngày sinh đầy đủ.” Không áp một ngưỡng tuổi chung cho mọi ngân hàng.                                                   |
| Điều kiện sản phẩm | Nhóm cư trú/quốc tịch theo phạm vi cần thiết (`residency_category`)             | Có điều kiện, chỉ khi nguồn sản phẩm yêu cầu                 | “Bạn thuộc nhóm khách hàng cư trú/quốc tịch nào theo điều kiện gói vay này?” Chỉ phục vụ tra điều kiện công bố, không thu số giấy tờ.                                      |
| Hồ sơ              | Loại giấy tờ chứng minh thu nhập có thể chuẩn bị (`income_evidence_categories`) | Có điều kiện: checklist                                      | “Bạn có thể chuẩn bị nhóm giấy tờ nào: xác nhận lương, sao kê hay hồ sơ kinh doanh?” Chỉ hỏi loại giấy tờ, không thu bản sao trong MVP.                                    |
| Ưu tiên            | Tiêu chí lựa chọn (`comparison_priorities`)                                     | Có điều kiện: so sánh                                        | “Bạn ưu tiên khoản trả thấp, tổng chi phí, lãi ổn định, thời hạn hay linh hoạt trả trước?” Cho phép chọn nhiều tiêu chí, không tự thay bằng tiêu chí lợi ích của bên bán.  |

## 8. Tích hợp tính toán khả năng vay và khoản trả nợ

### 8.1. Trạng thái thực tế và ranh giới kiến trúc

Nhánh hiện tại **chưa có `backend/finance/calculator.py`**, chưa có endpoint tính toán của backend và chưa có port calculator trong AI service. Tên đường dẫn trên là mục tiêu tích hợp module của bạn Định, không phải một import có thể dùng ngay. MVP chỉ hỏi đáp có nguồn; lời chào phải nói rõ chưa hỗ trợ tính toán, system prompt tiếp tục cấm LLM tự tính.

Khi module sẵn sàng, tái sử dụng công thức ở backend thay vì viết lại trong prompt, endpoint chat hay frontend:

- **Backend:** calculator là nơi duy nhất sở hữu công thức, quy tắc làm tròn và test nghiệp vụ; application use case của backend gọi module và presentation cung cấp API có version.
- **AI domain:** khai báo input/output có kiểu dữ liệu và port `LoanCalculator`; domain không import FastAPI, HTTP client hoặc package `backend`.
- **AI application:** use case thu thập/kiểm tra thông tin, yêu cầu xác nhận giả định, gọi port và xử lý lỗi. Tách khỏi use case hỏi đáp kiến thức hiện tại để không làm tăng phụ thuộc của mọi lượt chat.
- **AI infrastructure:** adapter HTTP triển khai port và gọi API calculator của backend với timeout/retry có giới hạn; composition root inject adapter. Hai service triển khai độc lập, không import chéo source tree.
- **AI presentation:** chỉ validation/serialize HTTP/SSE, không chứa công thức. LLM chỉ giải thích kết quả đã nhận; số tiền/kỳ hạn/lãi suất hiển thị từ output có cấu trúc, không để mô hình tạo lại con số.

**Trạng thái triển khai hiện tại:** `ai_service` đã có luồng mô phỏng annuity với lãi suất cố định toàn kỳ, `EstimateLoanUseCase` và adapter gọi loan calculator backend. Calculator chỉ được gọi sau khi đã thu thập đủ số tiền vay, thời hạn, lãi suất và khách hàng xác nhận kịch bản. Đây là mô phỏng tham khảo, không đánh giá khả năng chi trả hoặc quyết định duyệt vay.

### 8.2. Hợp đồng kết quả estimate trên SSE

Khi lượt chat hoàn tất, `ai_service` phát event SSE `done`. Payload giữ các trường hội thoại hiện có (`conversation_id`, `client_request_id`, `conversation_version`, `user_message_id`, `assistant_message_id`, `reply`) và có thêm trường `estimate`:

- Nếu calculator trả kết quả thành công sau xác nhận, `estimate` là object chứa `input.amount` (số nguyên VND), `input.years` (số nguyên năm), `input.rate` (chuỗi thập phân theo `%/năm`), `monthly_payment` (số nguyên VND), `total_interest` (số nguyên VND) và `updated_at`.
- Với lượt không tạo ra kết quả tính toán — ví dụ chat kiến thức, thu thập dữ liệu, chờ xác nhận hoặc hủy — `estimate` là `null`.
- `reply` vẫn là nội dung thân thiện để hiển thị cho người dùng; frontend dùng `estimate` để hiển thị/định dạng các giá trị số, không phân tích ngược số từ `reply`.
- Các giá trị trong object lấy từ response của calculator backend; LLM không tự tính, sửa hoặc suy diễn kết quả.

Ví dụ payload của event `done` khi mô phỏng thành công:

```json
{
  "conversation_id": "<uuid>",
  "client_request_id": "<uuid>",
  "conversation_version": 4,
  "user_message_id": "<uuid>",
  "assistant_message_id": "<uuid>",
  "reply": "Khoản trả hàng tháng khoảng 1.234.567 VND.",
  "estimate": {
    "input": {
      "amount": 1000000000,
      "years": 20,
      "rate": "9.5"
    },
    "monthly_payment": 8770000,
    "total_interest": 1104800000,
    "updated_at": "2026-10-31"
  }
}
```

Response hoàn tất được lưu cùng request ledger để replay trả lại cùng `reply` và `estimate` mà không gọi calculator lần nữa. Với response thành công đã lưu bởi phiên bản cũ nhưng chưa có trường này, luồng replay chuẩn hóa thành `estimate: null`.

### 8.3. Luồng mô phỏng hiện tại

1. Xác định khách muốn lịch trả nợ hay đánh giá ngân sách/khả năng vay. Tận dụng thông tin đã xác nhận trong hội thoại, hỏi từng dữ kiện còn thiếu theo mục 7; không hỏi cả bộ hồ sơ khi chỉ cần kiến thức chung.
2. Với lịch trả nợ: cần tiền vay, thời hạn, phương thức trả và lãi suất/lịch lãi suất có nguồn hoặc giả định được xác nhận. Với khả năng vay: cần thêm thu nhập ròng, nợ hiện tại, chi phí sinh hoạt và chính sách/ngân sách do khách chọn. Không mặc định một ngưỡng DTI chung cho mọi ngân hàng.
3. Xác nhận kịch bản: đơn vị tiền, tháng/năm, lãi suất năm dạng phần trăm hay tỷ lệ, giai đoạn ưu đãi, sau ưu đãi, phí được tính/chưa tính và quy tắc trả nợ. Nếu calculator không hỗ trợ lãi thay đổi/ân hạn thì từ chối kịch bản đó thay vì âm thầm thay bằng lãi cố định.
4. Application gọi calculator qua port. Input/output cần thống nhất với backend trước triển khai: phiên bản công thức, đơn vị, quy tắc làm tròn, giả định, lịch trả nợ và các kết quả tổng hợp. Không dùng con số trong văn bản RAG chưa kiểm duyệt trực tiếp làm tham số.
5. Nếu calculator thiếu dữ liệu, timeout hoặc lỗi validation: hỏi bổ sung/báo chưa tính được; **không chuyển sang cho LLM tự tính**. Không ghi thành kết quả mô phỏng thành công.
6. Hiển thị kết quả tham khảo, giả định và nguồn chính sách; phân biệt “khoản có thể trả theo ngân sách” với “hạn mức ngân hàng chấp thuận”. Không hứa đủ điều kiện vay.

### 8.2. Luồng dự kiến

1. Xác định khách muốn lịch trả nợ hay đánh giá ngân sách/khả năng vay. Tận dụng thông tin đã xác nhận trong hội thoại, hỏi từng dữ kiện còn thiếu theo mục 7; không hỏi cả bộ hồ sơ khi chỉ cần kiến thức chung.
2. Với lịch trả nợ: cần tiền vay, thời hạn, phương thức trả và lãi suất/lịch lãi suất có nguồn hoặc giả định được xác nhận. Với khả năng vay: cần thêm thu nhập ròng, nợ hiện tại, chi phí sinh hoạt và chính sách/ngân sách do khách chọn. Không mặc định một ngưỡng DTI chung cho mọi ngân hàng.
3. Xác nhận kịch bản: đơn vị tiền, tháng/năm, lãi suất năm dạng phần trăm hay tỷ lệ, giai đoạn ưu đãi, sau ưu đãi, phí được tính/chưa tính và quy tắc trả nợ. Nếu calculator không hỗ trợ lãi thay đổi/ân hạn thì từ chối kịch bản đó thay vì âm thầm thay bằng lãi cố định.
4. Application gọi calculator qua port. Input/output cần thống nhất với backend trước triển khai: phiên bản công thức, đơn vị, quy tắc làm tròn, giả định, lịch trả nợ và các kết quả tổng hợp. Không dùng con số trong văn bản RAG chưa kiểm duyệt trực tiếp làm tham số.
5. Nếu calculator thiếu dữ liệu, timeout hoặc lỗi validation: hỏi bổ sung/báo chưa tính được; **không chuyển sang cho LLM tự tính**. Không ghi thành kết quả mô phỏng thành công.
6. Hiển thị kết quả tham khảo, giả định và nguồn chính sách; phân biệt “khoản có thể trả theo ngân sách” với “hạn mức ngân hàng chấp thuận”. Không hứa đủ điều kiện vay.
