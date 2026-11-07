# Общая политика выпуска

## Статус и область

Этот документ описывает одобренную владельцем общую Studio policy для новых миграций на доверенный self-hosted CI. Он не утверждает, что каждый проект уже переведён, и не даёт права на production release. Конкретный проект сохраняет свои principals, release branch, gates, data runbook и согласованный scope.

Наблюдаемая пятикомпонентная реализация рассматривается отдельно в [архитектуре](architecture.md) и [native release](native-release.md). Её детали не заменяют общие инварианты.

## 1. Доверенное исполнение

Application install, build, test и packaging выполняются на назначенном self-hosted CI/build host. Рабочая машина редактирует исходники и управляет запусками, но не становится fallback для сборки. GitHub-hosted compute в этой политике не используется.

До checkout или привилегированного шага admission проверяет repository, actor, event, ref, workflow и допустимый runner. Недоверенный fork или PR не получает publisher, production secrets и persistent trusted cache. Изменение admission policy внутри candidate checkout не является независимой границей.

Runner, UID, rootless daemon, caches и network образуют project trust boundary. Rootless Docker снижает часть рисков, но socket даёт широкие полномочия над своим daemon. Проекты с несовместимым доверием не делят unrestricted socket.

## 2. Один build для полного release SHA

Для каждого полного Git SHA приложение компилируется один раз. Проверяется именно bundle/image, который позже будет опубликован. Packaging копирует проверенный output, а не запускает компилятор повторно.

Merge commit получает новый SHA и потому новый проверочный run. Это не нарушение build once: identity кандидата изменилась. На preview и production не выполняются application install, build или startup compilation.

Сервис без компиляции не освобождается от контроля. Он получает immutable source/package identity, meaningful checks, release manifest и runtime acceptance.

## 3. Один проверенный artifact на площадках

Preview и production используют один OCI digest. Mutable tag пригоден для навигации, но не служит release identity. Runtime configuration, public origin, feature flags и secrets задаются на площадке без изменения проверенных bytes.

Если build-time различия мешают same-digest promotion, сначала устраняют зависимость либо явно документируют проектное исключение. Нельзя называть два разных образа одним artifact из-за общего тега.

Multiarch OCI index, platform manifest, image config и ordered layers различаются. Gate проверяет всю цепочку для целевой архитектуры, а не только верхний digest.

## 4. Независимый release manifest и promotion gate

Manifest связывает:

- repository и полный release SHA;
- trusted workflow, runner, actor, event и ref;
- authorization run и исходные build run/attempt;
- component source SHA и input fingerprints;
- результаты обязательных проверок и hashes receipts;
- OCI index/platform/config/layers для каждого компонента;
- свежие security scans и применимую policy;
- content identity, если выпускается отдельный content snapshot.

Target gate получает доказательства по доверенному каналу и самостоятельно пересчитывает критические fingerprints. Он отклоняет неправильный repo/SHA/ref/platform/attempt, stale baseline, missing checks, copied green job и подменённый digest. Слово `success`, переменная окружения или файл из checkout недостаточны.

Уже принятый release завершается как проверенный no-op. Старый run не перезаписывает новый release благодаря serial lock и compare-and-swap safeguards.

## 5. Разделённые credentials

| Возможность | Минимальная область | Запрещено |
|---|---|---|
| Build/test | Disposable test data, pinned tools, ограниченный cache | Production DB, SMTP/CMS write secrets, общий root SSH |
| Registry publish | Только нужный project namespace и только publication steps | Read/write вне проекта, deploy credentials |
| Target proof | Read-only API и registry | Push/delete/admin, произвольный production shell |
| Runtime | Только secrets и config своей площадки | Publisher credential и CI-wide secrets |
| Operator policy | Установка и обновление вне candidate checkout | Автоматическое исполнение новой target policy из artifact |

Разные jobs не изолируют repository-wide secrets автоматически. Проверяйте фактические ACL principals, а не только названия tokens.

## 6. Release authority

Проект явно определяет release branch и допустимый trigger. В режиме main-as-release отдельное поручение владельца push/merge main разрешает штатный выпуск после всех gates без второго вопроса. Доступ к Git, готовая ветка или успешный CI сами по себе такого разрешения не создают.

Publication-only retry сохраняет исходную authorization identity и не расширяет её. Unknown activation outcome сначала сверяется с фактическим runtime и журналом. Новый идентификатор запроса для сверки не становится новым правом на deploy.

## 7. Данные, backup и rollback

До активации фиксируются previous images/config, свободные ресурсы и согласованный backup. Успешность backup подтверждают snapshot/readback и изолированным restore, а не наличием timer или завершением экспортера.

Предпочтительны expand–contract migrations и совместимость старого runtime с новой схемой. Кодовый rollback возвращает только сохранённые images/config изменённых сервисов. Он не выполняет DB down/restore автоматически и не удаляет новые business writes.

После первого возможного business effect recovery следует after-writes плану проекта. Старый dump не накатывается поверх нового canonical writer. Неизвестный исход останавливает повторение: сначала receipt/runtime reconciliation.

## 8. Приёмка

Зелёный CI подтверждает проверку кандидата, но не production acceptance. После активации проверяются:

- exact runtime source/digest каждого компонента;
- сохранение identities незатронутых сервисов и данных;
- health/readiness, worker, owner access и критический UI/API scenario;
- внешний HTTPS/TLS/redirects, если это входит в проект;
- отсутствие второго writer и ошибок domain commands;
- зафиксированный rollback и оставшиеся unknowns.

Не создавайте реальные клиентские заявки, платежи или финансовые записи ради smoke.

## 9. Content-only выпуск

Документация, catalog или read-only content snapshot может иметь отдельный маршрут с собственным content SHA и readback. Он не требует rebuild неизменного application image, но не объявляется passive автоматически.

Если Markdown импортируется приложением, участвует в генерации, меняет control policy или входит в build inputs, это не passive docs. Content-only и native component release не подменяют друг друга.

## 10. Изменение политики

Изменение planner, release contract, watcher, target policy или security threshold — control change. Оно требует полного согласованного gate и независимой установки оператором. Оптимизация не должна удалять meaningful checks, ослаблять ACL или расширять release authority.
