# Архитектура и System Design

## Задача 1: Шардирование кэша и алгоритм Consistent Hashing (Hash Ring) {#task-001-python-system-design-consistent-hashing}
**Видео:** [Собеседование Python Middle / Senior. Вопросы и ответы](https://www.youtube.com/watch?v=zZOnhVGQ05U)
**Категория:** System Design, Распределенные системы
**Популярная:** 1

### Условие
Обсуждается шардирование данных в распределенном кэше (например, в Redis Cluster). 
Вопрос: Как алгоритмически распределить ключи по узлам (нодам), чтобы минимизировать перераспределение данных при добавлении или падении (удалении) одной из нод?

### Решение кандидата
Сначала кандидат предполагает, что данные распределяются через мастер-репликацию, но интервьюер направляет его в сторону алгоритмов хэширования, упоминая концепцию кольца хэшей (Hash Ring).

### Эталонное решение (AI)
Проблема классического шардирования по модулю числа серверов (формула `node_index = hash(key) % N`) заключается в том, что при изменении количества узлов `N` (например, при добавлении нового сервера), почти все существующие ключи меняют свой индекс. Это приводит к инвалидации 99% кэша и лавинообразной нагрузке на основную базу данных (Cache Stampede).

**Эталонное решение — алгоритм Consistent Hashing (Согласованное хэширование):**
1. Все доступные узлы хэшируются (например, по их IP) и размещаются на абстрактном "кольце" (Hash Ring), представляющем собой пространство значений от 0 до 2^32-1.
2. Приходящий ключ кэша также хэшируется и проецируется на это же кольцо.
3. Система идет по кольцу по часовой стрелке от позиции ключа и записывает/читает данные на **первом встретившемся узле**.
4. **Результат:** При добавлении нового узла на кольцо он забирает ключи **только** у одного своего соседа (часть "дуги"). Остальные узлы остаются нетронутыми. В результате инвалидируется лишь малая часть кэша (`1/N` данных), что позволяет кластеру масштабироваться безболезненно.


## Задача 2: Код-ревью веб-приложения: паттерн Outbox, конкурентность и REST {#task-002-dotnet-code-review-outbox-pattern-rest}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
В рамках секции код-ревью (задача с собеседования в Альфа-Банк на позицию .NET Backend Developer) представлен исходный код API на ASP.NET Core / Entity Framework Core со следующими требованиями и проблемами:
1. **Бизнес-требование:** начисление кэшбэка пользователю не чаще одного раза в сутки, фиксация статистики администратора и отправка уведомлений (Email/Push/SMS).
2. **Исходный код содержит антипаттерны:**
   - Контроллер: ручное создание зависимостей (`new Service()`) вместо DI; нарушение REST (GET для изменяющих операций, неверные пути роутов, возврат нетипизированного `IActionResult` с пропущенным `await`); отсутствие использования интерфейсов.
   - In-memory кэш через обычный `List<long>` без потокобезопасности, TTL и распределенного состояния.
   - Сервисный слой: прямое создание `DbContext` внутри методов, отсутствие транзакционной целостности при выполнении цепочки: сохранение кэшбэка $\to$ инкремент статистики $\to$ отправка уведомлений.
   - Конкурентный доступ: при параллельных запросах на начисление кэшбэка возможно задвоение (Race Condition), так как транзакции на стандартном уровне изоляции (Read Committed) не блокируют проверку истории начислений.

### Решение кандидата
1. **Контроллеры и DI:** Переписал конструкторы на Primary Constructors в C#, выделил интерфейсы для тестируемости, исправил роутинг (переход на POST для начисления кэшбэка, RESTful URL), заменил `IActionResult` на строго типизированные ответы (или `Results<Ok<T>, BadRequest>`). Использовал извлечение ID пользователя через `ClaimsPrincipal` / контекст авторизации, а не параметр запроса.
2. **Кэширование:** Указал, что самописный статический список не потокобезопасен и сбрасывается при рестарте/масштабировании. Заменил на распределенный кэш (Redis) с TTL 24 часа. Подчеркнул, что кэш не является источником правды, поэтому проверка в БД все равно обязательна.
3. **Транзакционность и Outbox:** Для атомарности бизнес-операции и внешних интеграций предложил паттерн Transactional Outbox: сохранение события начисления и сообщений для отправки нотификаций/статистики в рамках одной транзакции EF Core (`Unit of Work`). Фоновые воркеры считывают Outbox-таблицу и отправляют нотификации/сообщения в Kafka.
4. **Борьба с гонками (Race Conditions):** При параллельных запросах обычный `SELECT` вернет пустую/старую запись обоим потокам. Предложил пессимистическую блокировку: `SELECT ... FOR UPDATE` по строке Customer в транзакции.
5. **Параллельное выполнение асинхронных операций:** Для нотификаций (Email, SMS, Push) предложил запускать задачи параллельно через `Task.WhenAll(task1, task2, task3)` вместо последовательного `await`.

### Эталонное решение (AI)
Комплексный рефакторинг данного сервиса строится вокруг устранения гонок и гарантированной доставки событий.

#### 1. Устранение состояния гонки (Race Condition)
Если два запроса приходят одновременно:
- Проверка кэша может пропустить оба запроса (cache miss).
- Чтение последней транзакции на `Read Committed` в обоих потоках покажет, что суток еще не прошло (или записей нет).

**Решение:** Пессимистическая блокировка родительской записи (Customer) через `FOR UPDATE`:
```csharp
await using var transaction = await dbContext.Database.BeginTransactionAsync(ct);

// Блокируем запись клиента на время транзакции (EF Core 7+: FromSqlRaw)
var customer = await dbContext.Customers
    .FromSqlRaw("SELECT * FROM Customers WHERE Id = {0} FOR UPDATE", customerId)
    .FirstOrDefaultAsync(ct);

if (customer is null)
    throw new NotFoundException("Customer not found");

var lastCashback = await dbContext.Cashbacks
    .Where(c => c.CustomerId == customerId)
    .OrderByDescending(c => c.CreatedAt)
    .FirstOrDefaultAsync(ct);

if (lastCashback != null && lastCashback.CreatedAt.AddDays(1) > DateTimeOffset.UtcNow)
{
    throw new RateLimitException("Кэшбэк уже был начислен за последние 24 часа");
}

// Начисление кэшбэка
var cashback = new Cashback { CustomerId = customerId, Amount = amount, CreatedAt = DateTimeOffset.UtcNow };
dbContext.Cashbacks.Add(cashback);

// Outbox Messages для аналитики и нотификаций
dbContext.OutboxMessages.AddRange(
    new OutboxMessage { Type = "CashbackCreated", Payload = JsonSerializer.Serialize(new { customerId, amount }) },
    new OutboxMessage { Type = "AdminStatsIncrement", Payload = JsonSerializer.Serialize(new { adminId }) }
);

await dbContext.SaveChangesAsync(ct);
await transaction.CommitAsync(ct);
```

#### 2. Параллельный вызов нотификаций (Fan-out)
Воркер Outbox считывает сообщение и рассылает параллельно нотификации:
```csharp
public async Task SendAllNotificationsAsync(long customerId, string message, CancellationToken ct)
{
    var emailTask = _emailSender.SendAsync(customerId, message, ct);
    var pushTask = _pushSender.SendAsync(customerId, message, ct);
    var smsTask = _smsSender.SendAsync(customerId, message, ct);

    await Task.WhenAll(emailTask, pushTask, smsTask);
}
```

#### 3. Best Practices для репозиториев / EF Core
- Запросы на чтение для отображения должны использовать `.AsNoTracking()`.
- Проекция через `.Select(c => new Dto { ... })` исключает вычитку лишних колонок.
- Замена `Single()` / `SingleOrDefault()` на `FirstOrDefaultAsync()`, если не требуется валидация на уникальность внутри БД (так как `Single` выполняет `TOP 2` и проверяет наличие второй записи).

## Задача 3: Вопрос: HTTP-методы, PUT/PATCH, OPTIONS, структура запроса и query-параметры {#task-003-http-methods-qa-http-requests}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Назвать HTTP-методы, отличие PUT от PATCH, что такое OPTIONS, структуру HTTP-запроса и как передать несколько параметров без body.
### Решение кандидата
Кандидат назвал GET, POST, PUT, DELETE, PATCH, OPTIONS. Сказал, что GET запрашивает информацию, POST создаёт сущность, PUT заменяет полностью, PATCH меняет только нужное поле. OPTIONS используется для служебных целей и показывает методы сервера. Структура: протокол, тело, content-type, авторизация. Несколько параметров без body передаются в URL через амперсанд.
### Эталонное решение (AI)
GET — read, POST — create или submission, PUT — replace, PATCH — partial update, DELETE — remove, OPTIONS — metadata или CORS. Запрос: request line, headers, body. Query parameters: key=value pairs separated by ampersand, URL-encoded. PUT idempotent, PATCH not necessarily. Status codes: 200, 201, 204, 400, 401, 403, 404, 500.

## Задача 4: Вопрос: Микросервисы против монолита {#task-004-qa-microservices-vs-monolith}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Преимущества и недостатки микросервисного подхода против монолита.
### Решение кандидата
Кандидат сказал, что монолит сложнее менять, потому что затрагивает все разделы; микросервисы разделены, изолированы, могут работать на разных серверах, масштабировать отдельные сервисы, использовать разные технологии. Монолит проще в разработке, деплое и отладке.
### Эталонное решение (AI)
Микросервисы: независимый деплой, масштабирование, fault isolation, технологическая гибкость, командная автономия. Минусы: сетевая латентность, распределённые транзакции, сложность observability, DevOps, data consistency. Монолит: простота, одна БД, лёгкий деплой, меньше overhead; минусы: сложность масштабирования, coupling, risk of single failure.

## Задача 5: Найти ошибки в JSON {#task-005-json-validation-errors}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
На скрине JSON с переменными найти ошибки.
### Решение кандидата
Кандидат заметил проблемы со скобками: структура не закрыта, непонятно массив или объект; лишние или недостающие скобки; номер карты указан дробным числом, хотя должен быть целым или строкой; проблемы с отступами и выравниванием.
### Эталонное решение (AI)
Проверить: один корневой объект или массив, пары key и value, строки в кавычках, числа без кавычек, массивы в квадратных скобках, объекты в фигурных, нет trailing comma, нет semicolon, вложенность корректна. Номер карты лучше хранить как строку, чтобы сохранить ведущие нули и избежать проблем с числом.

## Задача 6: Найти ошибки в XML {#task-006-xml-error-finding}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
На скрине XML найти ошибки.
### Решение кандидата
Кандидат нашёл несовпадение открывающего и закрывающего тега, лишнюю цифру, отсутствие открывающего тега, проблемы с форматированием и лишний текст.
### Эталонное решение (AI)
XML должен быть well-formed: один корневой элемент, все теги закрыты, имена совпадают, вложенность корректна, атрибуты в кавычках, нет посторонних символов, namespace и encoding корректны.

## Задача 7: Найти ошибки в двух JSON {#task-007-json-validation-errors}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
На скрине два JSON-фрагмента, найти ошибки.
### Решение кандидата
Кандидат сказал, что это два JSON, в первом нет закрывающей скобки, во втором вместо предпоследней скобки должна быть квадратная, есть лишняя точка с запятой, значения должны быть в разных фрагментах.
### Эталонное решение (AI)
JSON не использует semicolon. Каждый документ имеет один корень. Объекты в фигурных скобках, массивы в квадратных. Нельзя просто склеивать два JSON без массива или JSON Lines. Проверить trailing commas, кавычки, вложенность, типы значений.

## Задача 8: Вопрос: Swagger, моки и тестирование нового endpoint {#task-008-swagger-api-testing-endpoint}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Что такое Swagger, использовались ли моки, как тестировать новый endpoint сервиса, чтобы сторонний сервис корректно работал с ним.
### Решение кандидата
Кандидат сказал, что Swagger — библиотека или наглядный формат по эндпоинтам, работали через Postman. Моки — подмена ответов хардкодом. Для endpoint создаёт запрос в Postman и тестирует.
### Эталонное решение (AI)
Swagger или OpenAPI — спецификация API, автодокументация, генерация клиентов и моков. Моки — фиктивные ответы для изоляции тестов. Тестирование endpoint: contract, auth, positive и negative, validation, idempotency, integration with external service, logs, DB, performance, security, error handling, versioning.

## Задача 9: Вопрос: DevTools, локализация бага и уровни логирования {#task-009-manual-qa-devtools-bug-localization-logging-levels}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Где в DevTools смотреть запрос и ответ, как локализовать баг, когда фронт отправляет новые данные, получает 200, но UI не меняется, какие уровни логирования и regex или Kibana.
### Решение кандидата
Кандидат сказал смотреть Network, входящие и исходящие запросы. Для бага проверить, что уходит на бэк: если уходят старые данные — фронт, если новые — бэк; проверить ответ и ошибки. Уровни: trace, debug, info, warn, error. Regex использовал шаблоны, Kibana по стороне.
### Эталонное решение (AI)
DevTools: Network, Payload, Response, Console, Application. Локализация: проверить request payload, status, response body, backend logs, DB state, caching, frontend state, reproduce. Logging levels: TRACE, DEBUG, INFO, WARN, ERROR, FATAL. Structured logs, correlation ID, regex for patterns, Kibana или ELK for search and dashboards.

## Задача 10: Вопрос: CI/CD и очереди сообщений {#task-010-ci-cd-message-queues}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Что такое CI/CD, из каких этапов состоит, разница синхронного и асинхронного обмена, принципы очередей, Kafka topics и partitions.
### Решение кандидата
Кандидат сказал, что CI/CD — непрерывная интеграция и доставка, сборка билда, деплой, Jenkins, devops. Синхронно — ждать ответ, асинхронно — отправить и продолжить. В Kafka есть topics, partitions, consumers, репликация для надёжности.
### Эталонное решение (AI)
CI: commit, build, test, artifact. CD: deploy to staging или prod, automated tests, monitoring, rollback. Sync: request-response, blocking. Async: event-driven, queue, non-blocking. Kafka: topic — logical stream, partition — ordered shard, consumer group, offsets, replication, durability, at-least-once или exactly-once semantics.

## Задача 11: C# Garbage Collector: generations, reachability, heaps, manual collection {#task-011-csharp-garbage-collector-generations-reachability-heaps-manual-collection}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Собеседователь просит объяснить, как работает Garbage Collector в C#/.NET: основные этапы, поколения, достижимость объектов, триггеры запуска, кучи, опасность ручного вызова GC.Collect.
### Решение кандидата
Кандидат говорит, что GC управляет управляемой кучей, строит граф достижимых объектов от корней в стеке, помечает недостижимые, удаляет их, дефрагментирует память. Описывает поколения 0, 1, 2: короткие объекты в 0, пережившие сборку переходят дальше. Триггеры: нехватка памяти, лимит процесса, ручной GC.Collect. Упоминает small object heap и large object heap около 85 КБ, frozen/pinned objects. Полагает, что ручной вызов опасен, потому что может удалить ещё востребованные объекты и занять ресурсы.
### Эталонное решение (AI)
.NET GC — это generational mark-sweep-compact collector. Корни: ссылки в стеке, статические поля, GC handles. Алгоритм: mark reachable objects, sweep unmarked, compact/defragment. Gen0 collects frequently, survivors promoted to Gen1/Gen2. LOH for objects >85KB historically; .NET 8 introduces POH. LOH is less compacted. Triggers: allocation failure, budget, explicit GC.Collect. Manual collection is not recommended in production: it can cause pauses, does not guarantee immediate collection, and may interact with weak references. It does not collect reachable objects. Heaps: SOH, LOH, POH; pinned/frozen for interop/constants. Memory leaks in managed code usually from static collections, event handlers, caches holding references; unmanaged resources need Dispose.

## Задача 12: C# finalization, IDisposable, using, GC.SuppressFinalize {#task-012-csharp-finalization-idisposable-gc-suppressfinalize}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Как вызвать утечку памяти в .NET, что такое финализация, когда использовать IDisposable, как правильно реализовать класс с неуправляемым ресурсом, что будет, если разработчик не вызовет Dispose.
### Решение кандидата
Кандидат называет утечку неуправляемой памяти через файловые дескрипторы без Dispose, а также управляемую утечку через постоянно растущий словарь. Говорит про finalization queue, деструктор, но не знает гарантированно когда вызывается финализация. Предпочитает IDisposable и using, раскрывает using в try/finally. При реализации класса предлагает реализовать IDisposable, в Dispose освободить приватные поля-ресурсы. Не уверен в GC.SuppressFinalize и финализаторе; если Dispose не вызовут, ресурс не освободится.
### Эталонное решение (AI)
Finalizer is non-deterministic last resort, runs on GC thread, can delay reclamation and add overhead. For deterministic cleanup implement IDisposable. Recommended pattern: private bool _disposed; public void Dispose() { Dispose(true); GC.SuppressFinalize(this); } protected virtual void Dispose(bool disposing) { if (_disposed) return; if (disposing) dispose managed resources; release unmanaged resources; _disposed = true; } If class has finalizer, finalizer calls Dispose(false). using ensures Dispose is called even on exception. If user forgets Dispose and there is no finalizer, unmanaged resource may leak until process exit or OS cleanup. Use finalizer only when unmanaged resources exist and Dispose may be missed; always call GC.SuppressFinalize in Dispose to avoid finalizer queue.

## Задача 13: C# concurrency: multithreading, asynchrony, parallelism, race condition, deadlock {#task-013-csharp-concurrency-multithreading-asynchrony-parallelism-race-condition-deadlock}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Дать определения: многопоточность, асинхронность, параллельность. Когда возможна параллельность, что такое race condition и deadlock.
### Решение кандидата
Кандидат описывает многопоточность как несколько потоков, выполняющих операции параллельно, с риском race condition и критическими секциями. Асинхронность связывает с несколькими потоками, отсутствием простоев, await как state machine и передачей операции другому потоку. Параллельность объясняет как выполнение несколькими потоками, упоминает физические ядра процессора. Deadlock — взаимная блокировка потоков.
### Эталонное решение (AI)
Multithreading — наличие нескольких потоков, которые могут выполняться одновременно или чередоваться. Parallelism — фактическое одновременное выполнение на нескольких ядрах. Concurrency — организация нескольких задач, возможно без одновременного выполнения. Asynchrony — неблокирующий стиль выполнения: await позволяет освободить поток во время ожидания I/O, continuation может продолжить на другом потоке или в том же контексте. Parallelism возможна для независимых CPU-bound задач при наличии ядер и отсутствии общих блокировок. Race condition — несинхронизированный доступ к общим изменяемым данным. Deadlock — циклическое ожидание блокировок.

## Задача 14: C# lock/monitor, await inside lock, ConfigureAwait, semaphores {#task-014-csharp-concurrency-lock-await-semaphores}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Как работает lock, почему нельзя использовать строковый литерал, что произойдёт при await внутри lock, как синхронизировать async-код, чем Semaphore отличается от SemaphoreSlim.
### Решение кандидата
Кандидат говорит, что lock — синтаксический сахар над Monitor.Enter/Exit, объект обычно приватный. Строковый литерал плох, потому что может быть общим. Await внутри lock опасен: continuation может выполниться в другом потоке, и Monitor.Exit может вызвать другой поток. Упоминает ConfigureAwait true/false, но не считает решением. Называет семафоры, SemaphoreSlim, Interlocked; Semaphore — межпроцессный, системный, тяжёлый; SemaphoreSlim — внутри процесса, быстрее.
### Эталонное решение (AI)
lock(obj) compiles to Monitor.Enter/Exit in finally. Lock object should be private readonly, not this, string literal, boxed value, or public object. await inside lock is unsafe because the continuation may run on a different thread; the lock is not associated with the async method across await, and Monitor.Exit may be called by a different thread or the lock may be held while the thread is blocked. For async synchronization use SemaphoreSlim, AsyncLock, or avoid holding locks across await. ConfigureAwait controls whether continuation captures original SynchronizationContext; it does not make lock safe. SemaphoreSlim is in-process and supports async WaitAsync; Semaphore can be named and cross-process but heavier. Interlocked for atomic operations.

## Задача 15: C# Task vs Thread, CPU-bound vs IO-bound {#task-015-csharp-thread-vs-task-cpu-vs-io-bound}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Чем Task отличается от Thread, когда использовать Task, когда Thread, что такое CPU-bound задачи.
### Решение кандидата
Кандидат говорит, что Task — абстракция/обещание, Thread — поток приложения, обычно лучше использовать Task. Для CPU-bound не уверен, предполагает многопоточность и шардирование операций.
### Эталонное решение (AI)
Thread is a raw OS thread. Task represents asynchronous operation and can run on thread pool, represent completion, support await, continuations, parallelism. Use Task/async for I/O-bound work. Use Task.Run or Parallel for CPU-bound work to avoid blocking thread pool threads, but limit degree of parallelism. Raw Thread only for special cases: dedicated thread, thread affinity, precise control. CPU-bound tasks benefit from parallelism when independent and enough cores; I/O-bound tasks benefit from asynchrony.

## Задача 16: C# List<T> and Dictionary<TKey,TValue> internal implementation {#task-016-csharp-data-structure-list-dictionary-implementation}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Как устроен List<T>, как работает Dictionary<TKey,TValue>, хэш-таблицы, коллизии, сравнение объектов.
### Решение кандидата
Кандидат говорит, что List — динамический массив, расширяемый размер, IEnumerate, доступ по индексу O(1), при переполнении создаётся новый массив обычно вдвое больше. Dictionary построен на хэш-таблицах, бакеты, GetHashCode, коллизии, сравнение Equals, в лучшем случае O(1), в худшем O(n).
### Эталонное решение (AI)
List<T> stores elements in contiguous array; capacity grows, usually doubles, and copies elements; index access O(1), add amortized O(1), insert/remove in middle O(n). Dictionary<TKey,TValue> uses hash table with buckets; key hash via GetHashCode, equality via IEquatable/Equals. Collisions are resolved by chaining or open addressing depending on implementation; performance depends on hash quality and load factor. For reference types implement value-based equality if needed. ConcurrentDictionary uses partitioned locking for thread safety.

## Задача 17: C# concurrent collections and thread safety {#task-017-csharp-concurrent-collections-thread-safety}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Какие конкурентные коллекции использовались, чем ConcurrentDictionary лучше обычного Dictionary с lock, все ли операции потокобезопасны.
### Решение кандидата
Кандидат говорит, что использовал ConcurrentDictionary для кэша. Полагает, что блокируется только часть словаря, а не весь, поэтому другие потоки могут читать другие области. Чтение обычно потокобезопасно. Упоминает конкурентные стеки/очереди.
### Эталонное решение (AI)
Concurrent collections are designed for multi-threaded access. ConcurrentDictionary uses fine-grained locking/partitioning, so operations on different keys can proceed concurrently; it is not simply a whole-dictionary lock. Reads are safe; TryAdd/TryUpdate/TryGetValue are atomic. Enumeration may reflect a snapshot or may throw if collection changes depending on type. For simple low-contention cases lock + Dictionary may be acceptable, but concurrent collections reduce deadlocks and improve scalability. Use ConcurrentQueue/ConcurrentStack/ConcurrentBag for producer-consumer patterns.

## Задача 18: System architecture: event sourcing on Cassandra, secondary Postgres, Elasticsearch, Rabbit, Redis {#task-018-csharp-architecture-event-sourcing}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Описать текущую архитектуру: персистентные хранилища, event sourcing, вторичные хранилища, поиск, месседжброкер, кэши, миграции, ORM.
### Решение кандидата
Кандидат рассказывает про продукт Diadoc: первичное хранилище Cassandra с таймлайнами и event sourcing, вторичные хранилища Postgres для чтения, фоновые синхронизаторы, Elasticsearch для полнотекстового поиска документов, внутренняя шина на Rabbit, Redis для небольших кэшей, Link to DB для миграций, in-memory кэши на ConcurrentDictionary, DI, логирование, кастомный трейсинг, OpenTelemetry/Prometheus/Grafana.
### Эталонное решение (AI)
This is a CQRS/event-sourcing style architecture: immutable events in Cassandra, projections/materialized views in Postgres for query models, async workers to keep projections consistent, Elasticsearch for full-text search, Rabbit for messaging, Redis for hot cache. Key concerns: eventual consistency, idempotent consumers, outbox pattern, backpressure, monitoring lag, schema evolution, data retention, failover. Link to DB is a lightweight migration tool; EF Core is alternative ORM. Use OpenTelemetry for traces/metrics, Prometheus/Grafana for dashboards, structured logging with correlation IDs.

## Задача 19: Infrastructure: DI, logging, tracing, deployment, testing, serialization {#task-019-csharp-infrastructure-di-logging-tracing-deployment-testing-serialization}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Какие DI-контейнеры, логирование, трейсинг, деплой, тестирование, месседжброкеры, сериализация используются.
### Решение кандидата
Кандидат говорит про внутренний DI-контейнер, переход на Microsoft DI, кастомное логирование, кастомный трейсинг, OpenTelemetry, Prometheus/Grafana, деплой через внутренний инструмент похожий на Kubernetes, тесты в NUnit/xUnit, сервисы и хранилища в Docker, Rabbit, protobuf контракты, System.Text.Json.
### Эталонное решение (AI)
Prefer standard .NET DI, Microsoft.Extensions.DependencyInjection, for testability and ecosystem. Use structured logging, Serilog/NLog, with correlation IDs. Use OpenTelemetry for traces, metrics, logs; Prometheus/Grafana for metrics. Deployment via Kubernetes or internal PaaS; CI/CD with GitLab, tests in Docker. Use xUnit/NUnit consistently. For serialization use System.Text.Json or protobuf for performance; gRPC if needed. Message brokers: RabbitMQ/Kafka depending on ordering, throughput, replay. Caches: Redis with LRU/TTL, local caches for hot data.

## Задача 20: Системный дизайн для сервиса заказов {#task-020-golang-system-design-order-service}
**Источник:** [GOLANG СОБЕСЕДОВАНИЕ OZON НА 380К](https://www.youtube.com/watch?v=z2hdeFw6Q-U)

### Условие
Опишите архитектуру системы, которая включает сервис заказов и сервис аналитики. Как можно улучшить производительность, если сервис аналитики работает медленно?
### Решение кандидата
Кандидат предложил использовать transactional outbox для записи данных в базу данных и асинхронной отправки их в сервис аналитики через брокер сообщений, такой как Kafka.
### Эталонное решение (AI)
Для улучшения производительности можно использовать паттерн CQRS, где запросы на чтение и запись разделяются. Также можно внедрить адаптер, который будет накапливать данные и отправлять их пакетами в сервис аналитики, чтобы избежать перегрузки.

## Задача 21: Реализация паттерна Outbox {#task-021-dotnet-pattern-outbox}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
В процессе работы с кэшбэком необходимо обеспечить транзакционность операций, таких как добавление кэшбэка, обновление статистики и отправка уведомлений. Если одна из операций завершится с ошибкой, все изменения должны быть отменены.
### Решение кандидата
Кандидат предложил использовать паттерн Outbox для обеспечения транзакционности, добавляя записи в специальную таблицу и обрабатывая их с помощью фоновых задач.
### Эталонное решение (AI)
Для реализации паттерна Outbox необходимо создать таблицу, в которую будут записываться события, и реализовать фонового работника, который будет обрабатывать эти события. Это позволит сохранить целостность данных и избежать потери информации при сбоях.

## Задача 22: Обработка многопоточности {#task-022-dotnet-threading-cashback-processing}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
В системе может возникнуть ситуация, когда несколько потоков одновременно пытаются начислить кэшбэк одному и тому же клиенту. Необходимо обеспечить корректную обработку таких случаев, чтобы избежать двойного начисления.
### Решение кандидата
Кандидат предложил использовать блокировку на чтение или оператор 'select for update' для предотвращения одновременного начисления кэшбэка.
### Эталонное решение (AI)
Для решения проблемы можно использовать уровень изоляции транзакций, который предотвращает одновременное чтение и запись одних и тех же данных. Также можно рассмотреть использование распределенной блокировки для обеспечения корректности операций в многопоточной среде.

## Задача 23: Реализация Unit of Work {#task-023-dotnet-design-pattern-unit-of-work}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
Необходимо реализовать паттерн Unit of Work для управления транзакциями в приложении, чтобы обеспечить целостность данных при выполнении нескольких операций.
### Решение кандидата
Кандидат предложил создать класс, который будет управлять несколькими репозиториями и обеспечивать выполнение операций в рамках одной транзакции.
### Эталонное решение (AI)
Паттерн Unit of Work можно реализовать, создав класс, который будет содержать ссылки на репозитории и метод для сохранения изменений, который будет вызывать метод SaveChanges у контекста базы данных.

## Задача 24: Архитектура клиент-сервер {#task-024-architecture-client-server}
**Источник:** [Как проваливаются собеседования ⧸ Разбор реального собеседования на QA Middle+](https://www.youtube.com/watch?v=vp0ijyXVgzc)

### Условие
Опишите, как работает клиент-серверная архитектура. Какие уровни существуют и как они взаимодействуют друг с другом?
### Решение кандидата
Клиент-серверная архитектура — это способ взаимодействия клиента и сервера. У нас есть одноуровневая система, когда это чисто клиент, например, что-то, что находится на телефоне или в браузере. Есть двухуровневая система, когда у нас есть клиент и сервер, и трехуровневая, когда добавляется база данных. Клиенты могут общаться с сервером через HTTP-запросы.
### Эталонное решение (AI)
Клиент-серверная архитектура представляет собой модель, в которой клиент запрашивает ресурсы или услуги у сервера, который обрабатывает запрос и возвращает ответ. Существует одноуровневая архитектура, где клиент и сервер находятся на одном уровне, двухуровневая, где клиент взаимодействует с сервером, и трехуровневая, где добавляется уровень базы данных. Взаимодействие происходит через различные протоколы, такие как HTTP, WebSocket и другие.

## Задача 25: Микросервисная архитектура {#task-025-microservice-architecture}
**Источник:** [Как проваливаются собеседования ⧸ Разбор реального собеседования на QA Middle+](https://www.youtube.com/watch?v=vp0ijyXVgzc)

### Условие
Объясните, что такое микросервисная архитектура и как она работает. Какие преимущества она предоставляет?
### Решение кандидата
Микросервисная архитектура — это когда у нас есть несколько сервисов на проекте, которые взаимосвязаны и взаимодействуют. Каждый сервис является отдельным сервером и может развиваться отдельно. Это позволяет нам фиксировать микросервисы отдельно и проводить интеграционное тестирование.
### Эталонное решение (AI)
Микросервисная архитектура — это подход к разработке программного обеспечения, при котором приложение разбивается на небольшие независимые сервисы, каждый из которых отвечает за определенную функциональность. Преимущества включают возможность независимого развертывания, масштабируемость, упрощение разработки и тестирования, а также улучшение устойчивости системы.

## Задача 26: Асинхронные генераторы {#task-026-python-concept-asynchronous-generators}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Объясните, что такое асинхронные генераторы в Python и как они отличаются от обычных генераторов.
### Решение кандидата
Кандидат объяснил, что асинхронные генераторы позволяют использовать ключевые слова async и await, что позволяет работать с асинхронными операциями. Они могут быть полезны для работы с потоками данных, которые поступают в разное время, например, при чтении из файлов или сетевых соединений.
### Эталонное решение (AI)
Асинхронные генераторы в Python используют ключевые слова async и await, что позволяет им работать с асинхронными операциями. Они позволяют обрабатывать данные по мере их поступления, что особенно полезно в ситуациях, когда данные могут приходить с задержкой, например, при работе с сетевыми запросами или чтении из файлов.

## Задача 27: Репликация в PostgreSQL {#task-027-postgresql-database-replication}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Как работает репликация в PostgreSQL и какие существуют ее типы?
### Решение кандидата
Кандидат объяснил, что в PostgreSQL существует синхронная и асинхронная репликация. Синхронная репликация гарантирует, что данные будут записаны на всех репликах перед подтверждением транзакции, в то время как асинхронная репликация позволяет подтверждать транзакции без ожидания записи на реплики.
### Эталонное решение (AI)
Репликация в PostgreSQL позволяет создавать копии базы данных для повышения доступности и отказоустойчивости. Существует два основных типа репликации: синхронная и асинхронная. Синхронная репликация требует, чтобы данные были записаны на всех репликах перед подтверждением транзакции, что обеспечивает высокую степень согласованности, но может замедлить производительность. Асинхронная репликация позволяет подтверждать транзакции без ожидания записи на реплики, что повышает производительность, но может привести к несогласованности данных.

## Задача 28: Обработка асинхронных запросов {#task-028-python-fastapi-async-requests}
**Источник:** [Python-собес： провал на собеседовании в X5： Почему разработчик получил грейд Junior？](https://www.youtube.com/watch?v=MWHKF2RTodw)

### Условие
Как обрабатывать асинхронные запросы в FastAPI и какие проблемы могут возникнуть при использовании синхронных библиотек?
### Решение кандидата
Кандидат указал на проблемы блокировки, когда синхронные запросы не позволяют обрабатывать другие запросы, и предложил использовать асинхронные библиотеки.
### Эталонное решение (AI)
Использование асинхронных библиотек позволяет избежать блокировки и эффективно обрабатывать множество запросов одновременно, что улучшает производительность приложения.

## Задача 29: Модульность в Java {#task-029-java-modularity-introduction}
**Источник:** [Java-собеседование в МТС： Ошибки, из-за которых ты не пройдешь на Middle](https://www.youtube.com/watch?v=dYEm12kTLPg)

### Условие
Когда появилась модульность в Java и что она означает?
### Решение кандидата
Кандидат затрудняется ответить, но упоминает, что теперь каждый пакет нужно импортировать отдельно, что создает новую структуру.
### Эталонное решение (AI)
Модульность в Java была введена в Java 9. Она позволяет разбивать приложения на модули, что улучшает управление зависимостями и безопасность.

## Задача 30: Эмуляция процессора RISC {#task-030-java-emulator-risc-processor}
**Источник:** [Java-собеседование в МТС： Ошибки, из-за которых ты не пройдешь на Middle](https://www.youtube.com/watch?v=dYEm12kTLPg)

### Условие
Расскажите о проекте по разработке симулятора процессора RISC.
### Решение кандидата
Кандидат описывает, что проект заключался в написании программы для симуляции инструкций процессора, с акцентом на изучение спецификаций и документации.
### Эталонное решение (AI)
Проект по эмуляции процессора RISC включает в себя создание программного обеспечения, которое может интерпретировать и выполнять инструкции, а также требует глубокого понимания архитектуры процессора.

## Задача 31: Архитектура микросервисов {#task-031-java-architecture-microservices}
**Источник:** [Java-собес： менти не дотянул до Middle. Почему нельзя говорить лишнего на собеседовании？](https://www.youtube.com/watch?v=IoXoGi41VtY)

### Условие
Объясните, как устроена архитектура микросервисов и какие преимущества она предоставляет.
### Решение кандидата
Архитектура микросервисов предполагает разделение приложения на небольшие, независимые сервисы, каждый из которых отвечает за свою функциональность. Это позволяет легче масштабировать приложение, обновлять отдельные компоненты и использовать разные технологии для разных сервисов. Однако это также увеличивает сложность управления и взаимодействия между сервисами.
### Эталонное решение (AI)
Архитектура микросервисов делит приложение на независимые сервисы, что позволяет улучшить масштабируемость и гибкость разработки. Каждый сервис может быть написан на своем языке программирования и использовать свои технологии. Однако это требует продуманного управления взаимодействием между сервисами и может усложнить развертывание и тестирование.

## Задача 32: Микросервисные паттерны {#task-032-python-microservices-patterns}
**Источник:** [🔥 Python-собес： Это уровень, за который платят 350k+. Разбор от Senior из Avito](https://www.youtube.com/watch?v=U0NgmwjnP3M)

### Условие
Обсудите паттерны проектирования микросервисов, которые вы знаете, и приведите примеры их использования.
### Решение кандидата
Кандидат упоминает паттерн "Сетевой каркас", который используется для управления взаимодействием между микросервисами, а также паттерн "Команда-Запрос", который разделяет операции изменения данных и чтения данных для улучшения масштабируемости. Также обсуждаются механизмы управления доступом и авторизации на уровне микросервисов.
### Эталонное решение (AI)
Паттерны проектирования микросервисов включают "Сетевой каркас" для управления взаимодействием между сервисами, "Команда-Запрос" для разделения операций записи и чтения, а также "API Gateway" для маршрутизации запросов и управления доступом. Эти паттерны помогают улучшить масштабируемость, безопасность и управляемость микросервисной архитектуры.

## Задача 33: Вопрос: Различия между SSR и SPA {#task-033-javascript-frontend-ssr-vs-spa}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Обсудите различия между серверным рендерингом (SSR) и одностраничными приложениями (SPA). Каковы преимущества и недостатки каждого подхода?
### Решение кандидата
Кандидат объяснил, что в SPA используется клиентский рендеринг, где пустая HTML-страница загружается, а затем подгружается JavaScript-бандл. В случае SSR HTML-страница генерируется на сервере и отправляется клиенту, что позволяет быстрее отображать интерфейс. Также были упомянуты ограничения в SSR, такие как использование хуков и взаимодействие с внешними API.
### Эталонное решение (AI)
SSR обеспечивает более быструю первую отрисовку и лучшее SEO, так как контент доступен сразу. SPA обеспечивает более плавный пользовательский опыт после первоначальной загрузки, но может иметь проблемы с SEO и временем загрузки, если не оптимизирован.

## Задача 34: Вопрос: Проблемы с микрофронтендами {#task-034-javascript-frontend-microfrontends-issues}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Обсудите возможные проблемы, с которыми можно столкнуться при использовании микрофронтендов. Как вы решали эти проблемы в своих проектах?
### Решение кандидата
Кандидат упомянул, что проблемы могут возникать с роутингом, типизацией импортируемых компонентов и передачей состояния между микрофронтендами. Он также отметил, что важно правильно настраивать зависимости между микрофронтендами, чтобы избежать ошибок.
### Эталонное решение (AI)
Проблемы с микрофронтендами могут включать сложности в управлении состоянием, конфликты версий библиотек и проблемы с производительностью. Решения могут включать использование общего хранилища состояния, таких как Redux или Context API, а также применение стратегий для синхронизации версий библиотек.

## Задача 35: Вопрос: CORS и его настройка {#task-035-javascript-web-cors-configuration}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Что такое CORS и как вы настраивали его в своих проектах? Как вы обходили CORS при локальной разработке?
### Решение кандидата
Кандидат объяснил, что CORS (Cross-Origin Resource Sharing) - это политика браузера, которая ограничивает доступ к ресурсам с других доменов. Он упомянул, что настраивал CORS заголовки на сервере и использовал проксирование запросов в Nginx для обхода CORS ошибок при локальной разработке.
### Эталонное решение (AI)
CORS настраивается с помощью заголовков, таких как Access-Control-Allow-Origin, которые указывают, какие домены могут обращаться к ресурсам. Для локальной разработки можно использовать прокси-сервер или расширения браузера, чтобы избежать CORS ошибок.

## Задача 36: Архитектура приложения с использованием базы данных {#task-036-go-architecture-database}
**Источник:** [Go Live Interview с Senior-разработчиком из Ozon](https://www.youtube.com/watch?v=Yt0M8-hfYYQ)

### Условие
Опишите, как вы бы организовали архитектуру приложения, взаимодействующего с базой данных, включая управление соединениями и обработку запросов.
### Решение кандидата
Кандидат предлагает использовать паттерн репозитория для управления доступом к данным и описывает, как инициализировать соединение с базой данных в конструкторе репозитория.
### Эталонное решение (AI)
Архитектура приложения должна включать слой доступа к данным, который управляет соединениями с базой данных через пул соединений. Это позволяет избежать избыточных соединений и улучшает производительность приложения.

## Задача 37: Итерируемые и генераторы {#task-037-python-iterator-generator}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Обсудите, что такое итераторы и генераторы в Python, и в чем их различия.
### Решение кандидата
Кандидат объяснил, что итераторы позволяют проходить по коллекциям, скрывая внутреннюю логику. Генераторы, в свою очередь, являются специальным видом итераторов, которые могут сохранять свое состояние и возвращать значения по мере необходимости. Он также упомянул о методах `next()` и `send()` в генераторах.
### Эталонное решение (AI)
Итераторы в Python реализуют методы `__iter__()` и `__next__()`, позволяя проходить по элементам коллекции. Генераторы, создаваемые с помощью функции с `yield`, автоматически реализуют эти методы и могут сохранять состояние между вызовами, что делает их более эффективными по памяти.

## Задача 38: Асинхронные генераторы {#task-038-python-async-generator}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Обсудите, что такое асинхронные генераторы и как они отличаются от обычных генераторов.
### Решение кандидата
Кандидат объяснил, что асинхронные генераторы позволяют работать с асинхронными итерациями, используя ключевое слово `async`. Они могут использоваться для обработки данных, которые поступают по мере их получения, например, при работе с сетевыми запросами. Он также упомянул, что асинхронные генераторы могут использовать `await` для ожидания завершения асинхронных операций.
### Эталонное решение (AI)
Асинхронные генераторы в Python создаются с использованием ключевого слова `async def` и могут использовать `await` для асинхронного выполнения. Они позволяют обрабатывать данные по мере их поступления, что особенно полезно в сетевых приложениях, где данные могут поступать с задержкой.

## Задача 39: Модель памяти в Java {#task-039-java-memory-model}
**Источник:** [Java： ПЕРВОЕ собеседование в жизни. ТехЛид МТС поставил мне грейд Стажёр.](https://www.youtube.com/watch?v=LI4cpOk5eGs)

### Условие
Опишите модель памяти в Java. Как она устроена и какие области памяти существуют?
### Решение кандидата
Кандидат говорит, что память в Java делится на стек и хип. В стеке хранятся примитивные типы и информация о вызовах функций, а в хипе - объекты.
### Эталонное решение (AI)
Модель памяти в Java включает стек, хип и метапамять (metaspace). Стек используется для хранения локальных переменных и вызовов методов, хип - для объектов, а метапамять - для хранения метаданных классов и статических переменных.

## Задача 40: Идентичность HTTP-запросов {#task-040-http-idempotency-identity}
**Источник:** [Java： ПЕРВОЕ собеседование в жизни. ТехЛид МТС поставил мне грейд Стажёр.](https://www.youtube.com/watch?v=LI4cpOk5eGs)

### Условие
Что такое идемпотентность в контексте HTTP-запросов? Приведите примеры идемпотентных и неидемпотентных методов.
### Решение кандидата
Кандидат объясняет, что идемпотентность - это свойство запроса, при котором повторный запрос с одинаковыми параметрами возвращает один и тот же результат. Примеры: GET и PUT - идемпотентные, POST - неидемпотентный.
### Эталонное решение (AI)
Идемпотентность означает, что повторные запросы с одинаковыми параметрами не изменяют состояние сервера. Примеры идемпотентных методов: GET, PUT, DELETE. Пример неидемпотентного метода: POST, который создает новый ресурс при каждом вызове.

## Задача 41: Конкурентный доступ к слайсу {#task-041-go-concurrency-slice-access}
**Источник:** [Собеседуем Go-разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=s1Lo_RQx3xs)

### Условие
Опишите, что произойдет, если несколько горутин попытаются одновременно записать значения в один и тот же элемент слайса. Как можно избежать проблем?
### Решение кандидата
Кандидат указал на возможность гонки данных и предложил использовать мьютексы для синхронизации доступа.
### Эталонное решение (AI)
Используйте sync.Mutex для блокировки доступа к слайсу во время записи, чтобы избежать гонки данных.

## Задача 42: Конкурентный доступ к мапе {#task-042-go-concurrency-map-access}
**Источник:** [Собеседуем Go-разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=s1Lo_RQx3xs)

### Условие
Что произойдет, если несколько горутин попытаются одновременно записать значения в одну и ту же мапу? Как можно избежать проблем?
### Решение кандидата
Кандидат указал на возможность паники и предложил использовать синхронизированную мапу или мьютексы для защиты.
### Эталонное решение (AI)
Используйте sync.Map для безопасного конкурентного доступа к мапе или синхронизируйте доступ с помощью sync.Mutex.

## Задача 43: Объяснение работы планировщика в Go {#task-043-go-scheduler-explanation}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Объясните, как работает планировщик в Go, включая его модель GMP и локальные очереди.
### Решение кандидата
Планировщик в Go работает по модели GMP (Goroutine, Machine, Process). Он распределяет горутины по процессам и использует локальные очереди для оптимизации выполнения. Каждое ядро имеет свою локальную очередь, что позволяет избежать глобальных блокировок. Если локальная очередь пуста, планировщик может заимствовать горутины из других локальных очередей.
### Эталонное решение (AI)
Планировщик в Go использует модель GMP, где G - это горутина, M - это операционная система поток, а P - это процессор. Каждое ядро имеет локальную очередь (LRQ) для горутин, что позволяет эффективно распределять задачи и минимизировать блокировки. Если LRQ пуста, планировщик может заимствовать горутины из глобальной очереди или других локальных очередей.

## Задача 44: Примитивы синхронизации в Go {#task-044-go-synchronization-primitives}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Перечислите и объясните примитивы синхронизации в Go.
### Решение кандидата
В Go есть несколько примитивов синхронизации, таких как атомарные операции, каналы, мьютексы и группы ожидания. Каждый из них используется для решения различных задач синхронизации между горутинами.
### Эталонное решение (AI)
Примитивы синхронизации в Go включают: 1) Атомарные операции для безопасного доступа к переменным; 2) Каналы для передачи данных между горутинами; 3) Мьютексы для защиты критических секций; 4) Группы ожидания (WaitGroups) для ожидания завершения нескольких горутин.

## Задача 45: Асинхронность в Python {#task-045-python-concept-asynchronicity}
**Источник:** [Собеседование Python： Senior инженер из Avito сказал ＂Беру в команду＂](https://www.youtube.com/watch?v=9cO7UcqTZMI)

### Условие
Объясните, что такое асинхронность в Python и как она реализуется. Какие преимущества она предоставляет?
### Решение кандидата
Кандидат описывает асинхронность как способ выполнения задач, который позволяет не блокировать выполнение программы, когда одна задача ожидает завершения другой. Упоминает о библиотеке asyncio.
### Эталонное решение (AI)
Асинхронность в Python позволяет выполнять несколько задач одновременно, не блокируя выполнение программы. Это достигается с помощью корутин и цикла событий, реализованных в библиотеке asyncio. Асинхронность особенно полезна для задач, связанных с вводом-выводом, так как она позволяет эффективно использовать ресурсы, не дожидаясь завершения операций ввода-вывода.

## Задача 46: Потоки и процессы в Python {#task-046-python-concurrency-threads-processes}
**Источник:** [Собеседование Python： Senior инженер из Avito сказал ＂Беру в команду＂](https://www.youtube.com/watch?v=9cO7UcqTZMI)

### Условие
Объясните различия между потоками и процессами в Python. В каких ситуациях лучше использовать каждый из них?
### Решение кандидата
Кандидат объясняет, что потоки легче и быстрее создаются, но имеют ограничения из-за GIL, тогда как процессы изолированы друг от друга и могут использовать несколько ядер.
### Эталонное решение (AI)
Потоки в Python - это легковесные единицы выполнения, которые используют общую память, но ограничены GIL, что мешает истинной параллельности. Процессы, с другой стороны, являются независимыми экземплярами программы с собственной памятью и могут использовать несколько ядер. Потоки лучше подходят для задач ввода-вывода, тогда как процессы лучше использовать для вычислительно интенсивных задач.

## Задача 47: Синхронное и асинхронное программирование {#task-047-python-programming-sync-async}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Объясните разницу между синхронным и асинхронным программированием, а также приведите примеры, когда лучше использовать каждый из подходов.
### Решение кандидата
Синхронное программирование выполняет задачи последовательно, в то время как асинхронное позволяет выполнять задачи параллельно, не блокируя выполнение других операций. Асинхронность полезна при работе с I/O операциями, где время ожидания может быть использовано для обработки других запросов. Например, в веб-сервере асинхронный подход позволяет обрабатывать несколько запросов одновременно, не дожидаясь завершения каждого из них.
### Эталонное решение (AI)
Синхронное программирование выполняет задачи последовательно, блокируя выполнение до завершения каждой операции. Асинхронное программирование позволяет выполнять несколько операций одновременно, что особенно полезно при работе с I/O операциями, такими как сетевые запросы. Асинхронный подход позволяет улучшить производительность и отзывчивость приложений, особенно в веб-серверах и приложениях, работающих с большим количеством пользователей.

## Задача 48: Обработка запросов в HTTP-сервере {#task-048-go-http-server-request-handling}
**Источник:** [Собеседуем Go разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=5HSGuUaaPxY)

### Условие
Опишите, как должен быть реализован HTTP-сервер для обработки запросов, включая использование контекста и управление соединениями с базой данных.
### Решение кандидата
Кандидат говорит о том, что нужно использовать контекст запроса для управления временем жизни соединений и обрабатывать ошибки, возникающие при взаимодействии с базой данных. Он также упоминает, что соединение с базой данных должно быть открыто один раз и использоваться для всех запросов.
### Эталонное решение (AI)
HTTP-сервер должен обрабатывать запросы асинхронно, используя контекст для управления временем жизни соединений. Соединение с базой данных должно быть открыто при старте сервера и закрыто при его остановке. Обработка ошибок должна быть реализована для всех операций с базой данных.

## Задача 49: Архитектура для генерации форм {#task-049-javascript-architecture-form-generation}
**Источник:** [Реальное собеседование с интересным лайвкодингом на Middle⧸Senior Frontend-разработчика на ЗП 320К!](https://www.youtube.com/watch?v=k9HE34qB9pQ)

### Условие
Необходимо разработать архитектуру для создания 60 различных форм, где каждая форма соответствует одному файлу на бэкенде. Формы должны быть динамическими и управляться через API.
### Решение кандидата
Кандидат предложил создать общий модуль для управления шаблонами форм, который будет включать методы для получения, создания, редактирования и удаления шаблонов. Формы будут строиться на основе JSON-структуры, получаемой с бэкенда.
### Эталонное решение (AI)
1. Создать API с методами для управления шаблонами форм: GET, POST, PATCH, DELETE.
2. Шаблоны форм должны храниться в виде JSON-структур, которые описывают поля и их атрибуты.
3. На фронте реализовать динамическое создание форм на основе полученных шаблонов, включая валидацию данных.

## Задача 50: Проблемы с архитектурой кода {#task-050-python-architecture-code-issues}
**Источник:** [Python-собес： провал на собеседовании в X5： Почему разработчик получил грейд Junior？](https://www.youtube.com/watch?v=MWHKF2RTodw)

### Условие
Обсудите архитектурные проблемы в коде, где классы инициализируются, но не используются повторно.
### Решение кандидата
Кандидат отметил, что это может привести к избыточности и усложнению кода. Он предложил использовать композицию вместо агрегации.
### Эталонное решение (AI)
Использование композиции позволяет уменьшить зависимость классов друг от друга и улучшить читаемость кода. Это также способствует повторному использованию кода и снижает вероятность ошибок.

## Задача 51: Проектирование системы Tinder {#task-051-system-design-tinder}
**Источник:** [Mock-собеседование по System Design ｜ Ex-Team Lead Яндекс](https://www.youtube.com/watch?v=qsEvKryZ5YA)

### Условие
Спроектировать систему Tinder, которая будет предлагать анкеты пользователям на основе их предпочтений и геолокации. Система должна обрабатывать лайки и дизлайки, а также определять матчи между пользователями.
### Решение кандидата
Кандидат предложил архитектуру, в которой пользователи регистрируются и создают профили, состоящие из фотографии и описания. Система должна обрабатывать запросы на получение анкет, а также хранить информацию о лайках и матчах в базе данных. Для обработки событий кандидат предложил использовать Kafka для передачи сообщений о матчах. Также обсуждались нефункциональные требования, такие как ожидаемая нагрузка и масштабируемость системы.
### Эталонное решение (AI)
Эталонное решение включает в себя использование микросервисной архитектуры, где каждый компонент системы отвечает за свою часть функциональности. Для хранения данных можно использовать реляционные базы данных для профилей пользователей и NoSQL базы для хранения лайков и матчей. Веб-сокеты могут быть использованы для обеспечения быстрого взаимодействия с пользователями, а Kafka для асинхронной обработки событий.

## Задача 52: Масштабируемый и безопасный API {#task-052-python-api-scalable-secure}
**Источник:** [Настоящее собеседование на MIDDLE Python разработчика (правильные ответы)](https://www.youtube.com/watch?v=Sg83kDt8wrI)

### Условие
Раскрой, пожалуйста, что ты подразумеваешь под масштабируемым и безопасным API?
### Решение кандидата
Под масштабируемым я подразумеваю, что не было привязки к состоянию. А безопасный - это использование JWT токенов.
### Эталонное решение (AI)
Масштабируемый API должен поддерживать горизонтальную масштабируемость, что включает в себя кэширование, балансировку нагрузки и возможность обработки большого количества запросов. Безопасный API должен использовать механизмы аутентификации и авторизации, такие как JWT, а также учитывать аудит и управление доступом.

## Задача 53: Внедрение кэша {#task-053-python-cache-implementation}
**Источник:** [Настоящее собеседование на MIDDLE Python разработчика (правильные ответы)](https://www.youtube.com/watch?v=Sg83kDt8wrI)

### Условие
Когда стоит внедрять кэш и какие есть нюансы использования кэша?
### Решение кандидата
Кэш стоит внедрять, когда данные редко обновляются. Нужно помнить о том, что кэш может содержать устаревшую информацию и необходимо реализовать инвалидацию кэша.
### Эталонное решение (AI)
Кэш следует внедрять для ускорения доступа к данным, которые редко изменяются. Важно учитывать, что необходимо реализовать механизмы инвалидации кэша, чтобы избежать использования устаревших данных, а также следить за объемом кэша, чтобы не перегружать память.

## Задача 54: Безопасная аутентификация {#task-054-python-security-authentication}
**Источник:** [Настоящее собеседование на MIDDLE Python разработчика (правильные ответы)](https://www.youtube.com/watch?v=Sg83kDt8wrI)

### Условие
Расскажи поподробнее, как работает твоя система аутентификации и в чем заключается безопасность.
### Решение кандидата
Аутентификация была реализована через JWT токены, которые состоят из рефреш и access токенов.
### Эталонное решение (AI)
Система аутентификации на основе JWT токенов включает в себя создание двух типов токенов: access токен, который имеет короткий срок действия, и рефреш токен, который используется для получения нового access токена. Это обеспечивает безопасность, так как даже если access токен будет украден, он быстро станет недействительным.

## Задача 55: Работа интерпретатора CPython {#task-055-python-interpreter-cpython}
**Источник:** [Настоящее собеседование на MIDDLE Python разработчика (правильные ответы)](https://www.youtube.com/watch?v=Sg83kDt8wrI)

### Условие
Как интерпретатор CPython исполняет питоновский файл поэтапно?
### Решение кандидата
Файл интерпретируется в байт-код и записывается в файлы с расширением .pyc. Если изменений не было, то запускается именно он.
### Эталонное решение (AI)
CPython выполняет файл поэтапно: сначала он разбирает файл на токены, затем строит абстрактное синтаксическое дерево (AST), компилирует его в байт-код и, если нет изменений, использует кэшированный байт-код для выполнения программы.

## Задача 56: Свойства общих модулей в 1С {#task-056-1c-properties-common-modules}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Каковы свойства общих модулей в 1С? Объясните, что они делают.
### Решение кандидата
Привилегированный серверный вызов, выбор места работы общего модуля (на клиенте или сервере), кэширование значений.
### Эталонное решение (AI)
Свойства общих модулей включают возможность выбора места выполнения (клиент или сервер), кэширование значений для оптимизации производительности и привилегированные вызовы, которые позволяют выполнять код независимо от прав пользователя.

## Задача 57: Транзакции в 1С {#task-057-1c-transaction-definition}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Что такое транзакция в 1С и для чего она используется?
### Решение кандидата
Транзакция - это бинарный элемент, который либо выполняется полностью, либо не выполняется вообще. Пример - перевод денег. Есть два типа транзакций: явные и неявные.
### Эталонное решение (AI)
Транзакция в 1С - это механизм, обеспечивающий целостность данных, который гарантирует, что все операции в рамках транзакции будут выполнены успешно или не будут выполнены вовсе. Явные транзакции управляются программистом, а неявные - системой.

## Задача 58: Вложенные транзакции в 1С {#task-058-1c-transaction-nested-transactions}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Как работают вложенные транзакции в 1С?
### Решение кандидата
Вложенные транзакции в 1С не работают. Если вложенная транзакция завершается с ошибкой, то вся транзакция также завершается с ошибкой.
### Эталонное решение (AI)
В 1С не поддерживаются вложенные транзакции. Если возникает ошибка в вложенной транзакции, то вся родительская транзакция также откатывается.

## Задача 59: События документа в 1С {#task-059-1c-event-document-functionality}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Какова функциональность событий документа в 1С, таких как перед записью, во время записи и обработка исполнения?
### Решение кандидата
Перед записью - это проверка, во время записи - это фактическая запись документа, а обработка исполнения - это проверка возможности проведения и любые движения в регистрах.
### Эталонное решение (AI)
События документа в 1С позволяют выполнять проверки перед записью, осуществлять фактическую запись документа и обрабатывать бизнес-логику, связанную с движениями в регистрах. Эти события обеспечивают контроль целостности данных и бизнес-процессов.

## Задача 60: GIL в Python {#task-060-python-concurrency-gil}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Что такое GIL (Global Interpreter Lock) в Python и как он влияет на многопоточность?
### Решение кандидата
Кандидат объясняет, что GIL - это механизм, который делает Python потоко-безопасным, позволяя только одному потоку выполнять байт-код Python в любой момент времени. Он упоминает, что это может привести к проблемам с производительностью в многопоточных приложениях, так как потоки не могут эффективно использовать многоядерные процессоры.
### Эталонное решение (AI)
GIL (Global Interpreter Lock) - это механизм, который предотвращает одновременное выполнение нескольких потоков Python. Это делает Python потоко-безопасным, но также ограничивает производительность многопоточных приложений, так как только один поток может выполнять байт-код в любой момент времени. Для обхода этой проблемы можно использовать многопроцессорность или асинхронное программирование.

## Задача 61: Различие между SAS и PaaS {#task-061-sas-paas-difference}
**Источник:** [КРУТЕЙШЕЕ СОБЕСЕДОВАНИЕ на Python-разработчика (кандидат разнес на собеседовании)](https://www.youtube.com/watch?v=avK0RjT8an0)

### Условие
Объясните разницу между SAS (Software as a Service) и PaaS (Platform as a Service). Как это влияет на разработку и развертывание приложений?
### Решение кандидата
Кандидат объяснил, что SAS - это когда код работает на собственных серверах или в облаке, а PaaS - это когда программное обеспечение передается клиенту для установки на его серверах. Он также отметил, что ошибки в PaaS могут быть более затратными для исправления.
### Эталонное решение (AI)
SAS предоставляет пользователям доступ к программному обеспечению через интернет, в то время как PaaS предоставляет платформу для разработки и развертывания приложений. В SAS пользователи не заботятся о серверной инфраструктуре, в то время как в PaaS разработчики должны управлять средой развертывания.

## Задача 62: Проектирование системы Twitter {#task-062-system-design-twitter}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Спроектировать систему, аналогичную Twitter, с основной функциональностью публикации твитов и просмотра ленты. Лента должна быть основана на подписках пользователей и пользовательских твитах. Необходимо учесть лайки, дизлайки и комментарии, а также ограничения по длине твита и количеству медиафайлов.
### Решение кандидата
Кандидат предложил реализовать ленту в обратном хронологическом порядке, ограничить длину твита до 280 символов и разрешить прикрепление только одной картинки. Также было предложено ограничить количество подписчиков до 1 миллиона и учесть, что пользователи будут чаще читать, чем писать твиты.
### Эталонное решение (AI)
Для реализации системы Twitter необходимо использовать микросервисную архитектуру, где каждый сервис отвечает за свою функциональность: сервис твитов, сервис подписок, сервис ленты и сервис медиа. Для хранения данных можно использовать реляционные базы данных для подписок и NoSQL базы для твитов. Также важно учесть кэширование ленты для быстрого доступа к данным.

## Задача 63: Обработка твитов и медиафайлов {#task-063-python-system-design-twitter-media-processing}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как будет происходить загрузка и обработка твитов с медиафайлами? Нужно определить, как будет выглядеть процесс загрузки медиа и связывания его с твитом.
### Решение кандидата
Кандидат предложил двухэтапный процесс: сначала загрузить медиафайл, получить его ID, а затем создать твит с прикрепленным ID медиафайла. Это стандартное решение, которое часто используется в подобных системах.
### Эталонное решение (AI)
Для загрузки медиафайлов можно использовать облачные хранилища, такие как S3. Процесс загрузки должен быть асинхронным, чтобы не блокировать создание твита. Также важно учитывать возможность удаления неиспользуемых медиафайлов, если твит не был опубликован.

## Задача 64: Кэширование ленты пользователей {#task-064-system-design-cache-user-feed}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как будет организовано кэширование ленты пользователей для быстрого доступа к данным? Нужно определить, как обновлять кэш при создании новых твитов.
### Решение кандидата
Кандидат предложил использовать Redis для кэширования ленты, где ключом будет ID пользователя, а значением - массив твитов. При создании нового твита необходимо обновлять кэш, используя асинхронную очередь, например, Kafka.
### Эталонное решение (AI)
Кэширование ленты пользователей должно быть организовано таким образом, чтобы минимизировать обращения к базе данных. При создании твита можно использовать паттерн "transactional outbox" для обеспечения согласованности данных между кэшем и базой данных.

## Задача 65: Обработка знаменитостей в системе {#task-065-system-design-celebrities-processing}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как система будет обрабатывать пользователей с большим количеством подписчиков (знаменитостей)? Нужно определить, как оптимизировать операции записи для таких пользователей.
### Решение кандидата
Кандидат предложил не обновлять ленты подписчиков знаменитостей при создании их твитов, а только обновлять их собственную ленту. При этом, если подписчик знаменитости запрашивает свою ленту, кэш инвалидируется, и данные загружаются из базы.
### Эталонное решение (AI)
Для оптимизации работы с знаменитостями можно использовать флаг в базе данных, который будет указывать, является ли пользователь знаменитостью. Это позволит избежать ненужных операций записи и инвалидации кэша для всех подписчиков.

## Задача 66: Масштабируемость и отказоустойчивость системы {#task-066-system-design-scalability-fault-tolerance}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как система будет масштабироваться и обеспечивать отказоустойчивость? Нужно определить архитектурные решения для достижения этих целей.
### Решение кандидата
Кандидат отметил, что система состоит из stateless сервисов, что позволяет легко масштабировать их, добавляя новые инстансы. Базы данных и очереди сообщений можно реплицировать для обеспечения отказоустойчивости.
### Эталонное решение (AI)
Для обеспечения масштабируемости системы можно использовать горизонтальное масштабирование, шардирование баз данных и интеграцию с CDN для разгрузки хранилищ. Также важно следить за производительностью и оптимизировать запросы к базе данных.

## Задача 67: Дизайн системы для депрессора {#task-067-design-system-depressor}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Разработать архитектуру системы для депрессора, который будет взаимодействовать с внутренней базой данных и интернетом для проверки гипотез менеджеров и аналитиков. Система должна иметь возможность генерировать ответы на запросы и предоставлять ссылки на источники информации.
### Решение кандидата
Кандидат предложил архитектуру, включающую планировщик, агентов для выполнения задач, и верификатор для проверки результатов. Планировщик формирует список задач для агентов, которые могут быть веб-скрайперами или SQL-агентами. Верификатор проверяет, достаточно ли информации для ответа и генерирует диплинки на источники.
### Эталонное решение (AI)
Эталонное решение может включать использование микросервисной архитектуры, где каждый компонент (планировщик, агенты, верификатор) реализован как отдельный сервис. Использование очередей сообщений для взаимодействия между сервисами и базы данных для хранения результатов и логов. Также можно рассмотреть использование API для интеграции с внешними источниками данных.

## Задача 68: Архитектура системы для обработки запросов {#task-068-architecture-system-request-processing}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Определить архитектуру системы, которая будет обрабатывать запросы от пользователей, включая взаимодействие с базами данных и внешними API.
### Решение кандидата
Кандидат описал архитектуру, включающую входные точки для запросов, обработку запросов через планировщик, выполнение задач агентами и верификацию результатов. Каждый компонент системы имеет свои входные и выходные данные, что позволяет гибко управлять процессом обработки запросов.
### Эталонное решение (AI)
Эталонное решение может включать использование RESTful API для взаимодействия с клиентами, а также применение паттернов проектирования, таких как MVC или CQRS, для структурирования кода и управления состоянием приложения.

## Задача 69: Разница между грутинами и потоками {#task-069-golang-concurrency-goroutines-vs-threads}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Объясните разницу между грутинами и потоками, а также их преимущества и недостатки.
### Решение кандидата
Грутины - это легковесные потоки исполнения, управляемые рантаймом Go, в то время как потоки операционной системы управляются самой ОС и весят больше. Грутины позволяют более эффективно использовать ресурсы и обеспечивают большую конкурентность.
### Эталонное решение (AI)
Грутины занимают меньше памяти и позволяют создавать большее количество параллельных задач, чем потоки ОС. Это делает их более подходящими для высоконагруженных приложений.

## Задача 70: Планировщик Go {#task-070-go-scheduler-explanation}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Опишите, как работает планировщик Go и его основные компоненты.
### Решение кандидата
Планировщик Go работает по модели GMP (Грутины, Потоки, Процессоры). Он распределяет грутины по потокам ОС, используя локальные очереди и механизмы, такие как Netpoller для неблокирующих вызовов.
### Эталонное решение (AI)
Планировщик использует локальные очереди для оптимизации работы с грутинами, что позволяет избежать глобальных блокировок и эффективно распределять задачи между потоками.

## Задача 71: Проблемы с грутинами {#task-071-golang-concurrency-goroutines-issues}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Какие проблемы могут возникнуть при работе с грутинами?
### Решение кандидата
Основные проблемы включают утечки грутин, дедлоки и гонки данных. Утечки происходят, когда грутины не завершаются, а дедлоки возникают, когда все грутины ожидают друг друга.
### Эталонное решение (AI)
Проблемы с грутинами могут быть решены с помощью правильного управления синхронизацией и использования инструментов для выявления гонок данных.

## Задача 72: Контейнеризация и виртуализация {#task-072-golang-virtualization-containerization}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Объясните разницу между контейнеризацией и виртуализацией.
### Решение кандидата
Виртуализация создает несколько независимых ОС на одном хосте, тогда как контейнеризация использует одну ОС и изолирует приложения в контейнерах, что требует меньше ресурсов.
### Эталонное решение (AI)
Контейнеризация более легковесна и эффективна, так как не требует отдельного ядра для каждой ОС, что делает её более подходящей для микросервисной архитектуры.

## Задача 73: Объяснение потока RAG {#task-073-ml-explanation-rag-flow}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Объясните поток работы RAG, начиная с базовой версии и углубляясь в детали.
### Решение кандидата
Кандидат описал, что поток RAG начинается с получения запроса, после чего происходит его обработка и маршрутизация к различным источникам данных, включая SQL базы данных и векторные базы данных. Затем происходит повторная сортировка и генерация ответа с использованием LLM.
### Эталонное решение (AI)
Поток RAG включает в себя получение запроса, его обработку, маршрутизацию к различным источникам данных, выполнение повторной сортировки с использованием моделей ранжирования и генерацию ответа с использованием LLM. Важно учитывать, как данные добавляются в векторную базу данных и какие алгоритмы используются для этого.

## Задача 74: Объяснение HNSW {#task-074-ml-algorithm-hnsw-explanation}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Объясните, что такое HNSW и как он работает.
### Решение кандидата
Кандидат объяснил, что HNSW (Hierarchical Navigable Small World) использует иерархическую структуру для поиска ближайших соседей, начиная с широких выборок и постепенно уточняя результаты.
### Эталонное решение (AI)
HNSW - это алгоритм, который использует иерархическую навигацию для поиска ближайших соседей. Он начинает с поиска на более высоком уровне иерархии, а затем уточняет результаты, сравнивая с соседями на более низких уровнях, что позволяет достичь логарифмической сложности поиска.

## Задача 75: Параметры HNSW {#task-075-ml-algorithm-hnsw-parameters}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Какие три параметра необходимо учитывать при использовании HNSW?
### Решение кандидата
Кандидат упомянул, что это скорость, точность и использование памяти.
### Эталонное решение (AI)
При использовании HNSW необходимо балансировать между тремя параметрами: количеством соседей, которые мы рассматриваем, скоростью поиска и точностью результатов. Увеличение одного параметра может привести к снижению другого.

## Задача 76: Архитектура трансформеров {#task-076-architecture-transformers-nlp-overview}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Опишите архитектуру трансформеров на высоком уровне.
### Решение кандидата
Кандидат описал, что текст разбивается на токены, которые затем преобразуются в векторные представления с использованием позиционных кодировок и проходят через линейные слои и механизмы внимания.
### Эталонное решение (AI)
Архитектура трансформеров включает в себя процесс, где текст разбивается на токены, которые затем преобразуются в векторные представления с добавлением позиционных кодировок. Эти векторы проходят через слои внимания и линейные слои, что позволяет модели учитывать контекст и взаимосвязи между токенами.

## Задача 77: Различия между BERT и GPT {#task-077-nlp-difference-bert-gpt}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
В чем различия между BERT и GPT?
### Решение кандидата
Кандидат отметил, что основное различие заключается в том, что BERT использует кодировщик-декодер, а GPT - только декодер, что влияет на маскирование токенов.
### Эталонное решение (AI)
BERT использует архитектуру кодировщика-декодера и позволяет учитывать контекст как слева, так и справа от токена, в то время как GPT использует только декодер и маскирует будущие токены, что позволяет предсказывать следующий токен на основе предыдущих.

## Задача 78: Многошаговое внимание {#task-078-ml-concept-multi-step-attention}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Что такое многошаговое внимание и зачем оно нужно?
### Решение кандидата
Кандидат объяснил, что многошаговое внимание позволяет параллельно обрабатывать несколько матриц, что ускоряет вычисления и позволяет выявлять различные связи между токенами.
### Эталонное решение (AI)
Многошаговое внимание позволяет разделить вектор на несколько частей и обрабатывать их параллельно, что не только ускоряет вычисления, но и позволяет модели выявлять различные связи между токенами, улучшая качество представления.

## Задача 79: Дизайн системы для депрессора {#task-079-design-system-depressor}
**Источник:** [Реальное ML-собеседование： RAG, LLM, NLP и вопросы, на которых сыпятся кандидаты.](https://www.youtube.com/watch?v=jmOzoC02-zQ)

### Условие
Спроектируйте систему для депрессора, который будет взаимодействовать с внутренней базой данных и интернетом для тестирования управленческих гипотез.
### Решение кандидата
Кандидат предложил использовать планировщик, который будет управлять запросами и запускать несколько агентов для сбора информации из различных источников, включая SQL и веб-скраперы.
### Эталонное решение (AI)
Система депрессора должна включать планировщик, который формирует список задач и управляет несколькими агентами, которые собирают информацию из различных источников. Каждый агент должен иметь возможность взаимодействовать с базами данных и веб-ресурсами, а также проверять достоверность полученной информации.

## Задача 80: Обработка гонок в Go {#task-080-go-concurrency-race-condition}
**Источник:** [CОБЕСЕДОВАНИЕ В Т-БАНК НА ГОФЕРА ⧸ ИНТЕРВЬЮ СТАЖЁРА](https://www.youtube.com/watch?v=WclJtjQXptU)

### Условие
В процессе работы с кэшем в Go возникла проблема гонок, когда несколько горутин одновременно обращаются к одной и той же памяти. Необходимо определить, как решить эту проблему и какие инструменты для этого использовать.
### Решение кандидата
Кандидат предложил использовать мьютексы для синхронизации доступа к кэшу, чтобы избежать гонок. Он объяснил, как мьютексы работают и как их использовать для блокировки доступа к кэшу во время записи и чтения.
### Эталонное решение (AI)
Эталонное решение должно включать использование мьютексов для синхронизации доступа к кэшу, а также объяснение, как правильно их использовать, чтобы избежать дедлоков и гонок.

## Задача 81: Устранение утечек памяти {#task-081-interview-memory-leak}
**Источник:** [CОБЕСЕДОВАНИЕ В Т-БАНК НА ГОФЕРА ⧸ ИНТЕРВЬЮ СТАЖЁРА](https://www.youtube.com/watch?v=WclJtjQXptU)

### Условие
Сервис, использующий кэш, начал падать через несколько дней работы. Необходимо выяснить, что вызывает падение и как устранить утечки памяти.
### Решение кандидата
Кандидат предположил, что проблема может быть связана с переполнением кэша и предложил реализовать механизм очистки кэша, чтобы избежать утечек памяти. Он также упомянул о необходимости мониторинга и логирования для выявления проблем.
### Эталонное решение (AI)
Эталонное решение должно включать в себя реализацию механизма очистки кэша, а также использование профилирования памяти для выявления утечек и проблем с производительностью.

## Задача 82: Принципы ООП в Go {#task-082-go-oop-principles}
**Источник:** [Успешное собеседование в Яндекс： Go-разработчик, которого одобрили на мидла. Разбор.](https://www.youtube.com/watch?v=3xNiAjmRSf0)

### Условие
Как Go реализует инкапсуляцию, наследование и полиморфизм?
### Решение кандидата
Полиморфизм в Go реализуется с помощью интерфейсов и обобщений. Инкапсуляция достигается через различные зоны видимости. Наследование в Go отсутствует, но можно использовать встраивание.
### Эталонное решение (AI)
Полиморфизм в Go реализуется через интерфейсы, что позволяет использовать один и тот же код с разными типами данных. Инкапсуляция достигается через использование заглавных и строчных букв в именах функций и структур, определяющих их видимость. В Go нет традиционного наследования, но встраивание позволяет использовать поля и методы других структур.

## Задача 83: Сравнение микросервисов и монолита {#task-083-architecture-microservices-vs-monolith}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Объясните преимущества и недостатки подхода микросервисов по сравнению с монолитной архитектурой.
### Решение кандидата
Микросервисы легче масштабировать и развивать, так как каждый сервис независим. Монолит же проще в разработке и отладке, но сложнее масштабировать и изменять. Если что-то ломается в монолите, это может повлиять на всю систему.
### Эталонное решение (AI)
Микросервисы позволяют независимое развертывание и масштабирование, что делает их более гибкими. Монолиты проще в разработке, но изменения в одном компоненте могут вызвать проблемы в других частях системы.

## Задача 84: Принципы построения очередей {#task-084-qa-principles-queues}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Объясните разницу между синхронной и асинхронной коммуникацией.
### Решение кандидата
Синхронная коммуникация требует ожидания ответа от второго приложения, в то время как асинхронная позволяет продолжать выполнение задач без ожидания ответа.
### Эталонное решение (AI)
Синхронная коммуникация блокирует поток до получения ответа, тогда как асинхронная позволяет отправлять сообщения и продолжать выполнение других задач.

## Задача 85: Разница между SaaS и on-premise {#task-085-software-as-a-service-difference-saas-on-premise}
**Источник:** [КРУТЕЙШЕЕ СОБЕСЕДОВАНИЕ на Python-разработчика (кандидат разнес на собеседовании)](https://www.youtube.com/watch?v=avK0RjT8an0)

### Условие
Объясните разницу между SaaS (Software as a Service) и on-premise решениями. Как это влияет на разработку и поддержку программного обеспечения?
### Решение кандидата
Кандидат объяснил, что SaaS означает, что код работает на серверах разработчика, и в случае проблем можно быстро исправить ошибки. В то время как on-premise решения требуют, чтобы клиент устанавливал софт на свои сервера, что усложняет процесс исправления ошибок.
### Эталонное решение (AI)
SaaS позволяет разработчикам быстро развертывать и обновлять приложения, в то время как on-premise требует больше времени на установку и поддержку, а также может быть более затратным в обслуживании.

## Задача 86: Обработка событий с турникетов {#task-086-go-event-processing-turnstiles}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
Разработать конвейер обработки событий с турникетов, который будет обеспечивать гарантии доставки и обработку событий в реальном времени. Система должна быть способна обрабатывать события, поступающие с турникетов, и передавать их в другие сервисы для дальнейшей обработки.
### Решение кандидата
Кандидат предложил использовать Kafka для обеспечения гарантии доставки событий. Он описал архитектуру системы, где события с турникетов поступают в Kafka, а затем обрабатываются различными сервисами, которые читают данные из Kafka и записывают их в базу данных. Также была предложена нормализация данных и обогащение событий перед их отправкой в другие сервисы.
### Эталонное решение (AI)
Эталонное решение включает в себя использование Kafka для обработки событий, а также применение паттернов, таких как Outbox и Transactional Outbox, для обеспечения атомарности операций записи в базу данных и отправки событий в Kafka. Также важно учитывать обработку ошибок и ретраи для обеспечения надежности системы.

## Задача 87: Порядок событий в Kafka {#task-087-kafka-event-order}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
Обсудить, как гарантируется порядок событий в Kafka и при каких условиях он может быть нарушен. Также рассмотреть, как это влияет на архитектуру системы.
### Решение кандидата
Кандидат объяснил, что порядок событий в Kafka гарантируется на уровне партиций. Он также отметил, что порядок может быть нарушен при использовании нескольких консюмеров в одной группе, если они читают из разных партиций. Кандидат предложил использовать одну консюмер-группу для обеспечения порядка обработки событий.
### Эталонное решение (AI)
Эталонное решение включает в себя использование одной партиции для каждого типа события, чтобы гарантировать порядок, а также применение механизма контроля за порядком на уровне приложения, чтобы избежать дублирования и потери событий.

## Задача 88: Гарантия доставки сообщений {#task-088-go-kafka-message-delivery-guarantee}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
Обсудить, как обеспечить гарантию доставки сообщений в системе, использующей Kafka и базы данных. Рассмотреть возможные проблемы и решения.
### Решение кандидата
Кандидат предложил использовать паттерн Outbox для обеспечения гарантии доставки сообщений. Он объяснил, что сообщения должны быть записаны в Outbox в рамках одной транзакции с записью в базу данных, чтобы гарантировать, что они не потеряются. Также была предложена реализация механизма ретраев для обработки ошибок.
### Эталонное решение (AI)
Эталонное решение включает в себя использование Transactional Outbox, который позволяет записывать события в Outbox и отправлять их в Kafka в рамках одной транзакции. Это обеспечивает атомарность операций и гарантирует, что сообщения не будут потеряны при сбоях.

## Задача 89: Обогащение событий {#task-089-go-event-enrichment}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
Обсудить, как реализовать обогащение событий в системе, использующей Kafka и базы данных. Рассмотреть, какие данные необходимо добавлять и как это влияет на производительность.
### Решение кандидата
Кандидат предложил использовать дополнительные сервисы для обогащения событий перед их отправкой в Kafka. Он объяснил, что данные о сотрудниках и других сущностях могут быть получены из различных источников и добавлены к событиям. Также была обсуждена необходимость нормализации данных.
### Эталонное решение (AI)
Эталонное решение включает в себя использование микросервисов для обогащения событий, которые могут асинхронно получать данные из различных источников и добавлять их к событиям перед отправкой в Kafka. Это позволяет уменьшить нагрузку на основную систему и повысить производительность.

## Задача 90: Обработка ошибок и ретраи {#task-090-go-error-handling-retries}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
Обсудить, как обрабатывать ошибки и реализовать механизм ретраев в системе, использующей Kafka и базы данных. Рассмотреть, какие подходы можно использовать для обеспечения надежности.
### Решение кандидата
Кандидат предложил использовать экспоненциальные задержки для ретраев и механизм мониторинга для отслеживания состояния системы. Он также отметил, что важно учитывать, как часто происходят ошибки и как это влияет на производительность системы.
### Эталонное решение (AI)
Эталонное решение включает в себя использование паттерна Circuit Breaker для предотвращения перегрузки системы при частых ошибках, а также реализацию механизма ретраев с экспоненциальной задержкой для обработки временных сбоев. Это позволяет обеспечить надежность системы и избежать потери сообщений.

## Задача 91: Архитектура приложения с кэшем {#task-091-architecture-cache-application}
**Источник:** [Go Live Interview с Senior-разработчиком из Ozon](https://www.youtube.com/watch?v=Yt0M8-hfYYQ)

### Условие
Рассмотрите архитектуру приложения, которое обрабатывает запросы к базе данных с использованием кэша. Как вы будете организовывать взаимодействие с кэшем и базой данных?
### Решение кандидата
Кандидат предлагает использовать репозиторий для взаимодействия с базой данных и кэшем, чтобы избежать открытия соединения на каждый запрос. Он также упоминает о необходимости инвалидации кэша.
### Эталонное решение (AI)
Архитектура должна включать слой репозитория, который будет управлять соединениями с базой данных и кэшем. При каждом запросе сначала проверяется кэш, и если данные не найдены, выполняется запрос к базе данных. Важно также реализовать механизм инвалидации кэша для актуализации данных.

## Задача 92: Архитектура с очередью и мягкая резервация {#task-092-golang-architecture-queue-soft-reservation}
**Источник:** [Golang Тех собеседование В HFLabs на 300к](https://www.youtube.com/watch?v=30n5ashYGj8)

### Условие
Обсудить архитектуру системы, которая использует очередь сообщений для синхронизации данных между Redis и PostgreSQL, а также реализует мягкую резервацию.
### Решение кандидата
Кандидат описал, что использовал Redis для мягкой резервации, чтобы избежать дубликатов при бронировании. Также он упомянул, что очередь реализована через Kafka, которая синхронизирует данные между Redis и PostgreSQL.
### Эталонное решение (AI)
Для реализации такой архитектуры можно использовать паттерн CQRS (Command Query Responsibility Segregation), который разделяет операции записи и чтения. Использование Kafka позволяет обеспечить надежную доставку сообщений и масштабируемость системы.

## Задача 93: Чистая архитектура в Go {#task-093-go-architecture-clean-architecture}
**Источник:** [Golang Тех собеседование В HFLabs на 300к](https://www.youtube.com/watch?v=30n5ashYGj8)

### Условие
Обсудить, как реализована архитектура сервисов на Go, включая использование слоев и принципов чистой архитектуры.
### Решение кандидата
Кандидат объяснил, что архитектура сервисов в Go похожа на чистую архитектуру, где используются слои для отделения бизнес-логики от доступа к данным и внешним API. Он также упомянул, что придерживаются принципа единственной ответственности.
### Эталонное решение (AI)
Чистая архитектура подразумевает, что зависимости направлены внутрь, а внешние слои могут взаимодействовать с внутренними, но не наоборот. Это позволяет легко заменять компоненты и тестировать их независимо.

## Задача 94: Обработка конкурентного доступа к срезу {#task-094-go-concurrency-slice-access}
**Источник:** [Собеседуем Go-разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=s1Lo_RQx3xs)

### Условие
Представьте, что у вас есть срез, и несколько горутин пытаются одновременно записывать в него данные. Каковы будут последствия, и как вы можете избежать проблем с конкурентным доступом?
### Решение кандидата
Кандидат отметил, что стандартный срез в Go не является потокобезопасным, и предложил использовать мьютексы для синхронизации доступа к срезу.
### Эталонное решение (AI)
Для обеспечения потокобезопасности можно использовать мьютексы следующим образом:
```go
var mu sync.Mutex

func safeWrite(slice []int, index int, value int) {
    mu.Lock()
    defer mu.Unlock()
    slice[index] = value
}
```

## Задача 95: Сравнение среза и связного списка {#task-095-go-data-structure-slice-vs-linked-list}
**Источник:** [Собеседуем Go-разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=s1Lo_RQx3xs)

### Условие
Сравните операции вставки в срез и связный список. В каких случаях лучше использовать один из этих типов данных?
### Решение кандидата
Кандидат объяснил, что вставка в начало связного списка имеет сложность O(1), в то время как вставка в срез требует O(n) из-за необходимости сдвига элементов. Однако, если нужно часто добавлять элементы в конец, срез может быть более эффективным.
### Эталонное решение (AI)
При выборе между срезом и связным списком следует учитывать:
- Для частых вставок и удалений в начале или середине лучше использовать связный список.
- Для быстрого доступа по индексу и вставок в конец лучше использовать срез.

## Задача 96: Микросервисы и паттерны проектирования {#task-096-java-microservices-design-patterns}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Обсудите паттерны проектирования, используемые в микросервисах, такие как Saga, Circuit Breaker, Service Discovery, App Gateway, и Sharding.
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 97: Системный дизайн {#task-097-java-system-design}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Обсудите, как масштабировать систему. Какие подходы к репликации, шардированию и кэшированию вы знаете?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 98: Проектирование схемы базы данных для библиотеки {#task-098-golang-database-library-schema}
**Источник:** [РЕАЛЬНОЕ собеседование Senior Golang Backend на 6000$ ｜ (+ Live-coding)](https://www.youtube.com/watch?v=AKURknsxTwU)

### Условие
Необходимо спроектировать модель библиотеки с тремя сущностями: автор, книга и читатель. Нужно создать схему базы данных, которая будет учитывать, кто какую книгу взял.

### Решение кандидата
Кандидат предложил создать таблицы для авторов, книг и читателей, а также учесть связи между ними. Он отметил, что нужно создать отдельную таблицу для связи книги и автора, чтобы учесть возможность наличия нескольких авторов у одной книги.

### Эталонное решение (AI)
Для проектирования схемы базы данных можно использовать следующую структуру:
1. Таблица Authors (id, name)
2. Таблица Books (id, title, author_id)
3. Таблица Readers (id, name)
4. Таблица BookReaders (book_id, reader_id, date_borrowed)

Таким образом, мы можем отслеживать, какие книги находятся у каких читателей, а также поддерживать связь многие-ко-многим между книгами и авторами.

## Задача 99: Паттерн Saga {#task-099-java-pattern-saga}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Как разбить сложную, длительную транзакцию на более мелкие с использованием паттерна Saga?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 100: Circuit Breaker {#task-100-java-design-pattern-circuit-breaker}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Объясните, как работает паттерн Circuit Breaker и в каких случаях его следует использовать.
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 101: Микросервисы {#task-101-java-microservices-design-patterns}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Обсудите основные паттерны проектирования, используемые в микросервисной архитектуре.
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 102: Устранение утечек памяти в Go {#task-102-go-memory-leak}
**Источник:** [CОБЕСЕДОВАНИЕ В Т-БАНК НА ГОФЕРА ⧸ ИНТЕРВЬЮ СТАЖЁРА](https://www.youtube.com/watch?v=WclJtjQXptU)

### Условие
Сервис, использующий кэш, упал через несколько дней работы. Необходимо выяснить причину падения и предложить решение проблемы с утечкой памяти.
### Решение кандидата
Кандидат предположил, что проблема может быть связана с кэшом, который переполняется, и предложил реализовать функцию очистки кэша, которая будет удалять устаревшие данные.
### Эталонное решение (AI)
Эталонное решение должно включать в себя реализацию функции очистки кэша, которая будет проверять время создания каждого элемента и удалять те, которые старше заданного порога. Также стоит рассмотреть возможность использования мьютексов для синхронизации доступа к кэшу.

## Задача 103: Обработка событий в системе turnstiles {#task-103-go-event-processing-turnstiles}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
В системе обработки событий от турникетов необходимо гарантировать доставку и порядок обработки событий. Система должна обрабатывать события, поступающие от турникетов, и записывать их в базу данных, а затем передавать в Kafka для дальнейшей обработки другими сервисами.
### Решение кандидата
Кандидат предложил использовать Kafka для гарантии доставки событий и поддержания порядка их обработки. Он объяснил, что порядок событий может быть нарушен, если события обрабатываются несколькими экземплярами сервиса, и предложил использовать consumer group для управления порядком обработки.
### Эталонное решение (AI)
Для решения задачи можно использовать подход с использованием Kafka, где события группируются по ключу (например, ID сотрудника), что позволяет гарантировать порядок обработки событий внутри одной партиции. Также важно реализовать механизм обработки ошибок и повторных попыток при сбоях, чтобы избежать потери данных.

## Задача 104: Гарантии доставки сообщений {#task-104-go-kafka-message-delivery-guarantees}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
В системе, использующей Kafka для обработки событий, необходимо обеспечить гарантии доставки сообщений, даже в случае сбоев в базе данных или сети. Как можно реализовать такие гарантии?
### Решение кандидата
Кандидат предложил использовать паттерн Outbox, где события сначала записываются в Outbox таблицу, а затем асинхронно отправляются в Kafka. Это позволяет гарантировать, что события не будут потеряны, даже если произойдет сбой в процессе отправки.
### Эталонное решение (AI)
Для обеспечения гарантии доставки сообщений можно использовать транзакции, которые записывают события в базу данных и Outbox в рамках одной транзакции. Затем отдельный процесс или worker будет считывать события из Outbox и отправлять их в Kafka, обеспечивая тем самым надежность и согласованность данных.

## Задача 105: Обработка дубликатов сообщений {#task-105-go-kafka-duplicate-messages}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
В системе, использующей Kafka, необходимо обрабатывать дубликаты сообщений, которые могут возникать из-за повторной отправки событий. Как можно решить эту проблему?
### Решение кандидата
Кандидат предложил использовать уникальные идентификаторы для каждого события и проверять их перед записью в базу данных. Если событие с таким идентификатором уже существует, оно не должно обрабатываться повторно.
### Эталонное решение (AI)
Для обработки дубликатов можно использовать механизм проверки уникальности на уровне базы данных, например, с помощью уникальных индексов. Также можно реализовать логику на уровне приложения, которая будет отслеживать уже обработанные события и игнорировать дубликаты.

## Задача 106: Обработка ошибок и повторные попытки {#task-106-go-error-handling-retries}
**Источник:** [Открытый Go-собес с Senior Backend Engineer](https://www.youtube.com/watch?v=5wPVcB2VhNM)

### Условие
В системе, использующей Kafka и базу данных, необходимо реализовать обработку ошибок и повторные попытки при сбоях. Как можно организовать эту логику?
### Решение кандидата
Кандидат предложил использовать механизм повторных попыток с экспоненциальной задержкой для обработки сообщений, которые не удалось обработать из-за ошибок. Он также упомянул о паттерне Circuit Breaker для предотвращения перегрузки системы в случае частых ошибок.
### Эталонное решение (AI)
Для реализации обработки ошибок можно использовать библиотеку, которая поддерживает повторные попытки с экспоненциальной задержкой. Также стоит реализовать Circuit Breaker, который будет временно блокировать обработку сообщений, если количество ошибок превышает заданный порог.

## Задача 107: Интерфейсы в Go {#task-107-go-interface-implementation}
**Источник:** [Golang Собеседование в OZON - Технический скрининг на 400к](https://www.youtube.com/watch?v=TXh6ociaJJ4)

### Условие
Что такое интерфейсы в Go и как они работают?
### Решение кандидата
Кандидат объясняет, что интерфейсы в Go основаны на утиной типизации и описывает, как структуры реализуют интерфейсы без явного указания.
### Эталонное решение (AI)
Интерфейсы в Go позволяют создавать контракты, которые структуры должны реализовать, и работают на основе утиной типизации, что упрощает реализацию.

## Задача 108: Проектирование системы Twitter {#task-108-system-design-twitter}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Проектируем систему Twitter с основными функциональными требованиями: публикация твитов, формирование ленты на основе подписок и публикаций пользователей. Необходимо учесть ограничения на количество символов в твите, возможность добавления медиафайлов, а также требования к производительности и доступности.
### Решение кандидата
Кандидат предложил реализовать систему с использованием реляционных и NoSQL баз данных, кэширования для ускорения доступа к ленте, а также асинхронной обработки событий для обновления ленты пользователей. Обсуждались также ограничения на количество подписчиков и необходимость обработки "проблемы знаменитостей".
### Эталонное решение (AI)
Эталонное решение включает в себя использование микросервисной архитектуры, где каждый сервис отвечает за свою часть функциональности (например, сервис твитов, сервис подписок и т.д.). Также рекомендуется использовать кэширование для ускорения доступа к данным и асинхронные очереди для обработки событий, что позволит обеспечить масштабируемость и отказоустойчивость системы.

## Задача 109: Обработка медиафайлов в твитах {#task-109-mediafile-twitter-processing}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как организовать загрузку и хранение медиафайлов (изображений) в системе, чтобы обеспечить эффективное использование ресурсов и минимизировать задержки при публикации твитов.
### Решение кандидата
Кандидат предложил реализовать двухступенчатую загрузку медиафайлов: сначала загружать изображение в облачное хранилище (например, S3) и получать его идентификатор, а затем использовать этот идентификатор при создании твита. Также обсуждались варианты временного хранения изображений, которые не были опубликованы.
### Эталонное решение (AI)
Эталонное решение включает в себя использование облачного хранилища для медиафайлов с возможностью кэширования и оптимизации загрузки. Рекомендуется реализовать механизм очистки временных файлов, которые не были использованы, а также возможность повторного использования уже загруженных изображений для ускорения процесса.

## Задача 110: Кэширование ленты пользователей {#task-110-system-design-cache-users-feed}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как организовать кэширование ленты пользователей для обеспечения быстрой доставки твитов и минимизации нагрузки на базу данных.
### Решение кандидата
Кандидат предложил использовать Redis для кэширования ленты пользователей, где ключом будет идентификатор пользователя, а значением - массив данных о твитах. Обсуждалась необходимость обновления кэша при создании новых твитов.
### Эталонное решение (AI)
Эталонное решение включает в себя использование Redis для кэширования, а также реализацию механизма асинхронного обновления кэша при создании новых твитов. Рекомендуется использовать подходы, такие как "инвалидация кэша" для обновления данных в случае публикации твитов знаменитостями.

## Задача 111: Масштабируемость и отказоустойчивость системы {#task-111-system-design-scalability-reliability}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Как обеспечить масштабируемость и отказоустойчивость системы при увеличении числа пользователей и нагрузки на сервисы.
### Решение кандидата
Кандидат предложил использовать микросервисную архитектуру с возможностью горизонтального масштабирования, а также репликацию баз данных и очередей сообщений для обеспечения отказоустойчивости. Обсуждалась необходимость использования CDN для оптимизации загрузки медиафайлов.
### Эталонное решение (AI)
Эталонное решение включает в себя использование микросервисов, которые могут быть масштабированы независимо, а также реализацию шардирования и репликации баз данных. Рекомендуется интеграция CDN для оптимизации доставки медиафайлов и уменьшения нагрузки на основной сервер.

## Задача 112: Вопрос: Разница между HTTP и gRPC {#task-112-go-protocol-http-vs-grpc}
**Источник:** [Мок-собеседование Middle Go-разработчика： что спрашивают в Avito и Ozon](https://www.youtube.com/watch?v=ArpOzrG0gCM)

### Условие
Объясните разницу между HTTP и gRPC. В каких случаях лучше использовать каждый из этих протоколов?
### Решение кандидата
Кандидат объяснил, что gRPC использует HTTP/2 и обеспечивает более быструю передачу данных благодаря бинарному формату. Он также отметил, что gRPC часто используется для внутреннего общения между сервисами, в то время как HTTP чаще применяется для внешних запросов.
### Эталонное решение (AI)
HTTP - это текстовый протокол, который работает на основе запросов и ответов, в то время как gRPC использует бинарный формат и поддерживает стриминг. gRPC лучше подходит для высокопроизводительных систем, где важна скорость передачи данных и строгая типизация, в то время как HTTP более универсален и проще в использовании для внешних API.

## Задача 113: Вопрос: Масштабирование баз данных {#task-113-go-database-scaling}
**Источник:** [Мок-собеседование Middle Go-разработчика： что спрашивают в Avito и Ozon](https://www.youtube.com/watch?v=ArpOzrG0gCM)

### Условие
Объясните разницу между вертикальным и горизонтальным масштабированием баз данных.
### Решение кандидата
Кандидат объяснил, что вертикальное масштабирование включает в себя увеличение ресурсов одного сервера, тогда как горизонтальное масштабирование подразумевает добавление новых серверов для распределения нагрузки.
### Эталонное решение (AI)
Вертикальное масштабирование - это увеличение ресурсов (CPU, RAM) на одном сервере, что имеет свои ограничения. Горизонтальное масштабирование - это добавление новых серверов для распределения нагрузки и повышения доступности, что позволяет системе расти более гибко.

## Задача 114: Отличия грутин от потоков операционной системы {#task-114-go-concurrency-goroutines-vs-threads}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Чем отличается грутина от потоков операционной системы? Назовите три ключевых отличия.
### Решение кандидата
Первое - размер стека. Стек грутины при старте 2 кб, а у потока операционной системы 8 Мб. Второе - модель MН. Третье - переключение.
### Эталонное решение (AI)
1. Размер стека: грутины имеют меньший размер стека по сравнению с потоками ОС.
2. Модель MН: грутины могут работать на нескольких потоках ОС.
3. Переключение: грутины переключаются в Userpace без системного вызова.

## Задача 115: Работа с каналами в Go {#task-115-go-channel-difference}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Объясните, чем отличается буферизированный канал от небуферизированного и как работает нил-канал.
### Решение кандидата
Небуферизированный канал блокирует отправителя, пока получатель не прочитает данные. Буферизированный канал блокирует, когда буфер полон. Нил-канал всегда блокируется, даже когда пишем или читаем.
### Эталонное решение (AI)
1. Небуферизированный канал: блокирует отправителя до чтения.
2. Буферизированный канал: блокирует при заполнении буфера.
3. Нил-канал: блокирует в любом случае.

## Задача 116: Отличия Mтек и РВ Mutкса {#task-116-go-concurrency-differences-mtek-rw-mutks}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Чем отличается Mтек от РВ Mutкса?
### Решение кандидата
Mтек - это эксклюзивная блокировка, а РВ Mutкса разделяет читателей и писателей.
### Эталонное решение (AI)
1. Mтек: эксклюзивная блокировка, один захватывает ресурс.
2. РВ Mutкса: позволяет нескольким читателям одновременно, блокирует при записи.

## Задача 117: Устройство мапы в Go {#task-117-go-data-structure-map}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Как устроена мапа в Go?
### Решение кандидата
Мапа - это ТХш-таблица, внутри которой массив бакетов. Каждый бакет хранит до восьми пар ключ-значение. При превышении загрузки мапа увеличивается в два раза.
### Эталонное решение (AI)
1. Мапа: хэш-таблица с массивом бакетов.
2. Увеличение: происходит при превышении средней загрузки.

## Задача 118: Склеивание строк в Go {#task-118-go-string-concatenation}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Как правильно склеивать строки в Go?
### Решение кандидата
Если использовать оператор + в цикле, сложность будет O(N²). Лучше использовать string builder для линейной сложности.
### Эталонное решение (AI)
1. Использовать string builder для оптимизации.
2. Заранее задавать размер буфера для минимизации аллокаций.

## Задача 119: Дефер в Go {#task-119-go-concept-defer}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Что такое дефер и в каком порядке выполняется?
### Решение кандидата
Дефер откладывает вызов функции до выхода из текущей функции, порядок выполнения - LIFO.
### Эталонное решение (AI)
1. Дефер: откладывает выполнение функции.
2. Порядок: LIFO, последний вызов выполняется первым.

## Задача 120: Отличия слайса от массива {#task-120-go-difference-slice-array}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Чем отличается слайс от массива в Go?
### Решение кандидата
Массив фиксированного размера, слайс - это обёртка над массивом, динамически изменяемая.
### Эталонное решение (AI)
1. Массив: фиксированный размер, копируется при передаче.
2. Слайс: динамический, ссылается на массив.

## Задача 121: Работа планировщика Go и модель GMP {#task-121-go-scheduler-gmp}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Как работает планировщик Go и модель GMP?
### Решение кандидата
G - грутина, M - машина, P - логический процессор. M выполняет код на процессоре, P имеет свою очередь грутин.
### Эталонное решение (AI)
1. G: задача, которую нужно выполнить.
2. M: поток ОС, выполняющий код.
3. P: логический процессор, количество соответствует количеству ядер.

## Задача 122: Структура HTTP-запроса и ответа {#task-122-go-http-structure}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Из чего состоит HTTP-запрос и ответ?
### Решение кандидата
HTTP-запрос состоит из метода, пути, заголовков и тела. Ответ состоит из статус-кода, заголовков и тела.
### Эталонное решение (AI)
1. Запрос: метод, путь, заголовки, тело.
2. Ответ: статус-код, заголовки, тело.

## Задача 123: Устройство интерфейса в Go {#task-123-go-interface-structure}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Как устроен интерфейс в Go?
### Решение кандидата
Интерфейс - это набор методов, имплементация неявная. Пустой интерфейс принимает любой тип данных.
### Эталонное решение (AI)
1. Интерфейс: набор методов с неявной имплементацией.
2. Пустой интерфейс: принимает любой тип, реализуется автоматически.

## Задача 124: Трассировка микросервисов {#task-124-go-microservices-tracing}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Как организовать трассировку в системе с 1000 микросервисов?
### Решение кандидата
Каждый запрос получает ID, который передаётся через заголовки. Каждый сервис создаёт спан с временем начала и конца.
### Эталонное решение (AI)
1. Трассировка: использование уникального ID для каждого запроса.
2. Спаны: временные отрезки, фиксирующие время обработки запроса.

## Задача 125: Вопрос о архитектуре FSD {#task-125-frontend-architecture-fsd-question}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Как вы выбирали архитектуру проекта? Какие слои FSD вы использовали?
### Решение кандидата
Кандидат описал, что использовал классическую модульную архитектуру без FSD, упомянул основные слои FSD: страницы, виджеты, функции, приложение, общие и сущности.
### Эталонное решение (AI)
При выборе архитектуры важно учитывать требования проекта и команду. FSD может помочь в организации кода, но требует строгого соблюдения стиля и структуры.

## Задача 126: Вопрос о микрофронтендах {#task-126-javascript-frontend-microfrontends}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Почему вы использовали микрофронтенды в вашем проекте? Какие проблемы возникали при интеграции?
### Решение кандидата
Кандидат объяснил, что использовал микрофронтенды для разделения больших приложений на более мелкие, управляемые командами. Упомянул проблемы с маршрутизацией и передачей состояния между микрофронтами.
### Эталонное решение (AI)
Микрофронтенды позволяют командам работать независимо, но могут вызвать сложности с интеграцией и синхронизацией версий. Важно иметь общую базу для передачи состояния.

## Задача 127: Вопрос о CORS {#task-127-javascript-web-cors-question}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Что такое CORS и как вы его настраивали в своем проекте?
### Решение кандидата
Кандидат объяснил, что CORS - это политика браузера, предотвращающая доступ к ресурсам с другого домена. Он настраивал CORS через заголовки на сервере и использовал прокси для локальной разработки.
### Эталонное решение (AI)
CORS позволяет контролировать доступ к ресурсам. Настройка включает добавление заголовков Access-Control-Allow-Origin и других на сервере для разрешения запросов с разных доменов.

## Задача 128: Вопрос о CSP {#task-128-frontend-security-csp}
**Источник:** [Реальное собеседование на Middle⧸Senior Frontend-разработчика со сложными вопросами! Собес с ЗП 300К](https://www.youtube.com/watch?v=ijprxQH2tMo)

### Условие
Что такое CSP и как вы его настраивали в своем проекте?
### Решение кандидата
Кандидат описал CSP как политику безопасности браузера, которая ограничивает загрузку ресурсов. Он упомянул, что обычно настройки CSP выполняются на сервере.
### Эталонное решение (AI)
CSP помогает предотвратить XSS-атаки, ограничивая источники загрузки скриптов и стилей. Настройка включает добавление заголовка Content-Security-Policy на сервере.

## Задача 129: Обсуждение GIL в Python {#task-129-python-discussion-gil}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Обсудить, как GIL (Global Interpreter Lock) влияет на многопоточность в Python и как это соотносится с производительностью приложений.
### Решение кандидата
Кандидат объясняет, что GIL ограничивает выполнение потоков в Python, позволяя только одному потоку выполнять байт-код в любой момент времени. Это приводит к проблемам с производительностью в CPU-bound задачах, но позволяет эффективно обрабатывать I/O-bound операции.
### Эталонное решение (AI)
GIL был введен для упрощения управления памятью и предотвращения проблем с синхронизацией данных. Однако, в многопоточных приложениях это может привести к снижению производительности, особенно в задачах, требующих интенсивных вычислений. Для обхода этого ограничения разработчики могут использовать многопроцессорные подходы или другие языки программирования без GIL.

## Задача 130: Обмен данными между процессами {#task-130-python-interprocess-communication-data-exchange}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Как происходит обмен данными между процессами в операционной системе и какие механизмы для этого используются?
### Решение кандидата
Кандидат объясняет, что обмен данными между процессами чаще всего осуществляется через очереди и механизмы межпроцессного взаимодействия (IPC), такие как сокеты и файлы.
### Эталонное решение (AI)
Обмен данными между процессами может происходить через различные механизмы IPC, включая очереди сообщений, сокеты, разделяемую память и каналы. Каждый из этих методов имеет свои преимущества и недостатки в зависимости от требований к производительности и сложности реализации.

## Задача 131: Контекстный переключатель {#task-131-python-interview-context-switcher}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Обсудить, что такое контекстный переключатель и почему он считается дорогой операцией.
### Решение кандидата
Кандидат объясняет, что контекстный переключатель включает в себя сохранение состояния текущего потока и загрузку состояния нового потока, что требует времени и ресурсов.
### Эталонное решение (AI)
Контекстный переключатель - это процесс, при котором операционная система сохраняет состояние текущего потока и загружает состояние другого потока. Это считается дорогой операцией из-за необходимости взаимодействия с памятью и кэшами, а также из-за времени, необходимого для выполнения этих операций.

## Задача 132: Проектирование схемы базы данных для библиотеки {#task-132-golang-database-library-schema}
**Источник:** [РЕАЛЬНОЕ собеседование Senior Golang Backend на 6000$ ｜ (+ Live-coding)](https://www.youtube.com/watch?v=AKURknsxTwU)

### Условие
Необходимо спроектировать схему базы данных для библиотеки, включающую три сущности: автор, книга и читатель. Опишите, как они будут связаны между собой.
### Решение кандидата
Кандидат предложил создать таблицы для авторов, книг и читателей, а также таблицу для учета того, кто взял какую книгу. Он отметил, что необходимо учитывать связи между этими сущностями и обеспечить уникальность записей.
### Эталонное решение (AI)
Схема базы данных может включать три таблицы: Authors, Books и Readers. Для связи между книгами и читателями можно создать таблицу BookLoans, которая будет содержать поля BookID и ReaderID, чтобы отслеживать, какая книга находится у какого читателя. Также можно создать таблицу BookAuthors для реализации связи многие-ко-многим между книгами и авторами.