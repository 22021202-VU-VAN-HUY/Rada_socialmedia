# Talent Radar

## Kiến trúc mới theo Project Plan

Repo hiện bắt đầu được tách thành các phần có thể mở rộng:

- `talent_radar.api`: FastAPI backend cho source, classify, health check.
- `talent_radar.models`: SQLAlchemy models cho source, crawl run, item, insight, alert, review, cost log.
- `talent_radar.services`: Query Pack, rule classifier, source registry.
- `talent_radar.jobs`: daily collection job skeleton.
- `config/query_pack_vsf.yaml`: tên chính thức, alias, slang Gen Z, nhắc gián tiếp và exclusion.
- `config/source_registry.example.yaml`: nguồn Facebook/TikTok/Threads mẫu.

Chạy API local:

```powershell
pip install -e .
uvicorn talent_radar.api.main:app --reload
```

Đồng bộ source registry mẫu:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/sources/sync
```

Test classifier rule-based:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/classify `
  -ContentType "application/json" `
  -Body '{"text":"VSF deadline đăng ký khi nào?","platform":"facebook"}'
```

Chạy daily job skeleton:

```powershell
python -m talent_radar.jobs.daily_collect
```

Chạy bằng Docker Compose:

```powershell
docker compose up --build
```

Prototype dashboard cho kế hoạch MVP social listening VSF-first.

## Chạy dashboard mẫu

```powershell
pip install -e .
streamlit run src/talent_radar/dashboard/app.py
```

Dashboard hiện dùng dữ liệu mẫu trong `data/samples/dashboard_mock_data.json`.
Chưa có database, collector, agent hay AI thật; mục tiêu là giúp hình dung workflow sản phẩm trước:

- Nút `Đăng nhập` / `Đăng ký` ở góc trên bên trái
- Trang `Cài đặt` để liên kết Facebook, TikTok, Threads
- Trang `Quét group & từ khóa` để quản lý keyword, xem lần quét gần nhất và thử đọc group qua Graph API
- Tổng quan KPI
- Dòng nội dung VSF + bộ lọc
- Bản tóm tắt ngày
- Hàng chờ rà soát
- Sức khỏe nguồn dữ liệu
- Crawl thử nguồn công khai
- Xuất CSV từ bộ lọc hiện tại

## Đăng nhập, đăng ký và liên kết nền tảng

Góc trên bên trái của app có nút `Đăng nhập` và `Đăng ký`.
Sau khi vào app, trang `Cài đặt` hiển thị các connector:

- Facebook:
  - Nếu chưa cấu hình Meta App ID: nút `Mở Facebook để đăng nhập ngoài` chỉ mở `facebook.com/login`.
  - Nếu đã cấu hình Meta App ID: nút `Tiếp tục với Facebook` mở Facebook Login/OAuth để app nhận callback.
- TikTok: placeholder giao diện, chưa nối API.
- Threads: placeholder giao diện, chưa nối API.

Prototype không lưu mật khẩu, cookie hay session Facebook cá nhân.
Không dùng nick Facebook của người dùng để tự đăng nhập rồi scrape group.
Connector thật phải đi qua OAuth/API chính thức và chỉ chạy với quyền/scope đã được cấp.

Khi người dùng bấm `Mở Facebook để đăng nhập ngoài`, trình duyệt sẽ chuyển sang Facebook để đăng nhập thủ công.
Việc này không tự cấp token/quyền cho Talent Radar, vì website không được đọc cookie/session của `facebook.com`.

Khi người dùng bấm `Tiếp tục với Facebook`, trình duyệt sẽ chuyển sang Facebook OAuth.
Nếu người dùng đang đăng nhập Facebook trong browser, Facebook sẽ dùng phiên đó để hỏi quyền liên kết app.

Tham khảo tài liệu chính thức:

- Facebook Login: https://developers.facebook.com/docs/facebook-login/
- Meta Graph API: https://developers.facebook.com/docs/graph-api/
- Permissions: https://developers.facebook.com/docs/permissions/reference/

## Cấu hình Facebook OAuth

Copy `.env.example` thành `.env` hoặc set biến môi trường tương ứng. App sẽ tự đọc file `.env` ở thư mục project khi khởi động:

```powershell
copy .env.example .env
$env:FACEBOOK_APP_ID="..."
$env:FACEBOOK_APP_SECRET="..."
$env:FACEBOOK_REDIRECT_URI="http://localhost:8501/"
$env:FACEBOOK_GRAPH_API_VERSION="v20.0"
$env:FACEBOOK_SCOPES="public_profile"
streamlit run src/talent_radar/dashboard/app.py
```

Sau khi cấu hình, góc trên bên trái/sidebar sẽ hiện nút `Đăng nhập bằng Facebook`.
Bấm nút này sẽ trỏ sang Facebook Login thật. Nếu callback trả về `code`, dashboard tự đổi code lấy access token, đọc profile cơ bản qua Graph API và đăng nhập user vào app.

Nếu Facebook báo `Invalid Scopes: email`, hãy dùng scope tối thiểu trước:

```env
FACEBOOK_SCOPES=public_profile
```

Chỉ thêm lại `email` sau khi app đã được Meta cấp quyền/advanced access phù hợp.

Redirect URI trong Meta dashboard phải khớp chính xác với `FACEBOOK_REDIRECT_URI`. Nếu chạy theo cấu hình mặc định, hãy thêm:

```text
http://localhost:8501/
```

Lưu ý: đọc bài viết trong Facebook group không tự động khả dụng chỉ vì người dùng đã đăng nhập Facebook.
Nếu API/permission không cho phép đọc group posts, connector sẽ báo `blocked`; fallback đúng là CSV/JSON import hoặc nguồn export được cấp quyền.

## Quét group & keyword

Mục `Quét group & từ khóa` hỗ trợ:

- Nhập Facebook Group URL hoặc Group ID.
- Thêm/xóa/bật/tắt keyword thủ công.
- Gợi ý keyword tự động từ metadata public của group.
- Chọn khoảng thời gian quét.
- Hiển thị lần quét gần nhất, khoảng thời gian quét gần nhất và số bài match theo từng keyword.
- Thử gọi Facebook Graph API để lấy feed group nếu token/scope được Meta cho phép.

Cấu hình group mặc định:

```env
FACEBOOK_DEFAULT_GROUP_URL=https://www.facebook.com/groups/782850425639223/
```

Nếu Graph API trả lỗi thiếu quyền, cần kiểm tra permission/app review/advanced access của Meta. App không dùng cookie hay browser automation để né giới hạn.

## Crawl thử nguồn công khai

Tab/mục `Crawl công khai` có sẵn link:

```text
https://www.facebook.com/groups/782850425639223/
```

Nút crawl chỉ fetch HTML công khai bằng request thường, rồi trích text/metadata và tóm tắt thô.
Prototype không đăng nhập, không né CAPTCHA/login wall, không dùng stealth browser và không thu dữ liệu private.
Nếu Facebook chỉ trả metadata hoặc nội dung rỗng, dashboard sẽ hiển thị đúng kết quả đó.

## Phạm vi bản prototype

Bản này bám theo `DEVELOPMENT_PLAN.md`, nhưng chỉ dựng lớp giao diện, mock data, OAuth connector skeleton cho Facebook và một thử nghiệm crawl public tối giản.
Các phần ingestion, relevance engine, AI analysis, scheduler và API sẽ được nối sau khi scope/source inventory được duyệt.
