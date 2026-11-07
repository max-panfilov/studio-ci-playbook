# Studio CI Playbook

Публичный русскоязычный playbook о воспроизводимом CI/CD: один release SHA собирается один раз на доверенном self-hosted runner, проверенные immutable artifacts проходят независимые promotion gates, а production data не откатывается вместе с образом. Документы обобщают одобренную политику и датированный опыт пяти компонентов без публикации частной реализации.

Это не готовый CI-сервер, не deployment tool и не копия Studio Platform. Здесь нет planner binary, watcher, production credentials, настоящих release receipts или исполняемого pipeline. Примеры созданы для чтения и тестирования публичной схемы; они не доказывают выпуск.

## Две модели, которые нельзя смешивать

| Слой описания | Что входит | Чего не следует из него заключать |
|---|---|---|
| Общая одобренная политика | Доверенный self-hosted CI, build once для полного release SHA, проверка выпускаемых bytes, immutable OCI identity, отдельные credentials, независимые gates, backup и запрет автоматического DB rollback | Что любой проект уже соответствует политике или получил право на production release |
| Наблюдаемая реализация | Studio CI как первый слой scope planning; отдельный второй слой component fingerprints и release contract для `runtime`, `worker`, `mcp`, `memory`, `pdf` | Что это универсальный PR/preview service, текущее live-состояние или публично доступный продукт |
| Синтетические примеры | Поля, связи и отрицательные случаи для обучения | Настоящие identities, разрешения, scans, acceptance или deployment |

Датированные наблюдения относятся к 5–6 ноября 2026 года. Они сохранены как исторические случаи, а не как утверждение о состоянии на сегодня.

## Главная идея

Первый слой решает, какие проверки нужны по diff. Второй слой внутри native release решает, какие компоненты изменились по полному Git tree, build recipe и toolchain identity. Неизвестный путь, отсутствующий baseline, control/schema/auth change или противоречивое дерево расширяет проверку либо останавливает выпуск.

Studio CI в этой модели не собирает приложение и не разворачивает его. Сборку и acceptance выполняет отдельный release pipeline. Независимый target validator заново проверяет source/run/attempt, fingerprints, tested bytes и OCI identity. Build scope, test scope, artifact reuse и deploy scope — четыре разных решения.

Текущий описанный workflow запускается по **push** и **workflow_dispatch**. Наличие schematic YAML не создаёт универсального PR/preview процесса. Publication-only resume повторяет публикацию уже проверенного checkpoint и не даёт нового deploy authority.

## Карта документов

| Документ | Содержание |
|---|---|
| [Политика](docs/policy.md) | Обязательные инварианты build once, same digest, credential separation и data safety |
| [Архитектура](docs/architecture.md) | Границы доверия, credentials и независимый promotion path |
| [Два слоя scope](docs/scope-and-components.md) | Diff planner, component fingerprints, fail-closed selection и пять компонентов |
| [Native release](docs/native-release.md) | Release identity graph, original provenance, scans и publication-only resume |
| [Эксплуатация](docs/operations.md) | Backup/readback/restore, selective activation, acceptance, rollback и unknown outcome |
| [Кейсы](docs/case-studies.md) | 147 минут, полный bootstrap, reuse, resume за 33 секунды и PDF startup correction |
| [Внедрение](docs/adoption.md) | Пошаговая адаптация политики к другому проекту без копирования частной схемы |
| [Ограничения](docs/limitations.md) | Что не реализовано, не доказано и не обещано |
| [Проверка репозитория](docs/verification.md) | Контейнерные self-hosted checks и отдельная проверка GitHub rendering |
| [Обезличивание](SANITIZATION.md) | Источники, абстракции, omissions и placeholder policy |

## Пять компонентов наблюдаемой модели

| Компонент | Роль | Граница повторного использования |
|---|---|---|
| `runtime` | Web/application runtime | Свой input fingerprint и проверенный OCI image; с `worker` может делить полный acceptance suite |
| `worker` | Скомпилированная фоновая обработка | Отдельный image identity, actor/epoch controls и runtime acceptance |
| `mcp` | Протокольный backend | Отдельные build inputs, исходный build receipt и свежий scan |
| `memory` | Хранение и обработка памяти | Отдельные build inputs, data safety, original receipt и recovery evidence |
| `pdf` | Изолированный renderer | Свой dependency/browser graph, bounded readiness и отдельная активация |

Общий набор компонентов не означает пять сборок при каждом изменении. Изменённые fingerprints определяют `built`; совпавшие fingerprints допускают `reused` только после проверки исходного **built** receipt. Рекурсивный reuse из другого reused receipt не принимается.

## Release за один проход

1. Admission проверяет repository, actor, event, ref и workflow до привилегированной работы.
2. Первый слой строит scope plan от правильного baseline до полного candidate SHA.
3. Второй слой вычисляет component fingerprints по полному дереву и выбирает acceptance profile.
4. CI один раз компилирует изменённые компоненты, проверяет выпускаемые bytes и сохраняет checkpoint до публикации.
5. Publisher с узким credential записывает immutable artifacts; свежие scans охватывают все пять digests, включая reused.
6. Независимый gate сверяет authorization run, исходные build runs/attempts, policy, receipts и цепочку OCI index → platform → config → layers.
7. Площадка сохраняет подтверждённый backup, активирует только изменённые компоненты и проверяет роли, сценарии и identities.
8. При ошибке кодовый rollback затрагивает только изменённые сервисы. База данных автоматически не восстанавливается поверх новых записей.

Полная схема — в [архитектуре](docs/architecture.md) и [native release](docs/native-release.md).

## Синтетические примеры

| Файл | Назначение |
|---|---|
| [`studio-ci.json`](examples/studio-ci.json) | Первый слой: paths, checks, passive docs и full scope |
| [`release-policy.json`](examples/release-policy.json) | Второй слой: входы пяти компонентов и control/full-check patterns |
| [`plan.json`](examples/plan.json) | Результат выбора проверок без release authority |
| [`request.json`](examples/request.json) | Reconciliation metadata dispatch/push, не разрешение выпуска |
| [`release-manifest.json`](examples/release-manifest.json) | Учебный identity graph с `synthetic-only` и недействительными identities |
| [`gitea-ci.yml`](examples/gitea-ci.yml) | Parseable schematic push/dispatch workflow, намеренно непригодный для запуска |
| [`examples.schema.json`](schemas/examples.schema.json) | Намеренно иллюстративная публичная JSON Schema |

Во всех JSON-примерах установлены `synthetic: true` и `evidence: false`. Используются nil UUID, нулевые run IDs, повторяющиеся placeholder hex и хосты `.invalid`. Не заменяйте их настоящими значениями в публичной ветке.

## Проверка без production

Зависимости нужны только для проверки документов: Python 3.12, `jsonschema==4.26.0` и `ruamel.yaml==0.18.10`. Lockfile генерируется на доверенном CI и коммитится для воспроизводимого `uv sync --frozen`. По умолчанию `ci/verify.sh` собирает pinned verifier image, а затем запускает проверки без сети:

```sh
./ci/verify.sh
```

Оператор может вместо локальной сборки передать уже принятый immutable image через `PLAYBOOK_VERIFY_IMAGE`. Скрипт проверяет JSON Schema, YAML 1.2 и duplicate keys, Markdown links/fences, ожидаемые Mermaid blocks, placeholder policy и ограниченный набор private/secret markers. Затем запускается stdlib `unittest`.

Эти проверки не заменяют Gitea workflow acceptance, Mermaid rendering, ручной security review или независимый secret scan. Команды и границы — в [verification](docs/verification.md).

## Что показывают измерения

Исторические случаи показывают цену повторного полного fixture и возможный эффект точного reuse:

- повторные полные runs заняли около 147 минут на конкретной серии работ;
- полный v2 bootstrap занял 25 мин 20 с;
- следующий main переиспользовал пять компонентов: 68 с CI и 247 с от push до live acceptance;
- publication-only resume занял 33 с без rebuild и со свежими scans;
- PDF single-probe activation откатилась, после чего bounded readiness и полный control gate исправили сценарий.

Это разные workloads на конкретной инфраструктуре, а не сравнение «до/после» и не SLA. Состав и ограничения каждого случая — в [case studies](docs/case-studies.md).

## С чего начать внедрение

Сначала прочитайте [политику](docs/policy.md), затем [пошаговое внедрение](docs/adoption.md). Зафиксируйте release semantics, компоненты, данные, credentials и текущий rollback. Не копируйте пять компонентов или схему fingerprints как обязательный шаблон: маленькому приложению может хватить одного artifact и одного promotion gate.

## Лицензия

Документация, схемы, примеры и скрипты распространяются по [MIT](LICENSE).
