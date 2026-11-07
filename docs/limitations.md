# Ограничения и недоказанные возможности

## Документация вместо продукта

Репозиторий не содержит исполняемый Studio CI, component release implementation, watcher или target validator. Текст и синтетические схемы нельзя использовать как самостоятельный production pipeline. Для внедрения нужны собственные threat model, код, policy, credentials и acceptance.

Публичная `schemas/examples.schema.json` намеренно иллюстративна. Она не совпадает с частной Studio CI schema, не покрывает все release invariants и не должна становиться единственным gate.

## Нет универсального PR/preview

Описанный текущий workflow использует push и workflow_dispatch. Fork/PR admission, изолированные preview environments, их DNS/TLS/auth, data lifecycle, garbage collection и cost controls здесь не спроектированы. Schematic YAML не добавляет эти возможности.

Наличие `native-release` в примере не задаёт универсального mapping для всех репозиториев. Пять компонентов и названия acceptance profiles относятся только к наблюдаемой реализации.

## Нет текущих live-утверждений

Runs и измерения относятся к 5–6 ноября 2026 года. Они не подтверждают текущий main, accepted release, uptime, security posture или конфигурацию инфраструктуры. Для действия нужны свежие разрешённые runtime facts и журналы.

Длительности получены на разных workloads без серии сопоставимых повторов. Это не SLA, не медиана, не гарантированный процент ускорения и не сравнение одинаковых операций. 147 минут описывают суммарную серию пяти полных runs; 68 секунд — CI warm reuse; 247 секунд — более широкий push-to-live интервал.

## Security — только выпускной gate

Свежий scan при продвижении блокирует исправляемые HIGH/CRITICAL по описанной policy. Это не означает нулевые уязвимости, отсутствие unfixed findings или безопасность всех dependencies.

Регулярный мониторинг новых CVE уже работающих образов здесь не заявлен. Идемпотентная проверка accepted receipt не равна ежедневному повторному сканированию. SBOM, signing и аттестации не считаются внедрёнными по наличию раздела в документации.

## Backup и recovery имеют границы

Snapshot/readback/restore receipt подтверждает конкретную проверку на конкретных данных. Он не гарантирует восстановление любой будущей версии, межбазовую атомарность, нулевой downtime или отсутствие потери последних записей.

Кодовый rollback не откатывает базу. После business writes требуется after-writes recovery plan. Старый dump поверх нового canonical writer автоматически не применяется.

## Scope и reuse не сокращают обязательные проверки

Diff classifier может ошибиться только в сторону полного scope либо остановки; пропуск неизвестного входа недопустим. Компонентный reuse требует исходного built receipt и независимой проверки tested bytes. Он не отменяет изменившиеся consumer, SDK, schema, auth или live acceptance cases.

Первый слой и второй слой не являются взаимозаменяемыми. Публичные примеры не реализуют ни один из них.

## Publication resume ограничен

Resume требует checked checkpoint, исходной authorization, точных immutable bytes и свежих scans. Он не пересобирает отсутствующий image, не исправляет failed activation и не даёт нового deploy authority. Unknown activation outcome требует остановки и сверки.

## Content-only отделён от application release

Read-only content snapshot может обновляться с сохранением application image. Это не универсальный способ пропустить build: executable content, build inputs и control changes требуют другого scope. Content SHA, component source SHA и release SHA остаются разными identities.

## Проверки репозитория неполны

Локальный validator проверяет ограниченный набор форматов и маркеров. Он не является полноценным Mermaid parser, Gitea runner, secret scanner, рендерером Markdown или аудитором смысловой приватности. YAML syntax не доказывает принятие Gitea, а JSON Schema не доказывает release authority.

После публикации нужны просмотр GitHub rendering, независимый secret scan дерева и истории, а также ручная проверка отсутствия частных сведений. Эти действия не следует считать выполненными без отдельного evidence.
