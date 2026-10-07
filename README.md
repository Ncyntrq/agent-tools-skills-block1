# Agent Tools & Skills — Block 1

## 1. Mục tiêu bài tập

Bổ sung `list_files` để agent khám phá tài liệu chính sách ngay cả khi tên file
thay đổi. Skill `refund-policy` cung cấp quy trình chọn chính sách theo ngày mua,
kiểm tra điều kiện hoàn tiền và trả lời kèm đường dẫn tài liệu làm căn cứ.

## 2. Cấu trúc repository

| Thành phần | Vai trò |
|---|---|
| `block1-stage-01-files/` | Bản sao stage 01: thêm và đăng ký `list_files` |
| `block1-stage-02-skills/` | Bản sao stage 02: file tools, skill hoàn tiền và bằng chứng model thật |
| `block1-verification/` | Kết quả gọi tool trực tiếp, báo cáo unit tests và hồ sơ kiểm chứng local |
| [analysis.md](analysis.md) | Kết quả chi tiết và vị trí dòng/event trong traces |
| [Bao_cao.pdf](Bao_cao.pdf) | Báo cáo kỹ thuật tiếng Việt để nộp bài |

Các stage mẫu được giữ nguyên. Hai bản sao có `pyproject.toml`, `uv.lock` và
môi trường riêng; chúng không nằm trong danh sách members của uv workspace gốc.
Trong thư mục traces local còn có lần thử thất bại; chỉ năm traces được liệt kê
ở mục 8 là bằng chứng được chấp nhận.

## 3. Chức năng chính

- `list_files(path)` liệt kê các mục trực tiếp, không đệ quy, sắp theo tên.
  Mỗi mục có `name`, `path` tương đối workspace và `type` (`file`/`directory`).
- Tái sử dụng cơ chế kiểm tra đường dẫn; chặn absolute paths, traversal và
  symlink ra ngoài workspace. Đường dẫn không tồn tại hoặc là file trả lỗi rõ ràng.
- Agent dùng `list_files("data/policies/")`, rồi `read_file` các đường dẫn vừa
  khám phá. Tên policy không được hard-code trong tool hay system prompt.
- Skill chọn chính sách theo **ngày mua**, tính ngày lịch từ ngày yêu cầu hoàn,
  kiểm tra trạng thái kích hoạt và đọc answer template trước khi trả lời đủ dữ liệu.
- Nếu thiếu ngày mua, ngày yêu cầu hoặc trạng thái kích hoạt, agent hỏi bổ sung
  trước khi kết luận; không tự giả định sản phẩm chưa kích hoạt.

## 4. Chính sách dùng trong bài

| Quy định | Chính sách cũ | Chính sách mới |
|---|---|---|
| Ngày mua áp dụng | Trước 01/10/2026 | Từ 01/10/2026, gồm ngày này |
| Thời hạn yêu cầu hoàn | 7 ngày kể từ ngày mua | 14 ngày kể từ ngày mua |
| Phí nếu đủ điều kiện | 10% giá trị đơn hàng | Không thu phí |
| Trạng thái kích hoạt | Đã kích hoạt: không hoàn | Đã kích hoạt: không hoàn |

Số ngày = ngày yêu cầu hoàn − ngày mua, theo ngày lịch; không dùng ngày hiện tại
của máy. Bằng đúng giới hạn vẫn đạt điều kiện thời gian. Stage-02 workspace hiện
dùng `archive-q7.md` (cũ) và `document-x9.md` (mới); fixtures giữ tên ban đầu.

## 5. Các scenario kiểm thử

| Scenario | Ý nghĩa | Kết quả được ghi nhận |
|---|---|---|
| A-original | Mua 28/09; yêu cầu 06/10/2026; chưa kích hoạt | Cũ; 8 ngày; không đủ điều kiện |
| B-original | Mua 02/10; yêu cầu 12/10/2026; chưa kích hoạt | Mới; 10 ngày; đủ; không phí |
| missing-information | Như B nhưng thiếu trạng thái kích hoạt | Hỏi trạng thái; chưa kết luận |
| A-renamed-fresh | A sau đổi tên, conversation mới | Kết luận A không đổi; dẫn `archive-q7.md` |
| B-renamed-fresh | B sau đổi tên, conversation mới | Kết luận B không đổi; dẫn `document-x9.md` |

## 6. Kết quả kiểm thử

Kết quả đã lưu của complete suites: **Stage 01: 49 passed**;
**Stage 02: 62 passed**, không failure/error/skip. Môi trường ghi nhận:
Ubuntu WSL, Python 3.12.3, pytest 9.1.1. Unit tests dùng model giả để kiểm tra
cơ chế; năm JSONL được chấp nhận ghi model thật. Hai loại bằng chứng bổ sung nhau.

Xem `block1-verification/test-results.json`, `stage01-tests.xml`,
`stage02-tests.xml`, hai `*-tools.json`, các traces ở mục 8 và `analysis.md`.

## 7. Cách chạy

Cần Python **3.11+** theo hai stage-level `pyproject.toml` và
[uv](https://docs.astral.sh/uv/). Chạy PowerShell từ root repository;
không sync các bản sao qua workspace mẫu ở root.

```powershell
cd block1-stage-01-files
uv sync --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Điền cấu hình local bằng trình soạn thảo; giữ nguyên cấu hình lớp nếu đã có.
uv run --locked pytest -q -p no:cacheprovider
uv run --locked streamlit run app.py
```

Dừng ứng dụng bằng Ctrl+C trước khi chạy stage 02:

```powershell
cd ../block1-stage-02-skills
uv sync --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run --locked pytest -q -p no:cacheprovider
uv run --locked streamlit run app.py
```

Nhóm dependency `dev` chứa pytest và được sync mặc định. `--locked` giữ nguyên
lockfile. Trên bash/WSL, thay dòng `Copy-Item` bằng
`test -f .env || cp .env.example .env`; các lệnh uv giữ nguyên. Kết quả complete
suites đã được xác minh trên WSL; Windows bị hạn chế quyền symlink hoặc chặn DLL
có thể cần chạy tests trong WSL. Không cần API key để chạy unit tests.

| Biến cấu hình local | Ý nghĩa |
|---|---|
| `OPENAI_API_KEY` | Credential của provider; bắt buộc để gọi model thật |
| `MODEL_NAME` | Model hỗ trợ native tool calling; dùng cấu hình lớp |
| `OPENAI_BASE_URL` | Endpoint OpenAI-compatible tùy chọn |

Stage 02 giữ `CompatibleChatOpenAI` để bảo toàn provider-returned
`thought_signature` qua các lượt tool call của Gemini/OpenAI-compatible provider
đã cấu hình. Đây là environment/provider compatibility shim, không chứa logic
hoàn tiền và không thay đổi model/provider. Stage 01 giữ đường đi `ChatOpenAI`
của mẫu, không có shim này. Chạy lại với cấu hình lớp có thể gặp khác biệt
tương thích provider ở stage 01; bài nộp không khẳng định có live traces stage 01.

## 8. Bằng chứng và báo cáo

Năm traces được chấp nhận, dưới `block1-stage-02-skills/traces/`:

| Scenario | JSONL |
|---|---|
| A-original | `20261007-214246_67b3706b_turn01_595494ca.jsonl` |
| B-original | `20261007-214556_f415168c_turn01_5d0a8db2.jsonl` |
| missing-information | `20261007-214620_2bd1c415_turn01_5930a690.jsonl` |
| A-renamed-fresh | `20261007-214805_779813ff_turn01_86c8b3b1.jsonl` |
| B-renamed-fresh | `20261007-214811_a1ed3e81_turn01_dbbec6cb.jsonl` |

`analysis.md` chỉ rõ dòng/sequence của schema, skill, `list_files`, policy reads,
reference và final answer. `Bao_cao.pdf` trình bày thiết kế, kiểm thử, kiểm chứng
đổi tên và giới hạn. Diagnostics local không phải submission evidence.

## 9. Lưu ý bảo mật

`.env` và API keys không nằm trong archive bài nộp; không commit hoặc chia sẻ
credential. Tạo `.env` chỉ từ template khi chưa có file local, không ghi đè cấu
hình đã dùng. Không đưa credential vào prompts, traces, báo cáo hay repository.
