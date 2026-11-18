# Judge audit

Chạy từ `src/` với phán quyết của judge lưu sẵn trong CSV.

```powershell
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Lớp dương là `FAIL`. Judge cần đạt cả ba ngưỡng κ ≥ 0.6, precision ≥ 0.8 và recall ≥ 0.7.

| Tiêu chí | n | TP / FP / FN / TN | κ | Precision | Recall | Tỷ lệ lỗi judge báo → hiệu chỉnh | Quyết định |
|---|---:|---|---:|---:|---:|---|---|
| `tone_ok` | 100 | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | 28% → 30% | Đạt. Dùng để chấm giọng điệu. |
| `helpful` | 100 | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | 9% → 30% | Rớt κ và recall. Loại khỏi gate. |

## Audit thủ công

| Case | Tiêu chí | Judge | Người | Ai đúng và vì sao | Thay đổi đề xuất |
|---|---|---|---|---|---|
| `H-008` | `tone_ok` | PASS | FAIL | Người. Cách xưng «em» kết hợp với «rồi nha» và «check giúp em» quá suồng sã so với chuẩn chăm sóc khách hàng của LogiX. | Thêm cặp ví dụ về cách xưng hô và tiểu từ thân mật trong cùng câu. Chấm theo ngữ cảnh thay vì cấm riêng một từ. |
| `H-017` | `tone_ok` | PASS | FAIL | Người. «Bạn ơi» và «rồi nha» tạo giọng quá thân mật khi nói với khách lớn tuổi như ghi chú của ca này. | Cho judge biết ngữ cảnh xưng hô nếu có. Khi chưa rõ cách gọi khách, dùng «anh/chị» làm ví dụ đạt trong rubric. |
| `H-029` | `tone_ok` | PASS | FAIL | Người. Câu «không cần nhắn thêm» mang giọng ra lệnh dù câu trước có «Dạ, vui lòng». | Yêu cầu kiểm tra giọng điệu của từng câu, kể cả câu hướng dẫn cuối. Thêm ví dụ về cách thông báo thời gian chờ lịch sự. |
| `H-042` | `tone_ok` | FAIL | PASS | Người. Câu xác nhận lịch sự và cho biết số tiền cùng thời gian nhận. Ghi chú cho biết judge phạt vì thiếu lời xin lỗi. | Thêm ví dụ đạt cho xác nhận hoàn tiền ngắn gọn. Chỉ yêu cầu xin lỗi khi ngữ cảnh có bất tiện cần được thừa nhận. |
| `H-051` | `tone_ok` | FAIL | PASS | Người. «Refund» là thuật ngữ đội chăm sóc khách hàng LogiX cho phép trong ngữ cảnh này. | Cho phép thuật ngữ trong danh mục nội bộ. Xét độ dễ hiểu của cả câu khi dùng từ mượn. |
| `HL-015` | `helpful` | PASS | FAIL | Người. Reply báo đã hoàn 55.000đ cho đơn O-112, còn ledger ghi 40.000đ. | Dùng grader bằng code để đối chiếu số tiền reply với ledger. Thêm ví dụ câu trả lời lịch sự nhưng sai số tiền vào rubric. |

## Kết luận

`helpful` báo đúng cả 9 lỗi mà nó phát hiện (`TP=9`, `FP=0`), nhưng bỏ sót 21 trong 30 lỗi theo nhãn người (`FN=21`). Rogan–Gladen đưa tỷ lệ lỗi ước tính từ 9% lên 30% trên tập này. Quyết định dùng gate vẫn dựa trên khả năng phát hiện từng lỗi, thể hiện qua recall và κ.

Kết quả dựa trên hai CSV replay công khai. Sau khi sửa rubric, cần đánh giá lại trên tập held-out có nhãn người mới để đo hiệu quả trên các câu trả lời chưa dùng trong audit.
