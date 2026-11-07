# Внедрение модели в другом проекте

## Не копируйте реализацию, переносите инварианты

Пять компонентов, имена suites и двухслойный planner — пример одной реализации. Новый проект начинает с inventory, release semantics, данных и угроз. Маленькому приложению может быть достаточно одного image, простого required check и независимого gate.

До любого push выясните побочные эффекты: webhooks, preview, production writers, scheduled jobs и миграции. Документарный playbook не разрешает production cutover и не заменяет поручение владельца.

## Шаг 1. Зафиксируйте baseline

Соберите таблицу текущего состояния:

- repository, default/release branches, full candidate SHA и accepted application SHA;
- dirty worktrees, remotes, branch protection и required checks;
- компоненты, worker/cron, CMS/DB/media и внешние integrations;
- действующие CI runners, principals, credentials и deployment triggers;
- текущий build/package path, artifacts и runtime configuration;
- accepted images/config, backup/restore и rollback;
- критические UI/API/worker scenarios и владельцы приёмки.

Сохраните чужую работу и существующий rollback. Неизвестное поле отмечайте `unknown`, а не `pass`.

## Шаг 2. Определите release authority

Запишите, какой ref, event и principal разрешают candidate, preview и production. Если владелец выбирает main-as-release, зафиксируйте, что его явное поручение push/merge main разрешает выпуск после всех gates без повторного вопроса.

Не выводите разрешение из доступа к Git, успешной ветки или наличия workflow. Отдельно определите, нужен ли preview. Push/dispatch модель не превращайте молча в PR service: для fork/PR нужны отдельные admission, secrets, cache и lifecycle.

## Шаг 3. Постройте trust boundary

Назначьте project-scoped self-hosted runner, UID/daemon, resource limits, network и caches. Установите admission вне checkout. Закрепите actions, base/job images и toolchain по reviewed immutable identities.

Выделите credentials для build/test, publication, target read и runtime. Проверьте отрицательные сценарии ACL. Не передавайте production DB/SMTP/CMS secrets в CI и не используйте общий root SSH как deploy protocol.

## Шаг 4. Сделайте build once и same digest

1. Выполните frozen dependency setup на CI.
2. Скомпилируйте приложение один раз для полного SHA.
3. Запустите meaningful checks против выпускаемого output.
4. Упакуйте этот output без второй компиляции.
5. Проверьте image с production-like runtime config и disposable data.
6. Опубликуйте immutable digest и manifest с source/run/attempt.

Preview и production должны получить один digest. Различия public origin, flags и secrets задавайте при запуске. Если это невозможно, оформите явное исключение и не заявляйте same-digest.

## Шаг 5. Введите scope только после полного пути

Сначала добейтесь корректного полного CI/preview. Затем измерьте фазы и выберите узкий bottleneck. Не начинайте с affected builds, если ещё нет независимого gate и accepted baseline.

Для первого слоя определите:

- path-to-component mapping и dependency closure;
- always-on checks;
- passive docs, которые  не входят в build;
- shared/lock/control/schema/auth patterns, требующие full;
- поведение при missing base, rename/delete/mode/symlink и unknown paths;
- стабильный required check и receipt `application_release: false` для docs-only.

Проверьте две накопленные правки между accepted baseline и candidate, а не только последний commit. Unknown всегда расширяет scope или останавливает выпуск.

## Шаг 6. Добавьте component reuse при необходимости

Reuse оправдан, если полные fixtures дороги, components независимы, а target способен проверить provenance. Для каждого component определите полный input fingerprint: path, mode, blob, recipe, toolchain и schema version.

Сохраняйте original built run/attempt/receipt. Запретите recursive reuse chains. Отдельно выберите test profile: неизменный image не отменяет изменившиеся consumer fixtures, schema checks или live acceptance.

Target независимо пересчитывает fingerprint и сравнивает tested bytes. Простого совпадения label или общего release SHA недостаточно.

## Шаг 7. Настройте независимый promotion

Gate вне checkout проверяет current protected ref, workflow/runner/actor/event, original attempt, required conclusions, artifact identity и preview evidence. Добавьте serial lock, CAS accepted state и защиту от stale run.

Publication-only resume вводите только после checked checkpoint. Он повторяет publication/scans без rebuild и сохраняет исходную authorization. Unknown activation outcome обрабатывается отдельной reconciliation, а не resume.

## Шаг 8. Подготовьте данные и эксплуатацию

До активации докажите backup через snapshot/readback/isolated restore. Сохраните previous images/config и running identities. Проверьте expand–contract compatibility и отсутствие второго writer.

Активируйте только изменённые компоненты. После проверки ролей, сценариев и identities зафиксируйте accepted release. Откат кода не выполняет DB restore. Для destructive migration нужен отдельный план и разрешение.

## Шаг 9. Проверьте отказы

Минимальный набор на безопасном контуре:

| Сценарий | Ожидаемый результат |
|---|---|
| Missing/corrupt cache | Корректный cold run без потери checks |
| Missing baseline или unknown path | Full scope либо отказ |
| Wrong actor/ref/SHA/attempt/digest | Независимый отказ до активации |
| Reused без original built receipt | Отказ reuse |
| Publication failure после checkpoint | Resume без rebuild и со свежими scans |
| Activation timeout | Reconciliation без нового side effect |
| Failed readiness | Bounded rollback изменённых components |
| Уже принятый release | Проверенный no-op без лишнего restart |
| Content-only | Новый content SHA при сохранённом application image |

Не заполняйте общий диск, не останавливайте соседние сервисы и не создавайте production business data ради negative test.

## Шаг 10. Отключите конкурирующий старый путь

После приёмки нового маршрута отключите прежние deploy triggers, credentials и второго writer в согласованном scope. Историю и recovery evidence сохраните. Старый target-build, ad hoc copy или archived watcher не должен оставаться случайным fallback.

Обновите AGENTS/runbook с фактическими командами и ограничениями. Зафиксируйте measured results, unknowns и rollback. Не объявляйте production принятым, если проверен только preview.

## Минимальный вариант без второго слоя

Для одного application image остановитесь на базовых инвариантах: trusted CI, exact SHA, build once, checked output, immutable digest, independent gate, separated credentials, backup и live acceptance. Component fingerprints и publication resume добавляйте только при измеренной необходимости. Это сокращает сложность без ослабления release identity.
