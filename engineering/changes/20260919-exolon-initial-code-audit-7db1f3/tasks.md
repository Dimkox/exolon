# Tasks — Exolon initial code audit

- [x] Establish durable change package (review-only, no write_agent).
- [x] Dispatch analysis agents: repo_explorer, architect, docs_researcher.
- [x] Linux static TMX / pbx / resource inventory.
- [x] Source review: input, collisions, cabin/teleport, suit, 125 zones.
- [x] Record analysis synthesis after architect report lands.
- [x] Run `python3 scripts/grok_verify.py --mode pr` and capture honest FAIL (no PR; factory-postgres-exit).
- [x] Independent `code_reviewer` (pass) + `test_reviewer` (fail — no macOS/XCTest).
- [x] Write Russian report + prioritized backlog.
- [x] Bind receipts to final tree fingerprint (verification fail, code_review pass, test_review fail).
- [x] Do **not** implement gameplay changes.

## Корректурный проход 2026-09-20 (v3, HEAD `52795d1`)

- [x] Перфайловая волна: 19 лагов по всем 18 Swift-файлам и корпусу данных; 2 независимых ревью финального дерева.
- [x] Снятие прежнего P0 (C1) подтверждено повторно: независимый пересчёт сетки + исполнение продуктового загрузчика.
- [x] Авторитет перенесён в `engineering/reports/exolon-full-audit-20260920-v3.md`; v1/v2 сохранены с баннерами.
- [x] Числа v3 закреплены одним самопроверяющимся инструментом `evidence/v3_measurements.py` (rc=0 ⇔ отчёт совпадает; 11 контролей переворачиваются).
- [x] Исправлены собственные ошибки v2: контроль джойна 0/370 → 3/370; разбивка спавна; «дыра GIF» снята; локатор O8; носители «номера шага» 3 → 4; 28 → 27 jsonschema; «7 из 8» → 10 уникальных.
- [x] Потолок Linux поднят: `evidence/harness/` собирает и исполняет настоящий `TMXMapLoader.swift` (125/125, фикстуры, негативный контроль сборки).
- [x] `linux_static_audit.py` воспроизводит порождённый `.md` побайтно (дефект, внесённый `52795d1`).
- [x] Приватность: `evidence/privacy_gate.sh` + скраб 15 файлов / 41 строки; шлюз PASS с подсаженным контролем.
- [x] `.gitignore` добавлен (отпечаток перестал зависеть от рабочей директории агента — upstream #168).
- [x] `waivers.md`: основание действий вне review-only скоупа (push, внешние issues, установка тулчейна); README не правился (FORBID-001) и вынесен в отдельное изменение.
- [ ] §9 macOS: 22 строки хендаута + `engineering/runbooks/macos-probe.sh` — ждут машину (ни локально, ни по ssh её нет).
- [ ] Доставка: PR на ветку аудита (ныне `52795d1`+ на origin без PR) и внешний App-owned check — локальными доказательствами не заменяется.
