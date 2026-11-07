# Обезличивание и границы публикации

## Принцип

Публичная версия сохраняет инженерные решения, но удаляет возможность восстановить частную инфраструктуру или использовать выпускной receipt как настоящий. Текст различает одобренную общую политику, датированные наблюдения и синтетические примеры. Ни один документ не подтверждает текущее live-состояние.

## Реестр источников и преобразований

| Источник | Что обобщено | Что опущено | Публичный статус |
|---|---|---|---|
| Одобренные CI/CD политики | Build once на self-hosted CI, same immutable artifact, независимые gates, разделение credentials, запрет автоматического DB rollback | Approval IDs, частные связи проектов, principals и topology | Общая политика без claims о внедрении во всех проектах |
| Scope planner | Классификация diff, always-on проверки, passive docs, fail-closed неизвестных входов | Бинарный planner, checksum, точная частная конфигурация и команды | Концептуальная модель первого слоя |
| Component release contract | Полный Git tree, path/mode/blob identity, toolchain, built/reused, original receipts без рекурсивных chains | Частная схема, реальные входы, validator и установленные policies | Наблюдаемая модель второго слоя |
| Release и operations | OCI identity, publication resume, backup/readback/restore, selective activation, reconciliation | Watcher, journal, request UUID, root paths, адреса, имена users и secrets | Датированное описание без deploy authority |
| Security checks | Свежие scans всех выпускаемых digests, блокировка исправляемых HIGH/CRITICAL | Scanner pins, отчёты, реальные CVE, registry coordinates и credentials | Политика выпуска, не заявление об отсутствии риска |
| Измерения | Номера runs, даты, длительности и состав workload для выбранных случаев | Полные SHA/digests, hosts, snapshots, клиентские данные и длинные логи | Исторические наблюдения, не SLA и не текущие live-факты |

## Что не публикуется

- исполняемый `.pyz`, watcher, target validator и частные policy bundles;
- production topology, IP-адреса, внутренние DNS, ports, Unix users и root paths;
- реальные principals, actors, tokens, SSH keys, cookies и другие credentials;
- полные Git SHA, OCI digests, artifact IDs, request UUID и snapshot IDs;
- журналы, полные receipts, выгрузки баз, переписка и клиентские сведения;
- старая production history как готовый fallback или руководство к восстановлению частной системы.

В публичном тексте не должно быть утверждений о текущем принятом release, шести текущих образах, старом shadow pipeline, универсальном PR/preview, универсальном native-release mapping, нулевых уязвимостях, регулярном сканировании уже работающих образов или гарантированном restore.

## Placeholder policy

Примеры используют только следующие классы идентичностей:

| Значение | Назначение |
|---|---|
| `00000000-0000-0000-0000-000000000000` | Nil UUID, не request ID |
| 40 нулей, единиц или двоек | Явно учебные Git SHA |
| `sha256:` и 64 нуля, единицы, двойки, тройки или четвёрки | Явно учебные digest/fingerprint значения |
| `0` | Недействительные run, attempt и artifact IDs |
| `example-org/playbook-demo` | Вымышленный репозиторий |
| Хосты `.invalid` | Зарезервированная неразрешаемая зона |
| `2000-01-01T00:00:00Z` | Намеренно устаревшая учебная дата |

Значения не связываются с реальными объектами. Даже при формальном совпадении шаблона синтетический manifest имеет `status: "synthetic-only"`, `release_authorized: false` и `evidence: false`.

`ci/verify.sh` по умолчанию собирает verifier image из `ci/Dockerfile.verify` с frozen `uv.lock`. Оператор может вместо этого передать уже принятый immutable image через `PLAYBOOK_VERIFY_IMAGE`; координата не навязывается публичным playbook.

## Проверка перед публикацией

1. Прочитать весь diff и сопоставить каждое наблюдение с допустимой категорией.
2. Проверить дерево и Git history независимым secret scanner, а затем локальным маркерным скриптом.
3. Проверить, что примеры не стали действительными credentials, receipts или deployment instructions.
4. Проверить относительные ссылки, JSON Schema, YAML 1.2 и Mermaid на self-hosted CI.
5. После публикации осмотреть GitHub rendering, видимость репозитория и отсутствие раскрытия через метаданные.

Автоматический поиск неполон. Ручной reviewer отвечает за смысловые признаки частной системы, которые нельзя перечислить регулярными выражениями.
