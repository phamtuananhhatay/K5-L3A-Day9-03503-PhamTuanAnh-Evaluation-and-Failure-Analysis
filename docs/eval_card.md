# Eval card ? LogiX-VN refund agent

Eval owner d? ki?n l? Ph?m Tu?n Anh, theo t?n repo. Ph?m vi ??nh gi? l? agent x? l? claim ho?n ti?n trong d? li?u c?ng khai, ch?y offline b?ng MockLLM v? SQLite t?m.

## Phi?n b?n v? d? li?u

| B? d? li?u | Run ID baseline | SHA | Spec | S? trial |
|---|---|---|---|---:|
| v1 | E-swarm-20261117-8cb8 | 8cb82c5e0c4e | 1.1 | 70 |
| v2 | E-swarm-20261118-af6c | af6cd54b0d77 | 2.1 | 140 |

Seeds l? 11, 22, 33, 44, 55. V1 c? 14 item, v2 c? 28 item. Nh?n n?m ri?ng trong labels_v1.json v? labels_v2.json. Code v? grader ???c l?u c?ng commit ch?a card v? baseline n?y. Commit n?n tr??c khi ho?n th?nh b?i l? d1b9471.

## Core v? gate

| Metric | Baseline v1 | Fixed | Seeded regression | Ng??ng v1 |
|---|---:|---:|---:|---|
| approval_bypass | 0 | 0 | 0 | max 0 |
| secret_leak | 0 | 0 | 0 | max 0 |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 | min 0.95 v? CI |
| reply_amount_matches_ledger | 1.0 | 1.0 | 0.7857 | min 1.0 |
| pass_rate | 0.9857 | 1.0 | 0.7143 | min 0.85 v? CI |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 | min 0.95, theo d?i |
| pass_5 | 0.9286 | 1.0 | 0.7143 | min 0.80, theo d?i |
| cost_per_success | 49.567 | 48.7157 | 81.202 | t?ng t?i ?a 10%, theo d?i |

Paired bootstrap l?y trung b?nh m?i claim qua c?c seed tr??c khi resample, 1.000 m?u v?i RNG 2027 v? m?c tin c?y 95%. Pass rate c?a seeded_regression c? ? ?0.271, CI [?0.500, ?0.057], khi?n gate exit 1. Fixed c? ? +0.014, CI [0.000, +0.043] v? exit 0.

Tone judge ??t ?=0.757, precision=0.857 v? recall=0.800. Helpful c? ?=0.375, recall=0.300 v? b? s?t 21/30 l?i n?n b? lo?i kh?i gate. Xem [judge audit](judge_audit.md). Ti?n v? approval ???c ch?m b?ng code.

[Trace case C-008](trace_case.md) x?c ??nh event reply l? b??c sai ??u ti?n khi ledger ghi 20.000? nh?ng agent b?o 35.000?. Regression test ch?y c?ng claim tr?n b?n l?i v? fixed.

## Slice v2

Money movement c? 12 item v?i s?n 0.95. Adversarial c? 14 item v?i s?n 0.90. Denial c? 11 item v?i s?n 0.90. M?i slice c?n ch?n gi?m c? ? ngh?a qua CI.

Slice regression c? pass rate to?n t?p 0.9357 v? CI ? [?0.121, +0.029]. Money movement ch? ??t 0.8500, d??i s?n 0.95. Fixed v? honest_refactor qua gate khi ch?y ki?m tra M5.

## M6 v? M7

S?n pass_hat_5 l? 0.80 v? ch?n gi?m c? ? ngh?a. Baseline c? pass_hat_5=0.8929. Ch? s? ???c t?nh tr?n t?ng claim r?i l?y trung b?nh. A/A cho pass_hat_5=0.8929 ? c? hai b? seed, ?=0. S?n 0.80 th?p h?n ?i?m A/A 0.0929. Scorecard ??t 3/3 regression b? ch?n v? 0 b?o nh?m. Flaky regression b? ch?n ? pass_hat_5, pass_rate v? money_movement. C? b?n trap c?ng khai tr? exit 1 v?i l? do INTEGRITY. K?t qu? ch?y th?c t? n?m trong [validation log](../src/reports/validation_m6_m7.txt).

Gate ki?m tra t?p item ? seed, d?ng tr?ng, gi? tr? grader b? thi?u ho?c kh?ng h?p l?, evaluator failures, thay ??i slice v? t?nh nh?t qu?n gi?a h?ng d? li?u v?i aggregate. Ratchet tr?n c?ng eval-set version ch?n x?a ho?c n?i ng??ng, b? metric, b? slice v? t?t blocking.

## Gi?i h?n v? v?n h?nh

MockLLM v? CSV judge replay c?ng khai ch?a ?o h?nh vi c?a model th?t ho?c kh?ch h?ng th?t. T?p 14/28 item c? CI r?ng. V?i 5 seed, l?i hi?m ? kho?ng m?t ph?n ba seed c? th? l?t ? m?t s? l?n ch?y. Model th?t c? th? c? d?i nhi?u A/A l?n h?n 0, c?n ?o l?i v? ch?n s?n c? kho?ng c?ch v?i d?i nhi?u.

Khi gate exit 1, eval owner ??c metric, trace v? ledger r?i s?a nguy?n nh?n tr??c khi ch?y l?i. Pilot hi?n gi?i h?n ? th? nghi?m offline theo claim v? principal trong b? lab. D? li?u production, thanh to?n th?t, multi-order v? tranh ch?p ph?p l? c?n ??nh gi? b? sung.

T?ng eval-set version khi ??i item ho?c nh?n v? sinh l?i baseline. T?ng metric-spec version khi ??i ??nh ngh?a ho?c ng??ng, ghi l? do trong PR. Spec v2.1 b? sung pass_hat_5 v? bootstrap theo t?ng item. Product owner v? ph? duy?t tri?n khai c?n ???c x?c nh?n tr??c pilot th?c t?.
