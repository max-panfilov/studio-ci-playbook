# Датированные случаи и измерения

## Как читать цифры

Все случаи относятся к наблюдениям 5–6 ноября 2026 года на одной частной self-hosted инфраструктуре. Номера runs сохранены как исторические ссылки, но сами runs, receipts и identities не публикуются. Текст не утверждает, что конфигурация или результаты остаются текущими.

Это единичные наблюдения разных workloads, а не медианы, контрольный эксперимент или SLA. Cold bootstrap, warm reuse, publication resume и live activation нельзя сравнивать как одинаковые операции. На длительность влияли fixtures, dependencies, registry, общая ёмкость runner, backup и acceptance.

| Случай | Дата | Workload | Наблюдение |
|---|---|---|---|
| Повторные полные runs | До 6 ноября 2026 | Пять main runs функции регистрации с полными fixtures | Около 147 минут CI суммарно |
| Полный v2 bootstrap, run 1360 | 6 ноября 2026 | Полный fixture, пять component identities, security scans и checkpoint | 25 мин 20 с |
| Main reuse, run 1361 | 6 ноября 2026 | Неизменные component inputs после bootstrap | `built 0 / reused 5`; CI 68 с; push → live 247 с |
| Publication resume, run 1362 | 6 ноября 2026 | Исходный checked checkpoint run 1361, обновлённые security data | 33 с; без native Build; пять свежих scans |
| PDF failed activation, run 1365 | 6 ноября 2026 | PDF-only candidate, один health probe сразу после запуска | Selective rollback и сохранение остальных identities |
| Full control gate, run 1366 | 6 ноября 2026 | Исправление watcher как control change | 24 мин 14 с на полном gate |

## 1. Повторная полная проверка: около 147 минут

Перед разделением component fingerprints серия выпусков функции регистрации потребовала пять main runs и примерно 147 минут CI. Значительная часть времени уходила на повторные полные fixtures. Ошибки загрузок, registry auth и security обнаруживались уже после дорогой работы.

Этот случай определил направление оптимизации: ранние preflights, checkpoint до публикации, пять component fingerprints, плоские original receipts и reuse неизменных bytes. Он не доказывает, что любой полный run длится 147 минут: это сумма конкретной серии, а не длительность одного pipeline.

## 2. Полный v2 bootstrap: 25 мин 20 с

Run 1360 выполнил первый полный component release v2. Старые images не угадывались по сходству labels: bootstrap потребовал полного acceptance и новых fingerprints. Проверялись выпускаемые bytes, полный fixture и security reports всех пяти компонентов.

Наблюдённая длительность 25 мин 20 с включает тяжёлую полную проверку, а не только компиляцию. Число служит baseline именно для cold/full v2 path. Оно не сравнивается напрямую с 147 минутами серии из пяти runs и не обещает такой же длительности на другом hardware.

## 3. Последующий main: `built 0 / reused 5`

Run 1361 не менял component inputs после полного bootstrap. План показал ноль построенных и пять reused components. CI занял 68 секунд; от main push до завершения live acceptance прошло 247 секунд.

Reuse опирался на исходные built receipts из run 1360, совпадающие fingerprints и те же tested bytes. Пять digests получили свежие scans. Независимый target validator проверил OCI identity и исходные runs/attempts; перед активацией был подтверждён backup/restore.

Интервал 247 секунд включает больше, чем CI: promotion, backup, независимую проверку и acceptance. Его нельзя называть временем сборки или универсальным deployment time. После любого существенного runtime/worker/control change потребуется другой профиль проверки.

## 4. Publication-only resume: 33 секунды

Run 1362 ссылался на исходный checked checkpoint run 1361 после неуспешного publication/scanning path. Native Build был пропущен, release images не пересобирались. Все пять исходных digests получили свежие scans после обновления security data.

Продолжительность составила 33 секунды. Live component identities и activation run не изменились: resume подтвердил publication, а не выпустил новый candidate. Исходная authorization осталась у run 1361.

Этот случай не означает, что любой retry занимает 33 секунды. Он требует доступного checkpoint, точных bytes, совместимого registry state и отсутствия unknown activation outcome. Отсутствие image или конфликт tag останавливает процесс.

## 5. PDF: отказ single-probe и исправление readiness

PDF-only candidate прошёл CI, но live activation в run 1365 откатилась. Watcher отправил единственный health request сразу после запуска нового renderer. Остальные services уже были готовы, поэтому их состояние не дало PDF времени на старт.

После отката прежний renderer снова прошёл render scenario. Изменённый PDF был возвращён к прежнему image; runtime, MCP, memory, data и worker identities сохранились. Failed attempt не был удалён или автоматически повторён.

Исправление ввело ограниченное ожидание read-only PDF readiness и связанные проверки:

- общий deadline — до 15 секунд;
- timeout одного request — не более 1 секунды;
- обязательное структурированное `ready: true` в ответе HTTP 200;
- один synthetic render после готовности;
- обязательные refusal, recovery и сохранность остальных components.

Watcher относится к control inputs, поэтому исправление не продвигали как ещё один узкий PDF reuse. Run 1366 выполнил полный control gate за 24 мин 14 с. Последующая отдельная активация прошла с новым readiness и подтверждённым backup/acceptance; это закрытое историческое наблюдение, а не текущий live-статус.

Случай показывает: успешный component CI не доказывает startup behavior на площадке, а rollback образа не требует восстановления базы. Ограниченное ожидание важнее бесконечного retry и дополнительных side effects.

## Как использовать эти случаи

Полезные выводы — разделение дорогих фаз, ранние отказы, проверенный reuse, свежие scans и узкая активация с сохранением данных. Нельзя переносить секунды, число компонентов, readiness deadlines или run topology на другой проект без собственных измерений.

Для нового внедрения записывайте cold/warm cache, workload, limits, queue, fixture time, publication, activation и acceptance отдельно. Несколько сопоставимых runs важнее одного удачного результата. Не удаляйте обязательные проверки ради улучшения таблицы времени.
