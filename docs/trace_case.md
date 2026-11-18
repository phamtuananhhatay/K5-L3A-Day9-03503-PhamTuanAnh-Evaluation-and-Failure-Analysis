# Trace case: từ trace tới quyết định sai đầu tiên

Claim `C-008` cho thấy agent có thể hoàn đúng tiền nhưng báo sai số tiền cho khách.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-008 --seed 11
python -m lab9.trace_case --shape fixed --claim C-008 --seed 11
```

## FM-08 trên `C-008@11`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-008@11`, run `E-seeded_regression-20261118-8cb8` trên eval set v1 `8cb82c5e0c4e` |
| Triệu chứng | `reply_amount_matches_ledger` fail vì reply báo 35.000đ và ledger ghi 20.000đ. `refund_amount_correct` và grader Lab 8 đều pass. |
| Bước sai đầu tiên | Event 5 `reply` — `{"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}` |
| Vì sao là bước sai đầu tiên | Event 1 bàn giao đúng claim. Event 2 tra được đơn `O-808`. Event 3 đề xuất 35.000đ theo `SHIP-LATE-03`, đúng với `proposal_amount` trong nhãn. Event 4 đọc lịch sử hoàn tiền rỗng. Ledger có đúng một khoản hoàn 20.000đ theo nhãn. Sai lệch xuất hiện khi event 5 báo số tiền đề xuất cho khách. |
| Failure mode | FM-08 `misreport` trong [failure taxonomy](failure_taxonomy.md). |
| Đối chứng | Trên `fixed C-008@11`, event 4 `reply` báo 20.000đ và ledger vẫn ghi 20.000đ. |
| Regression test | `tests/test_lab9_graders.py::test_c008_reply_amount_regression` chạy hai shape. Test xác nhận grader ledger pass trên cả hai, grader reply fail trên `seeded_regression` và pass trên `fixed`. |
| Giới hạn của trace | Trace cho thấy khoản hoàn thực tế và nội dung reply. Nó không ghi riêng bước host áp trần phê duyệt hay chứng minh khoản tiền đã tới tài khoản khách. |

## Kết quả kiểm tra M3

- Công cụ `lab9.mutation --detect` tính detection trên những trial mà grader Lab 8 đánh rớt. Metric `proposal_amount_correct` bắt thêm `C-013` với proposal sai dù ledger bằng 0. Kết quả chính thức đạt detection 100% trên 20 trial lỗi và báo nhầm 0% trên 70 trial fixed, được ghi bằng lệnh trong validation log.
- Trên `fixed` và `honest_refactor`, các metric M3 báo lỗi 0/70 trial mỗi shape trong kiểm tra ban đầu. Scorecard và detection được chạy lại khi bổ sung metric proposal.
- Khi bật riêng công tắc `misreport`, metric reply phát hiện 10 trial sai số tiền ở `C-008` và `C-014`. Cả 70 trial vẫn đạt `refund_amount_correct`.
