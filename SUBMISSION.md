# Nộp bài (hạn 23:59 cùng ngày)
PR từ `starter/d09` → `main` của repo nhóm. Chấm commit cuối trước 23:59; commit sau hạn không tính.

## Core (nên xong trước 17:00)
- [x] `src/lab9/{stats,graders,evalset}.py` đã hoàn thành TODO M1–M4
- [x] `src/data/eval/eval_set_v1.jsonl` có `failure_modes`, `labels_v1.json` tách riêng
- [x] `docs/failure_taxonomy.md`, `docs/trace_case.md` (1 case + regression test), `docs/judge_audit.md`, `docs/eval_card.md`, `docs/PRD_v1.1.md`
- [x] `src/reports/baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` (sinh bằng script)
- [x] `src/harness_map.yaml` có section `eval` (mẫu: `src/harness_map.eval.yaml`)
- [x] Job `eval-gate` xanh; output gate exit 1 của `seeded_regression` có trong mô tả PR #1 và validation log

## Advanced / Expert (tới 23:59)
- [x] `src/config/fm_map.yaml`, `src/config/metric_spec_v2.yaml` (slices, `pass_hat_5`, metric FM-08), `stats.pass_at_k/pass_hat_k`, `gate.slice_check`, `gate.integrity_check`
- [x] `src/data/eval/eval_set_v2.jsonl` + `labels_v2.json` (sinh bằng `evalset --v2 --build`)
- [x] `src/reports/baseline_v2.json` (sinh bằng script) → job `eval-gate-v2` đã chạy xanh trên PR #1
- [x] Mô tả PR #1 có output `lab9.mutation` (scorecard + `--aa`) và 4 dòng `exit 1` của các trap
- [x] `docs/eval_card.md` có mục v2, ngưỡng A/A, slice bắt lỗi và giới hạn cỡ mẫu

## Bằng chứng

- [PR nộp bài #1, starter/d09 → main](https://github.com/phamtuananhhatay/K5-L3A-Day9-03503-PhamTuanAnh-Evaluation-and-Failure-Analysis/pull/1).
- [PR hoàn thiện checklist #2, kèm toàn bộ output kiểm chứng mới](https://github.com/phamtuananhhatay/K5-L3A-Day9-03503-PhamTuanAnh-Evaluation-and-Failure-Analysis/pull/2). Kết quả CI của bản cập nhật nằm trong mục Checks của PR.
- [CI Core và Advanced/Expert đã thành công](https://github.com/phamtuananhhatay/K5-L3A-Day9-03503-PhamTuanAnh-Evaluation-and-Failure-Analysis/actions/runs/44138113551).
- [Output script kiểm chứng](src/reports/validation_m6_m7.txt) có gate Core, detection, A/A, scorecard và từng trap.
- [Eval card](docs/eval_card.md) và [PRD v1.1](docs/PRD_v1.1.md) ghi phạm vi, ngưỡng, trách nhiệm và giới hạn.

Checklist ghi nhận các deliverable công khai. Key anchor và bộ chấm ẩn thuộc giảng viên. Hạn chấm vẫn áp dụng theo thời điểm commit thực tế trên PR.
