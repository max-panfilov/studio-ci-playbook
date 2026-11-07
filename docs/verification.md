# Проверка playbook

## Где выполнять

Проверки документов запускаются на доверенном self-hosted runner в контейнере. Репозиторий не содержит GitHub-hosted workflow и не требует application install/build/test. Нужны только Python 3.12 и зависимости из `pyproject.toml`:

- `jsonschema==4.26.0`;
- `ruamel.yaml==0.18.10` с YAML 1.2 и duplicate-key rejection;
- stdlib `unittest`.

`uv.lock` генерируется на доверенном CI и коммитится для воспроизводимого `uv sync --frozen`. По умолчанию `ci/verify.sh` собирает verifier image из `ci/Dockerfile.verify`. Оператор может вместо этого передать уже принятый immutable image через `PLAYBOOK_VERIFY_IMAGE`.

## Основной entrypoint

На self-hosted runner из корня чистого checkout:

```sh
export PLAYBOOK_VERIFY_IMAGE='operator-reviewed-immutable-image'
./ci/verify.sh
```

Скрипт не выбирает registry и не содержит образ по умолчанию. Он запускает контейнер с read-only root filesystem и checkout, без сети, capabilities и production credentials. Временная файловая система `/tmp` ограничена по размеру. Команды внутри контейнера:

```sh
python3 scripts/check_playbook.py
python3 -m unittest discover -s tests -v
```

Подготовка verifier image — отдельная операторская задача на доверенном CI. Dependency downloads не входят в сетевой контур самого теста. Скрипт не устанавливает пакеты и не пишет в checkout.

## Что проверяет `check_playbook.py`

| Область | Проверка |
|---|---|
| JSON | Strict parsing, отказ duplicate keys, обязательные synthetic flags |
| JSON Schema | `Draft202012Validator.check_schema` и проверка каждого example по именованному `$defs` контракту |
| YAML | YAML 1.2, string key `on`, push/dispatch triggers, jobs/steps и отсутствие hosted runner labels |
| Duplicate YAML keys | Отказ parser на повторном ключе |
| Markdown | Существование относительных файлов и anchors, запрет выхода за root, balanced fences |
| Mermaid | Наличие ожидаемых blocks и базовой diagram declaration |
| Public safety | Ограниченные private markers, secret patterns, root paths и IPv4 |
| Placeholders | Только allowlisted SHA/digests/UUID, nil request identity, `.invalid` hosts |
| Репозиторий | Наличие `uv.lock` для frozen verification и отсутствие запрещённых binary artifacts |

Вывод содержит коды ошибок с путями. Нулевой exit code означает только успех этих ограниченных проверок.

## Ожидаемые Mermaid diagrams

| Файл | Число blocks | Смысл |
|---|---:|---|
| `docs/architecture.md` | 1 | Trust и credential boundaries |
| `docs/scope-and-components.md` | 1 | Два слоя selection и fail-closed unknown inputs |
| `docs/native-release.md` | 2 | Release identity graph и publication-only resume |
| `docs/operations.md` | 1 | Acceptance, backup, selective activation, failure и recovery |

Validator считает fenced `mermaid` blocks и проверяет их начальную декларацию. Дополнительно `ci/Dockerfile.mermaid` вызывает `mermaid.parse` для каждого block в Node-контейнере без сети. Полный визуальный контроль выполняется после публикации на GitHub.

## Отрицательные tests

`tests/test_examples.py` использует только stdlib `unittest` и публичные fixtures. Тесты проверяют не только положительный проход, но и отказ duplicate JSON/YAML keys, hosted runner labels, неизвестных identities и частных маркеров. Репозиторный тестовый набор не обращается к сети и не создаёт release effects.

## Что остаётся за другими проверками

1. **Gitea acceptance.** Синтаксический YAML не гарантирует expression semantics, runner labels, secrets binding или scheduling. Проверять нужно на изолированном self-hosted fixture без production credentials.
2. **Mermaid и Markdown rendering.** Осмотреть опубликованные страницы на GitHub, включая кириллицу, длинные labels и все пять diagrams. После browser inspection закрыть Playwright browser.
3. **Secret scanning.** Прогнать независимый scanner по дереву и полной Git history. Встроенные regex — второстепенный guard, не замена scanner.
4. **Ручная sanitization review.** Проверить смысловые признаки topology, клиентов и операционных receipts, которые regex не распознаёт.
5. **Свежий clone.** Повторить критический путь на чистом checkout после публикации и сравнить exact revisions.

Эти дополнительные действия не заявлены выполненными в исходном наборе файлов. Их результаты появляются только после фактической проверки на CI и просмотра опубликованного репозитория.
