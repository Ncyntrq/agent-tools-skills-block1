# Block 1 — Tra cứu chính sách đúng phiên bản

Ngày kiểm tra: 07/10/2026 (Asia/Bangkok). Làm trên `block1-stage-01-files/`
và `block1-stage-02-skills/`; các stage mẫu 00–04 giữ nguyên. Không sửa root uv
workspace, không commit hoặc push.

## 1. Triển khai và phạm vi

- Thêm `_list(workspace, path)` và `@tool list_files(path: str)` trong
  `tools/files.py` ở cả hai stage; tái sử dụng `_resolve`, `_error` và JSON.
  Chỉ liệt kê mục trực tiếp, sắp theo tên; mỗi mục có `name`, `path` tương đối
  workspace và `type`. Thư mục rỗng hợp lệ khác với lỗi đường dẫn/file.
- Export trong `tools/__init__.py`, đăng ký trong `agent.TOOLS`. Chặn absolute
  paths, traversal và symlink ra ngoài workspace. Hai stage dùng cùng mã tool;
  không sửa logic read/write hiện có.
- Policies có trong fixtures/workspace; stage 02 thêm `refund-policy/SKILL.md`
  và `references/answer-template.md` ở cả hai nơi để reset giữ tài nguyên.
- Catalog tự phát hiện skill; `prompts.py`, `skill_catalog.py`, `reset_workspace.py`
  không đổi. Skill hướng dẫn khám phá, chọn theo ngày mua, hỏi dữ liệu thiếu,
  tính ngày và dẫn tài liệu thực tế. Reference quy định cấu trúc câu trả lời.
  Không hard-code filenames, chính sách hoặc đáp án trong tool/system prompt;
  không thêm Bash/script.

### Environment/provider compatibility shim

Provider/model đã cấu hình trong lớp yêu cầu giữ `thought_signature` qua các
lượt tool call. Đường đi `ChatOpenAI` đã cài đặt bỏ metadata `extra_content`
khi chuyển response sang message và tạo request tiếp theo. Thử nghiệm
clean-scope riêng, dùng cùng cấu hình/thư viện nhưng không có adapter, tái hiện
HTTP 400 sau khi đọc skill: thiếu `thought_signature` ở `default_api:read_file`
(event/line 7), không có final answer.

Giữ subclass tối thiểu `CompatibleChatOpenAI` trong stage 02 như một
**environment/provider compatibility shim**. Adapter chỉ giữ metadata thực sự
do provider trả về theo message/call ID rồi gửi lại đúng tool call. Không tạo
signature giả, đổi model/provider, hard-code tên file/nội dung policy/đáp án,
hoặc sửa logic chọn chính sách. Bốn focused regression tests kiểm tra parallel
calls, ID lặp qua messages, deep-copy và payload thông thường.
Tham khảo [quy định của provider](https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures).

Failed diagnostics và clean-scope experiment được giữ **local**, không nằm
trong ZIP và không được tính là submission evidence.

## 2. Kiểm tra tool trực tiếp

Bằng chứng thật từ `list_files.invoke`, chỉ dùng dữ liệu lab giả:
`block1-verification/block1-stage-01-files-tools.json` và
`block1-verification/block1-stage-02-skills-tools.json`.

| Input | Kết quả thực tế ở cả hai stage | Kết quả | Vị trí JSON |
|---|---|---|---|
| `data` | `ok:true`, `empty` là directory, `note.md` là file; đúng thứ tự | PASS | `direct_tests[0].result` |
| `data/note.md` | `NOT_A_DIRECTORY` | PASS | `direct_tests[1].result` |
| `data/missing` | `DIRECTORY_NOT_FOUND` | PASS | `direct_tests[2].result` |
| `../outside` | `PATH_OUTSIDE_WORKSPACE` | PASS | `direct_tests[3].result` |
| `data/empty` | `ok:true, entries:[]` | PASS | `direct_tests[4].result` |

Offline evidence không thay thế model traces. Unit tests còn kiểm tra schema,
nonrecursive, invalid paths, symlinks, reset, registration, catalog, Streamlit
history/conversation và metadata-only prompt.

## 3. Năm tình huống model thật

Dùng cấu hình local qua settings loader; không mở thủ công, in hoặc sao chép
`.env`/API key. JSONL chứa observer events và câu trả lời thật, không mock hoặc
viết tay. Tất cả filenames dưới `block1-stage-02-skills/traces/`:

| Scenario | Kết quả thực tế | Kết quả | Trace |
|---|---|---|---|
| A-original | Cũ; 8 ngày; không đủ; dẫn policy cũ | PASS | `20261007-214246_67b3706b_turn01_595494ca.jsonl` |
| B-original | Mới; 10 ngày; đủ; không phí; dẫn policy mới | PASS | `20261007-214556_f415168c_turn01_5d0a8db2.jsonl` |
| missing-information | Hỏi trạng thái kích hoạt; không kết luận eligibility | PASS | `20261007-214620_2bd1c415_turn01_5930a690.jsonl` |
| A-renamed-fresh | Cũ; 8 ngày; không đủ; dẫn `archive-q7.md` | PASS | `20261007-214805_779813ff_turn01_86c8b3b1.jsonl` |
| B-renamed-fresh | Mới; 10 ngày; đủ; không phí; dẫn `document-x9.md` | PASS | `20261007-214811_a1ed3e81_turn01_dbbec6cb.jsonl` |

### Vị trí bằng chứng chính xác

L là số dòng từ 1, cũng bằng `sequence` trong mọi event. Call/result là
`tool_started/tool_finished`; policy paths có tiền tố `data/policies/`.

| Scenario | Schema/history mới | Skill call/result | list_files call/result | Policy read_file call/result | Reference call/result | Final |
|---|---|---|---|---|---|---|
| A-original | L2 | L4/L5 | L8/L9 | policy-before-oct.md L12/L13; policy-from-oct.md L16/L17 | L20/L21 | L24 |
| B-original | L2 | L4/L5 | L8/L9 | policy-from-oct.md L12/L13 | L16/L17 | L20 |
| missing-information | L2 | L4/L5 | L8/L9 | policy-from-oct.md L12/L13 | L16/L17 | L20 |
| A-renamed-fresh | L2 | L4/L5 | L8/L9 | archive-q7.md L12/L15; document-x9.md L13/L14 | L18/L19 | L22 |
| B-renamed-fresh | L2 | L4/L5 | L8/L9 | archive-q7.md L12/L13; document-x9.md L16/L17 | L20/L21 | L24 |

Mọi model request có đúng `read_file`, `write_file`, `list_files`. L8 gọi
`list_files("data/policies/")`; L9 trả filenames/paths dùng ở policy reads sau
đó. Skill/reference/policy tool results thành công xuất hiện trong request kế
tiếp. B gốc và missing-information đọc policy mới; A gốc và hai renamed runs
đọc cả hai. Không khẳng định mọi run đọc cả hai policies.

Final A từ chối vì 8 > 7; final B chấp nhận vì 10 <= 14, chưa kích hoạt, không
phí. Missing-information chỉ hỏi trạng thái kích hoạt, không tự giả định.
A/B dẫn đúng document path; finals sau đổi tên dẫn paths mới.

## 4. Đổi tên, giữ nội dung và conversation mới

Sau baseline runs: `policy-before-oct.md` -> `archive-q7.md`,
`policy-from-oct.md` -> `document-x9.md`. SHA-256 trước/sau bằng nhau:

| Policy | SHA-256 trước và sau |
|---|---|
| Cũ | `652e47574ee52c975b13624198cbb527a9ae28c18c799cf1ab339e16eafd7d2d` |
| Mới | `4d37991bdb1ce4b178eabe1a59119a11efae8ff4ed930457ad56565a7e39db48` |

Fixtures giữ tên gốc; stage-02 workspace giữ tên mới. Skill/reference không đổi
và workspace vẫn bằng bytes fixtures. Năm conversation IDs riêng:

| Scenario | Conversation ID |
|---|---|
| A-original | `67b3706b8a68421faca3deecb84eef3a` |
| B-original | `f415168c0cb24e06a88de306494594d6` |
| missing-information | `2bd1c41567f5426c9fc46cb3975f3dd7` |
| A-renamed-fresh | `779813ffed544f3aa85417af53ea43a6` |
| B-renamed-fresh | `a1ed3e81ab954eab979d1e4ba1e05dd8` |

L2 mỗi trace chỉ có một user message đúng scenario, không assistant/tool
history cũ; `chat_turn=1`. Mỗi run tạo model/graph/Observer mới, không checkpointer.
Hai renamed runs khám phá tên mới tại L9, đọc tài liệu và giữ kết luận.

## 5. Full tests sau cleanup và tính nhất quán source/evidence

Chạy lại complete suites trên Ubuntu WSL/Python 3.12.3, pytest 9.1.1, với
langchain 1.4.3, langchain-openai 1.6.7, openai 3.26.0. Không skip symlink hoặc
Streamlit tests. Fixtures trỏ `.env`, workspace và traces vào dữ liệu tạm,
không đụng credentials/traces thật.

| Stage | Kết quả cuối | Bằng chứng |
|---|---|---|
| block1-stage-01-files | **49 passed**, 0 failed/error/skipped; 36.71s | `block1-verification/stage01-tests.xml` |
| block1-stage-02-skills | **62 passed**, 0 failed/error/skipped; 31.13s | `block1-verification/stage02-tests.xml` |

Command/runtime/counts có trong `block1-verification/test-results.json`.
Mỗi stage chạy `python -B -m pytest -q -p no:cacheprovider --junitxml=../block1-verification/stage01-tests.xml`
(stage 02 dùng `stage02-tests.xml`).

Sau live traces, cleanup chỉ khôi phục `CAPABILITY_TEXT` trong hai `config.py`
về bản gốc. Chuỗi này chỉ được dùng bởi `st.caption`, không vào model
prompt/request hoặc policy logic. Toàn bộ config còn lại giữ nguyên.
Agent, adapter, tool code/schema, prompts, policies, skills, dependencies và
năm accepted traces giữ đúng bytes của archive trước cleanup. Thay đổi khác
chỉ là report và script đóng gói local. Không đổi model/tool runtime sau
accepted traces; không coi test stubs là live verification mới.

ZIP giữ hai runnable projects, tests (gồm bốn adapter regression tests), năm
accepted JSONL, `analysis.md`, hai direct-tool reports và ba final-test reports.
Không đóng gói failed traces, clean-scope experiment, explainer HTML,
diagnostic/helper scripts hoặc audit/index reports trùng bằng chứng.
Không có `.env`, credential, virtual environment hoặc cache. `.env.example`
chỉ có giá trị rỗng; tests dùng credential giả. Các diagnostics và original-stage
checksum audit giữ local, không phải submission evidence.

## 6. Câu hỏi cuối bài

Tool cung cấp khả năng liệt kê filesystem mà model không tự có: tìm filenames
và paths hiện tại rồi dùng `read_file`. Skill cung cấp quy trình chọn policy
theo ngày mua, kiểm tra dữ liệu thiếu, tính ngày và trình bày bằng chứng; nó
không thay thế khả năng filesystem.

Nếu chỉ có `read_file(path)`, model cần biết chính xác path trước. Sửa prompt
không tạo khả năng liệt kê thư mục, nên không bảo đảm tìm file sau đổi tên tùy
ý. Hard-code filenames không giải quyết yêu cầu đổi tên và vi phạm đề bài.
