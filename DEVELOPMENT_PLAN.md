# Kế Hoạch Phát Triển Talent Radar

## Mục Tiêu Sản Phẩm

Talent Radar là hệ thống theo dõi và phân tích nội dung social media về
Vinsmart Future/VSF. Trong giai đoạn hiện tại, trọng tâm không phải là tự động
tạo nội dung hay chatbot AI, mà là lấy dữ liệu đúng ngữ cảnh và phân loại đúng:

- Lấy bài viết, comment và reply trên Facebook, TikTok, Threads.
- Chỉ giữ lại nội dung có liên quan đến VSF/Vinsmart Future.
- Phân loại nội dung theo mức độ liên quan, chủ đề, cảm xúc và mức cần xử lý.
- Cho phép người dùng chủ động chạy lấy dữ liệu, xem lịch sử, lọc và xuất kết quả.

## Kiến Trúc Đã Chốt

Hệ thống được tách thành hai phần chính.

### 1. Website Trung Tâm

Website trung tâm chạy trên FastAPI và React, giữ vai trò điều phối:

- Quản lý tài khoản người dùng Talent Radar.
- Quản lý các extension/trình duyệt đã kết nối.
- Quản lý nguồn cần theo dõi: group, post, keyword, hashtag, profile/page nếu có.
- Tạo job lấy dữ liệu khi người dùng bấm nút thực hiện.
- Lưu dữ liệu vào database chuẩn hóa.
- Lọc bài viết/comment có liên quan đến VSF.
- Phân loại, gắn nhãn và hiển thị kết quả.
- Cung cấp dashboard, bộ lọc, lịch sử chạy và export.

AI nếu tích hợp sẽ nằm ở website trung tâm/backend, không nằm trong extension.
Extension chỉ nên lấy dữ liệu và gửi về server.

### 2. Extension Đa Trình Duyệt

Extension chạy trên trình duyệt người dùng đã đăng nhập sẵn, gồm Cốc Cốc,
Chrome, Edge, Brave và các trình duyệt hỗ trợ Chromium extension. Firefox có
bản build riêng nếu cần.

Vai trò của extension:

- Kết nối với Talent Radar bằng mã ghép nối một lần.
- Dùng session/cookie đang có trong trình duyệt của người dùng.
- Mở tab nền hoặc tab đang hoạt động để đọc nội dung trên Facebook/TikTok/Threads.
- Chạy job chỉ khi website trung tâm tạo job.
- Đọc DOM của trang, trích xuất bài viết, comment, reply và metadata.
- Gửi từng lô kết quả về backend trong quá trình chạy, không đợi đến khi xong.
- Báo trạng thái `running`, `completed`, `failed` về backend.

Nguyên tắc quan trọng: hệ thống không tự ý quét nếu người dùng chưa bấm chạy
hoặc chưa có lịch được cấu hình rõ ràng.

## Phạm Vi Nền Tảng

### Facebook

Ưu tiên trước vì đây là nguồn dữ liệu chính.

Cần hỗ trợ:

- Group public và group người dùng đã join.
- Link bài viết cụ thể.
- Lấy bài viết theo khoảng thời gian, ví dụ hôm nay từ sáng đến hiện tại.
- Mở rộng comment/reply nếu có thể đọc được bằng giao diện hiện tại.
- Lọc nội dung liên quan VSF bằng bộ keyword và bộ phân loại backend.

Rủi ro:

- DOM Facebook thay đổi thường xuyên.
- Comment ẩn sau nút "Xem thêm", "Tất cả bình luận", "Phản hồi".
- Một số nội dung chỉ hiển thị khi tài khoản có quyền xem.

### TikTok

Cần hỗ trợ sau Facebook.

Nguồn cần đọc:

- Video/search theo keyword.
- Comment của video nếu tài khoản và giao diện cho phép xem.
- Hashtag hoặc kết quả tìm kiếm liên quan VSF.

Rủi ro:

- TikTok có cơ chế lazy-load và chống tự động hóa mạnh.
- Comment và thông tin tác giả cần test trực tiếp trên giao diện thật.

### Threads

Cần hỗ trợ sau khi Facebook ổn định.

Nguồn cần đọc:

- Search keyword.
- Bài đăng theo profile hoặc thread URL.
- Reply trong bài đăng.

Rủi ro:

- Giao diện web và selector có thể thay đổi.
- Một số tính năng search/phiên đăng nhập có thể khác nhau theo tài khoản.

## Bộ Lọc VSF

Bộ lọc hiện tại cần tập trung vào việc nhận diện các cách người dùng nói về VSF.
Nguồn keyword nên nằm trong `config/vsf_keywords.yaml` để dễ cập nhật.

Nhóm keyword cần bao phủ:

- Tên chính thức: `Vinsmart Future`, `VinSmart Future`, `VSF`.
- Cách viết gần đúng: `vin smart future`, `vinsmartfuture`, `vin future smart`.
- Cách nói tắt hoặc nhầm lẫn phổ biến: `vin đỏ`, `vin do`, `vsf`, `v s f`.
- Từ khóa theo ngữ cảnh từ file plan/yêu cầu người dùng.
- Keyword mở rộng do AI gợi ý, nhưng phải được người dùng duyệt trước khi áp dụng.

Nguyên tắc lọc:

- Bài viết không liên quan VSF thì không đưa vào bảng kết quả chính.
- Comment liên quan VSF có thể được giữ ngay cả khi bài viết gốc chỉ liên quan yếu.
- Nếu bài viết liên quan VSF, có thể giữ thêm comment bên trong để bảo toàn ngữ cảnh.
- Luôn lưu metadata số lượng quan sát được, số lượng đã giữ lại và lý do lọc.

## Phân Loại Nội Dung

Giai đoạn 1 dùng bộ luật xác định để ổn định pipeline.

Nhãn cần có:

- `relevance`: mức độ liên quan VSF.
- `topic`: tuyển sinh, việc làm, công nghệ, sản phẩm, tài chính, nội bộ, khác.
- `sentiment`: tích cực, trung lập, tiêu cực, không rõ.
- `urgency`: bình thường, cần xem, ưu tiên cao.
- `source_type`: post, comment, reply.
- `platform`: facebook, tiktok, threads.

Giai đoạn 2 bổ sung AI ở backend:

- Đề xuất keyword mới.
- Phân loại ngữ nghĩa tốt hơn keyword thủ công.
- Gom nhóm bài viết/comment cùng chủ đề.
- Tóm tắt điểm nóng theo ngày.
- Giải thích vì sao nội dung được đánh dấu liên quan VSF.

AI chỉ nên hỗ trợ phân tích sau khi đã có dữ liệu. Không để AI điều khiển trình
duyệt hoặc tự ý thu thập dữ liệu.

## Database Cần Hướng Tới

Database mục tiêu là PostgreSQL. Schema cần dùng chung cho cả 3 nền tảng.

Bảng nên có:

- `users`: tài khoản Talent Radar.
- `browser_agents`: extension/trình duyệt đã kết nối.
- `platform_connections`: trạng thái kết nối theo nền tảng.
- `sources`: group, post URL, keyword search, hashtag, profile/page.
- `collection_jobs`: mỗi lần lấy dữ liệu.
- `raw_items`: dữ liệu thô từ extension gửi về.
- `social_posts`: bài viết đã chuẩn hóa.
- `social_comments`: comment/reply đã chuẩn hóa.
- `classifications`: kết quả lọc và phân loại.
- `exports`: lịch sử export nếu cần.

Nguyên tắc:

- `external_id` phải gắn với `platform` để tránh trùng ID giữa các nền tảng.
- Lưu URL gốc và timestamp thu thập.
- Giữ dữ liệu thô để debug selector khi nền tảng thay đổi.
- Kết quả phân loại nên tách bảng riêng để có thể chạy lại khi đổi bộ lọc/AI.

## Luồng Chạy Chính

1. Người dùng cài extension và ghép nối với website trung tâm.
2. Người dùng đăng nhập Facebook/TikTok/Threads trên trình duyệt của mình.
3. Người dùng thêm source cần theo dõi: group, post URL, keyword hoặc hashtag.
4. Người dùng bấm "Lấy dữ liệu" trên website.
5. Backend tạo `collection_job` cho extension phù hợp.
6. Extension nhận job, mở trang cần đọc và lấy dữ liệu.
7. Mỗi bài viết/comment lấy được sẽ được gửi về backend theo lô nhỏ.
8. Backend import, lọc VSF và phân loại ngay khi nhận dữ liệu.
9. Website hiển thị kết quả trong mục Bài viết/Comment mà không cần đợi job kết thúc.
10. Khi job xong, backend cập nhật trạng thái và tổng kết.

## Việc Đã Có

- Website React/FastAPI thay thế UI Streamlit cũ.
- PostgreSQL migration ban đầu.
- Extension đa trình duyệt có build Chromium và Firefox.
- Cơ chế pairing code một lần giữa website và extension.
- API để extension heartbeat, claim job, gửi item và complete/fail job.
- Facebook/TikTok/Threads collector MVP trong extension.
- Bộ lọc VSF xác định ban đầu ở backend.
- Job mới ưu tiên executor `browser_extension`, không tự mở Cốc Cốc profile mới.

## Việc Cần Làm Tiếp

### Ưu Tiên 1: Ổn Định Facebook

- Test collector trên group/post thật mà người dùng đã join.
- Chuẩn hóa selector lấy post, author, content, thời gian, URL.
- Chuẩn hóa selector mở và lấy comment/reply.
- Thêm checkpoint để tiếp tục khi job dài bị dừng.
- Thêm log rõ ràng cho từng bước extension đang làm.
- Thêm thông báo trên UI khi extension offline, mất quyền, hoặc trang yêu cầu đăng nhập.

### Ưu Tiên 2: Kết Quả Và Bộ Lọc

- Hiển thị bài viết/comment ngay khi backend nhận được item mới.
- Thêm nút reload/sync cho danh sách bài viết.
- Cho phép lọc theo keyword, source, nền tảng, thời gian, relevance, sentiment.
- Hiển thị lý do vì sao bài viết/comment được đánh dấu liên quan VSF.
- Lưu version bộ keyword và version bộ phân loại.

### Ưu Tiên 3: TikTok Và Threads

- Kiểm thử collector trên trang search, hashtag, video/post URL thật.
- Chuẩn hóa metadata riêng của từng nền tảng về schema chung.
- Thêm fallback khi comment không đọc được do UI/quyền đăng nhập.
- Tách test fixture DOM cho từng nền tảng.

### Ưu Tiên 4: AI Backend

- Thêm AI classifier sau khi pipeline lấy dữ liệu đã ổn định.
- Bắt đầu bằng classify batch nhỏ, có cache kết quả.
- Cho phép người dùng duyệt keyword AI gợi ý.
- Không gửi dữ liệu nhạy cảm ra AI nếu chưa có cấu hình rõ ràng.

### Ưu Tiên 5: Vận Hành

- Script dev để build extension nhanh.
- Hướng dẫn reload extension sau mỗi lần sửa.
- Đóng gói extension khi sẵn sàng phân phối nội bộ.
- Thêm lịch chạy hằng ngày nếu người dùng bật cấu hình rõ ràng.
- Giám sát lỗi selector theo nền tảng.

## Tiêu Chí Hoàn Thành Gần Nhất

- Cài extension trên Cốc Cốc user Huy và ghép nối thành công với website.
- Bấm nút lấy dữ liệu Facebook từ website thì extension mới bắt đầu chạy.
- Lấy được bài viết trong group/post người dùng có quyền xem.
- Bài viết/comment liên quan VSF hiển thị trong mục Bài viết/Comment ngay khi nhận về.
- Nội dung không liên quan VSF không xuất hiện trong kết quả chính.
- Job có trạng thái rõ: `queued`, `running`, `completed`, `failed`.
- Lỗi đăng nhập, mất quyền, selector hỏng hoặc extension offline hiển thị thông báo dễ hiểu.
- Không tự mở browser profile mới, không xóa cookie và không tự crawl ngoài ý người dùng.
