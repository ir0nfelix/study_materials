# Собеседования по Базам Данных (SQL)

## Задача 1: Сложный JOIN с фильтрацией по дате и условиям (Ozon) {#task-001-sql-join-date-filter}
**Видео:** [Golang Interview at OZON - Technical Screening for 400k](https://www.youtube.com/watch?v=TXh6ociaJJ4)
**Категория:** SQL
**Популярная:** 1

### Условие
Даны таблицы покупок (`Purchases`) и банов пользователей (`Banlist`). Нужно написать SQL-запрос, который выведет уникальные комбинации пользователя (`user_id`) и ID товара (`sku`) для всех покупок, но **только те, которые совершены пользователями до того, как их забанили** (или если они вообще не были забанены). Результат отсортировать сначала по имени пользователя, потом по SKU.
Дополнительный вопрос от ментора: Чем отличается `LEFT JOIN` от `INNER JOIN` (обычного `JOIN`) и почему в данной задаче используется именно `LEFT JOIN`?

### Решение кандидата
Кандидат использует `SELECT DISTINCT user_id, sku` для получения уникальных комбинаций. Для соединения таблиц он применяет `LEFT JOIN` таблицы `Banlist`, объясняя это тем, что пользователь может вообще не присутствовать в таблице банов (тогда поля будут `NULL`).
В `WHERE` добавляется условие: либо пользователь не в банлисте (`Banlist.id IS NULL`), либо дата покупки меньше даты бана.

Кандидат отлично объясняет разницу между джоинами: `JOIN` (INNER) работает как пересечение множеств, а `LEFT JOIN` берет все записи из левой таблицы и подставляет `NULL`, если в правой таблице нет совпадений.

### Эталонное решение (AI)
**Запрос:**
```sql
SELECT DISTINCT p.user_id, p.sku
FROM Purchases p
LEFT JOIN Banlist b ON p.user_id = b.user_id
WHERE b.user_id IS NULL OR p.purchase_date < b.ban_date
ORDER BY p.user_name, p.sku;
```
**Почему `LEFT JOIN`:** 
`INNER JOIN` отсекает строки из левой таблицы, если для них нет совпадений в правой. Если бы мы использовали `INNER JOIN`, запрос вернул бы покупки **только забаненных** пользователей. `LEFT JOIN` сохраняет все покупки добропорядочных пользователей (проставляя `NULL` в колонки банлиста), что позволяет нам легко отфильтровать их через `b.user_id IS NULL`.


## Задача 2: Хранение аналитической статистики: OLTP счетчики vs OLAP append-only {#task-002-dotnet-architecture-oltp-vs-olap}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
В методе репозитория сервиса выполняется инкремент продуктивности/статистики действий администратора:
```sql
UPDATE AdminStats SET Count = Count + 1 WHERE AdminId = @adminId
```
Какие архитектурные и производительностные проблемы несет такой подход в высоконагруженных системах, и как правильно спроектировать подсистему сбора продуктивности/статистики?

### Решение кандидата
1. Метод инкрементирует значение напрямую в реляционной БД (MS SQL/PostgreSQL), создавая операцию записи с блокировкой строки по `AdminId`.
2. При высокой нагрузке на запись операции `Count = Count + 1` вызывают конкуренцию за строку (row lock contention), снижая пропускную способность сервиса.
3. Реляционные БД не оптимизированы для непрерывных частых апдейтов агрегатов.
4. Более оптимальный подход: отправка событий в брокер (Apache Kafka), потребление аналитическим сервисом батчами и сохранение в OLAP-хранилище (например, ClickHouse) методом append-only (только вставка новых событий). Подсчет статистики производится агрегацией (sum/count) на стороне аналитики или специализированными движками (AggregatingMergeTree в ClickHouse).

### Эталонное решение (AI)
Прямой `UPDATE` счетчиков в OLTP БД — классический антипаттерн в распределенных системах:
1. **Проблемы прямого инкремента:**
   - **Блокировки и дедлоки:** Несколько параллельных транзакций с одинаковым `AdminId` выстраиваются в очередь на эксклюзивную блокировку (`X-lock`). Возникает деградация latency.
   - **Write Amplification (PostgreSQL HOT / MVCC):** Каждый апдейт создает новую версию строки и раздувает таблицу/индексы (bloat).
   - **Нарушение Single Responsibility Principle:** Транзакционный микросервис берет на себя несвойственную нагрузку OLAP-аналитики.

2. **Целевая архитектура:**
   - В основном бизнес-потоке публикуется легковесное событие (через Outbox $\to$ Kafka/RabbitMQ):
     ```json
     { "eventId": "uuid", "type": "AdminActionExecuted", "adminId": 123, "timestamp": 1711929600 }
     ```
   - Сервис сбора статистики вычитывает топик Kafka пачками (Batch Consumer).
   - Данные записываются append-only в аналитическую СУБД (ClickHouse):
     ```sql
     CREATE TABLE admin_actions (
         admin_id UInt64,
         action_time DateTime,
         action_type LowCardinality(String)
     ) ENGINE = MergeTree()
     ORDER BY (admin_id, action_time);
     ```
   - Если требуется мгновенное отображение счетчиков с минимальной задержкой в админ-панели, можно использовать Redis (`INCRBY admin:{id}:stats 1`) в качестве промежуточного кэша с периодическим сбросом в постоянное хранилище.

## Задача 3: Вопрос: Классификации и функции баз данных {#task-003-database-classification-functions}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Какие классификации БД знаешь, по каким признакам, примеры, какие функции должна выполнять БД.
### Решение кандидата
Кандидат назвал реляционные и нереляционные. Сказал, что реляционные для целостности и сложных запросов, нереляционные для скорости, хранения JSON-документов. Функции: хранение, чтение, обновление, удаление, поиск, CRUD.
### Эталонное решение (AI)
Классификации: relational, например PostgreSQL или MySQL; NoSQL document, например MongoDB; key-value, например Redis; column, например Cassandra; graph, например Neo4j; NewSQL. Признаки: модель данных, ACID, schema, scaling, consistency. Функции: storage, query, update, delete, transactions, integrity, security, backup и restore, replication, indexing.

## Задача 4: SQL-запросы по зарплатам и возрасту {#task-004-sql-query-salary-age}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
По таблице employees написать запросы: сортировка по зарплате по убыванию, сумма зарплат, максимальная зарплата внутри каждой группы по возрасту, имя и возраст сотрудников 27 и старше, количество разных зарплат.
### Решение кандидата
Кандидат написал: SELECT * FROM employes ORDER BY salary DESC; SELECT SUM(salary) AS total_salary FROM employes; SELECT MAX(salary) FROM employes GROUP BY age; SELECT name, age FROM employes WHERE age >= 27; COUNT(DISTINCT salary).
### Эталонное решение (AI)
SELECT * FROM employees ORDER BY salary DESC; SELECT SUM(salary) AS total_salary FROM employees; SELECT age, MAX(salary) AS max_salary FROM employees GROUP BY age; SELECT name, age FROM employees WHERE age >= 27; SELECT COUNT(DISTINCT salary) AS distinct_salaries FROM employees.

## Задача 5: Вопрос: JOIN и виды соединений {#task-005-sql-join-types}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Что такое JOIN, какие виды знаешь и применял.
### Решение кандидата
Кандидат сказал, что JOIN объединяет две таблицы по параметру, например users и orders по user_id. Назвал inner join, left join, right join, on.
### Эталонное решение (AI)
INNER JOIN — только совпадения; LEFT JOIN — все из левой и совпадения из правой; RIGHT JOIN — все из правой; FULL OUTER JOIN — все из обеих; CROSS JOIN — декартово; SELF JOIN — таблица с собой. Условия ON или USING, NULLs для несуществующих строк.

## Задача 6: SQL-запросы с таблицей offices {#task-006-sql-query-offices-employees}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Есть таблицы employees и offices. Вывести имена сотрудников и дату прикрепления из филиала Москва 1, где дата открепления не заполнена. Также вывести сотрудников, которые нигде не прикреплены к филиалу.
### Решение кандидата
Кандидат начал делать JOIN offices и employees по employee_id, фильтровать по Москва 1 и end_date IS NULL. Для не прикрепленных предложил проверить наличие ID, но понял, что нужно лучше через LEFT JOIN или NOT EXISTS.
### Эталонное решение (AI)
SELECT e.name, o.start_date FROM offices o JOIN employees e ON e.id = o.employee_id WHERE o.office_name = 'Москва 1' AND o.end_date IS NULL; SELECT e.name FROM employees e LEFT JOIN offices o ON e.id = o.employee_id WHERE o.id IS NULL; или NOT EXISTS (SELECT 1 FROM offices o WHERE o.employee_id = e.id).

## Задача 7: SQL: Авторы с суммарной выручкой более 500 000 рублей {#task-007-sql-authors-revenue-over-500k}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Даны таблицы `authors`, `books`, `books_authors` (many-to-many). Нужно выбрать авторов, у которых суммарная стоимость всех проданных книг больше 500 000 рублей. В результате должны быть поля автора и суммарная выручка.
### Решение кандидата
Кандидат сначала соединил таблицы `authors` -> `books_authors` -> `books`, попытался отфильтровать строки условием `WHERE books.cost * books.sold > 500000` и затем сгруппировал по автору. Ошибка: условие применялось к каждой книге, а не к суммарной выручке автора. После исправления перенёс проверку в `HAVING SUM(books.cost * books.sold) > 500000`.
### Эталонное решение (AI)
```sql
SELECT
  a.author_id,
  a.author_name,
  SUM(b.cost * b.sold) AS total_revenue
FROM authors a
JOIN books_authors ba ON ba.author_id = a.author_id
JOIN books b ON b.book_id = ba.book_id
GROUP BY a.author_id, a.author_name
HAVING SUM(b.cost * b.sold) > 500000;
```
Если нужно только список авторов без выручки, можно убрать `SUM` из `SELECT`, но `HAVING` остаётся.

## Задача 8: SQL: Количество сотрудников по категориям зарплаты {#task-008-sql-employee-salary-count}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Дана таблица `employees` с полями `employee_id` и `income`. Нужно посчитать количество сотрудников в каждой категории: низкая зарплата < 20000, средняя от 20000 до 50000, высокая > 50000. В итоговой таблице должны присутствовать все категории, если сотрудников нет — 0. Отсортировать по убыванию количества.
### Решение кандидата
Кандидат сделал три отдельных запроса с `COUNT(*)` и литеральным названием категории, объединил их через `UNION ALL` и отсортировал по `count` по убыванию. Для средней категории использовал `BETWEEN 20000 AND 50000`, что эквивалентно `>= 20000 AND <= 50000`.
### Эталонное решение (AI)
```sql
SELECT 'Низкая зарплата' AS category, COUNT(*) AS cnt
FROM employees
WHERE income < 20000
UNION ALL
SELECT 'Средняя зарплата', COUNT(*)
FROM employees
WHERE income BETWEEN 20000 AND 50000
UNION ALL
SELECT 'Высокая зарплата', COUNT(*)
FROM employees
WHERE income > 50000
ORDER BY cnt DESC;
```
Альтернатива через `CASE WHEN` и `GROUP BY` требует гарантировать наличие всех категорий, например через `CROSS JOIN` со справочником категорий.

## Задача 9: SQL: Имена пилотов старше 45 лет, летавших на пассажирских самолётах вместимостью более 30 {#task-009-sql-query-pilots-over-45-passenger-aircraft}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Даны таблицы `pilots`, `aircraft`/`planes`, `flights`. Нужно вывести имена пилотов старше 45 лет, которые выполняли полёты на пассажирских самолётах вместимостью более 30 человек. В таблице `flights` есть `first_pilot_id` и `second_pilot_id`, поэтому пилот может быть связан с рейсом по любому из двух полей. Результат — уникальные имена.
### Решение кандидата
Кандидат соединил `pilots` с `flights` по условию `ON f.first_pilot_id = p.id OR f.second_pilot_id = p.id`, затем с таблицей самолётов по `plane_id`. Добавил условия `p.age > 45`, `capacity > 30` и признак пассажирского самолёта. Чтобы избежать дублей из-за двух пилотов в одном рейсе, использовал `DISTINCT`.
### Эталонное решение (AI)
```sql
SELECT DISTINCT p.name
FROM pilots p
JOIN flights f
  ON f.first_pilot_id = p.id
  OR f.second_pilot_id = p.id
JOIN aircraft a ON a.id = f.aircraft_id
WHERE p.age > 45
  AND a.capacity > 30
  AND a.is_passenger = TRUE;
```
Если признак пассажирского самолёта хранится как `cargo_flag = 0`, условие можно заменить на `a.cargo_flag = 0`. Альтернатива — `UNION` двух `JOIN` по первому и второму пилоту.

## Задача 10: SQL: Средний возраст клиентов, купивших Smart Watch в 2024 году {#task-010-sql-query-average-age-smart-watch-2024}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Даны таблицы `customers`, `purchases`, `products` и, возможно, `product_categories`. Нужно найти средний возраст клиентов, которые купили товар `Smart Watch` в 2024 году. Важно усреднять по уникальным клиентам, а не по покупкам.
### Решение кандидата
Кандидат сначала сделал `AVG(c.age)` по `customers`, `purchases` и `products` с условием `product.name = 'Smart Watch'` и годом 2024. Ошибка: если клиент сделал несколько таких покупок, его возраст учитывался несколько раз. Затем кандидат вынес уникальных клиентов в подзапрос/CTE: `SELECT DISTINCT customer_key, age ...` и посчитал `AVG(age)` по этой выборке. В финале упростил запрос, убрав лишний `JOIN` к `customers` и используя `IN` по `customer_key`.
### Эталонное решение (AI)
```sql
WITH smart_watch_customers AS (
  SELECT DISTINCT c.customer_key, c.age
  FROM customers c
  JOIN purchases p ON p.customer_key = c.customer_key
  JOIN products pr ON pr.product_key = p.product_key
  WHERE pr.name = 'Smart Watch'
    AND EXTRACT(YEAR FROM p.purchase_date) = 2024
)
SELECT AVG(age) AS average_age
FROM smart_watch_customers;
```
Более компактный вариант:
```sql
SELECT AVG(c.age) AS average_age
FROM customers c
WHERE c.customer_key IN (
  SELECT p.customer_key
  FROM purchases p
  JOIN products pr ON pr.product_key = p.product_key
  WHERE pr.name = 'Smart Watch'
    AND EXTRACT(YEAR FROM p.purchase_date) = 2024
);
```
Таблица `product_categories` не нужна, если имя товара уже указано в `products`.

## Задача 11: PostgreSQL JSON vs JSONB and use cases {#task-011-postgresql-json-jsonb-use-cases}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Какие специальные типы в PostgreSQL, чем JSONB отличается от JSON, можно ли делать запросы и индексы, для чего хранить JSONB.
### Решение кандидата
Кандидат говорит, что использовал JSONB для хранения гибких контрактов ФНС, которые менялись несовместимо. Полагает, что JSONB хранит данные в бинарном виде, по нему можно делать запросы и индексы, в том числе полнотекстовый поиск. Считает, что JSONB может использоваться для денормализации и ускорения чтения.
### Эталонное решение (AI)
JSON stores text as given; JSONB stores binary parsed structure, faster for queries, supports operators, indexing, GIN/GiST, expression indexes. Use JSONB for flexible schema, metadata, semi-structured payloads, when structure changes often or not all fields are queried. Avoid JSONB for highly normalized relational data, frequent updates of nested fields, very large documents, or when strict schema and joins are needed. Can index specific keys, use tsvector for full-text, but full-text search is often better in dedicated search engine or PostgreSQL full-text with proper indexing.

## Задача 12: PostgreSQL index types, composite/covering indexes, selectivity {#task-012-postgresql-index-types-composite-covering-indexes-selectivity}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Что такое индексы, какие типы, составные и покрывающие индексы, порядок столбцов, когда индекс полезен, когда нет, что такое селективность.
### Решение кандидата
Кандидат называет B-tree, bitmap, hash, full-text, covering/composite indexes. Говорит, что в составном индексе порядок столбцов важен, сначала часто используемое поле. Индекс не полезен при частых записях и редких чтениях, при низкой селективности. Упоминает EXPLAIN/ANALYZE.
### Эталонное решение (AI)
Common PostgreSQL index types: B-tree, default, equality/range/sort; hash, equality; GIN/GiST, JSONB, arrays, full-text, geometric; BRIN, large physically ordered tables. Traditional bitmap indexes are not a standard PostgreSQL index type; bitmap is a scan method. Covering index uses INCLUDE to avoid heap fetch. Composite B-tree uses leftmost prefix; put equality columns first, then range/sort columns, consider selectivity and query patterns. Indexes add write overhead and storage. Not useful for small tables, low-selectivity columns, very high write throughput, or when optimizer chooses seq scan. Selectivity is fraction of rows returned; high selectivity favors index. Use EXPLAIN ANALYZE to verify.

## Задача 13: PostgreSQL EXPLAIN, EXPLAIN ANALYZE, ANALYZE {#task-013-postgresql-database-explain-analyze}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Как посмотреть план запроса, какие команды, как оптимизировать запросы.
### Решение кандидата
Кандидат называет EXPLAIN и EXPLAIN ANALYZE, упоминает ANALYZE для обновления данных/статистик. Рассказывает про миграцию MariaDB на PostgreSQL, где приходилось оптимизировать запросы.
### Эталонное решение (AI)
EXPLAIN shows estimated plan without executing. EXPLAIN ANALYZE executes query and shows actual time, rows, loops. ANALYZE updates planner statistics. Use plans to find sequential scans, nested loops, high-cost joins, missing indexes, bad selectivity. Optimize by adding indexes, rewriting queries, updating statistics, adjusting work_mem, partitioning, materialized views.

## Задача 14: Transaction isolation levels and anomalies in PostgreSQL {#task-014-postgresql-transaction-isolation-anomalies}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Какие уровни изоляции транзакций, какие аномалии они решают, есть ли READ UNCOMMITTED в PostgreSQL, как ведут себя записи в одну строку.
### Решение кандидата
Кандидат описывает READ UNCOMMITTED — грязное чтение, READ COMMITTED — только закомиченные данные, REPEATABLE READ — повторяющееся чтение, SERIALIZABLE — последовательное выполнение. Говорит, что в PostgreSQL READ UNCOMMITTED, возможно, нет или ведёт себя как READ COMMITTED, из-за MVCC. При записи в одну строку ожидаются блокировки, первая транзакция захватывает эксклюзивную блокировку.
### Эталонное решение (AI)
Isolation levels: READ UNCOMMITTED, dirty reads; READ COMMITTED, default in PostgreSQL, no dirty reads; REPEATABLE READ, snapshot, prevents non-repeatable reads and phantom reads for reads within the snapshot, but can allow write skew; SERIALIZABLE, full serializability, PostgreSQL SSI detects conflicts and aborts transactions. PostgreSQL does not support true READ UNCOMMITTED; it behaves as READ COMMITTED because of MVCC. For concurrent updates to same row, row-level locks are used; second transaction waits for first commit/rollback. At SERIALIZABLE, conflicting transactions may fail with serialization failure.

## Задача 15: PostgreSQL MVCC and row versioning {#task-015-postgresql-database-mvcc-row-versioning}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Что такое MVCC, почему в PostgreSQL невозможно READ UNCOMMITTED, как хранятся версии строк.
### Решение кандидата
Кандидат говорит, что MVCC — multiversion control, при изменениях создаются новые версии строк, поэтому невозможно прочитать незакомиченные данные.
### Эталонное решение (AI)
MVCC stores multiple versions of rows with transaction IDs, xmin/xmax. Readers see a snapshot based on transaction ID, so they do not block writers and do not read uncommitted changes. Updates create new row versions; old versions become dead tuples and are removed by VACUUM. This enables long-running transactions and consistent snapshots, but increases storage and requires vacuuming to avoid bloat.

## Задача 16: Database migration from MariaDB to PostgreSQL with dual-write states {#task-016-csharp-database-migration-dual-write}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Описать процесс миграции данных между базами, состояния переключения, транзакционные операции в обе стороны.
### Решение кандидата
Кандидат описывает миграцию MariaDB на PostgreSQL: сначала чтение в MariaDB, репликация в PostgreSQL, затем чтение/запись в PostgreSQL с репликацией обратно в MariaDB для отката, затем полное переключение. Писали отдельные репозитории для транзакционных операций в обе стороны.
### Эталонное решение (AI)
Phased migration: 1) baseline read from source, 2) initial load + continuous replication to target, 3) dual-write or proxy writes to both, 4) switch reads to target, 5) cutover writes, 6) rollback path. Need idempotent replication, conflict resolution, data validation, monitoring lag, query compatibility, index tuning, transaction boundaries. Dual-write is risky; outbox or CDC is often safer.

## Задача 17: Redis caching, LRU, in-memory caches, sharding {#task-017-csharp-caching-redis-lru-sharding}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
С чем работал кандидат в части кэширования: Redis, LRU, in-memory кэши, шардирование.
### Решение кандидата
Кандидат говорит, что использовал Redis, недавно заменял самописный LRU-кэш на встроенный LRU в Redis. В сервисах есть in-memory кэши на ConcurrentDictionary, локальные пулеры наполняют кэши при старте и актуализируют в фоне ночью.
### Эталонное решение (AI)
Redis can be used as distributed cache with TTL and eviction policies such as allkeys-lru, volatile-lru. Use cache-aside pattern, handle cache stampede, invalidation, consistency. In-process caches reduce latency but need invalidation and memory limits. Sharding can be done by key hash or Redis Cluster; choose keys to avoid hot spots. For event-driven updates, use outbox or message invalidation.

## Задача 18: ORM and schema migrations: Link to DB vs EF Core {#task-018-csharp-orm-schema-migrations-link-to-db-vs-ef-core}
**Источник:** [C# вопросы на собеседовании ｜ Пример реального интервью](https://www.youtube.com/watch?v=_qzPdABZUAM)

### Условие
Почему используется Link to DB, а не EF Core, код-фёрст или БД-фёрст.
### Решение кандидата
Кандидат говорит, что продукт старый, подход DB-first, лежат файлы создания таблиц, Link to DB лёгкий, можно влиять на запросы, нативные запросы; EF Core не используется в основном стеке, был опыт в студенчестве/первой работе.
### Эталонное решение (AI)
Link to DB is lightweight migration tool, good for DB-first, explicit SQL, performance control. EF Core provides ORM, change tracking, migrations, LINQ, but may be heavier and abstract SQL. Choose based on team, performance, complex queries, schema evolution. For high-performance data access, Dapper/ADO.NET or Link to DB may be preferred; for rapid development, EF Core.

## Задача 19: Проектирование базы данных для библиотеки {#task-019-golang-database-library-design}
**Источник:** [GOLANG СОБЕСЕДОВАНИЕ OZON НА 380К](https://www.youtube.com/watch?v=z2hdeFw6Q-U)

### Условие
Составьте схему базы данных для библиотеки, включающую сущности: автор, книга и читатель. Определите связи между ними.
### Решение кандидата
Кандидат предложил создать три таблицы: authors, books и readers, с учетом связей один ко многим между авторами и книгами, а также один к одному между книгами и читателями.
### Эталонное решение (AI)
Схема базы данных должна включать таблицы authors, books и readers, с дополнительной таблицей для связи многие ко многим между авторами и книгами. Также следует учитывать, что книга может быть у одного читателя.

## Задача 20: Оптимизация хранения статистики {#task-020-dotnet-database-optimization-statistics}
**Источник:** [РАЗБОР ЗАДАЧИ с собеседования в Альфабэнг на .NET Backend разработчика ｜ C#](https://www.youtube.com/watch?v=kFdA_6Ux4mM)

### Условие
В системе необходимо хранить статистику по начислению кэшбэка. Важно выбрать подходящую базу данных и структуру хранения для эффективной работы с большими объемами данных.
### Решение кандидата
Кандидат предложил использовать Clickhouse для хранения статистики, так как это аналитическая база данных, которая лучше подходит для обработки больших объемов данных.
### Эталонное решение (AI)
Для хранения статистики рекомендуется использовать специализированные аналитические базы данных, такие как Clickhouse или Druid, которые оптимизированы для выполнения запросов на агрегацию и анализа данных.

## Задача 21: SQL запросы {#task-021-sql-query-names-start-a-end-b}
**Источник:** [Как проваливаются собеседования ⧸ Разбор реального собеседования на QA Middle+](https://www.youtube.com/watch?v=vp0ijyXVgzc)

### Условие
Напишите SQL запрос, который выбирает все имена из таблицы, начинающиеся на 'A' и заканчивающиеся на 'B'.
### Решение кандидата
SELECT * FROM table_name WHERE name LIKE 'A%B';
### Эталонное решение (AI)
SELECT name FROM table_name WHERE name LIKE 'A%B';

## Задача 22: Работа с базами данных {#task-022-database-qa-working-with-databases}
**Источник:** [Как проваливаются собеседования ⧸ Разбор реального собеседования на QA Middle+](https://www.youtube.com/watch?v=vp0ijyXVgzc)

### Условие
Как вы работаете с базами данных в своей практике? Какие операции вы выполняете?
### Решение кандидата
Я использую GUI для работы с базами данных, чтобы редактировать данные. Я не пишу сложные запросы, но использую простые операции, такие как выборка и фильтрация данных.
### Эталонное решение (AI)
Работа с базами данных включает в себя выполнение операций CRUD (создание, чтение, обновление, удаление). Я использую SQL для выполнения запросов, а также GUI-инструменты для управления данными и выполнения простых операций.

## Задача 23: Индексы в PostgreSQL {#task-023-postgresql-database-indexes}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Какие типы индексов существуют в PostgreSQL и для каких задач они подходят?
### Решение кандидата
Кандидат упомянул, что в PostgreSQL существуют B-деревья, GiST и GIN индексы. B-деревья подходят для большинства задач, GiST используется для полнотекстового поиска, а GIN - для работы с массивами и JSON. Также кандидат отметил, что индексы могут значительно ускорить выполнение запросов.
### Эталонное решение (AI)
В PostgreSQL существуют различные типы индексов, такие как B-деревья, GiST, GIN и BRIN. B-деревья являются наиболее распространенными и подходят для большинства задач. GiST индексы используются для полнотекстового поиска и работы с геометрическими данными, а GIN индексы эффективны для работы с массивами и JSON. Правильное использование индексов может значительно улучшить производительность запросов.

## Задача 24: Транзакции в базах данных {#task-024-python-database-transactions}
**Источник:** [Python-собес： провал на собеседовании в X5： Почему разработчик получил грейд Junior？](https://www.youtube.com/watch?v=MWHKF2RTodw)

### Условие
Что такое транзакции в базах данных и как они обеспечивают целостность данных?
### Решение кандидата
Кандидат объяснил основные принципы транзакций, такие как атомарность и согласованность, и привел пример использования транзакций для обработки платежей.
### Эталонное решение (AI)
Транзакции обеспечивают целостность данных, гарантируя, что все операции в рамках транзакции либо выполняются полностью, либо не выполняются вовсе, что предотвращает возникновение неконсистентных состояний.

## Задача 25: Индексы в базах данных {#task-025-java-database-indexes}
**Источник:** [Java-собес： менти не дотянул до Middle. Почему нельзя говорить лишнего на собеседовании？](https://www.youtube.com/watch?v=IoXoGi41VtY)

### Условие
Объясните, что такое индексы в базах данных и как они влияют на производительность запросов.
### Решение кандидата
Индексы в базах данных - это структуры данных, которые улучшают скорость операций выборки. Они позволяют быстро находить строки в таблице по значениям определенных столбцов. Однако индексы занимают дополнительное место и могут замедлять операции вставки и обновления, так как индекс также нужно обновлять.
### Эталонное решение (AI)
Индексы в базах данных ускоряют выполнение запросов, позволяя быстро находить записи по определенным полям. Они могут значительно улучшить производительность выборок, но увеличивают объем занимаемого пространства и могут замедлять операции вставки и обновления, так как необходимо поддерживать актуальность индекса.

## Задача 26: Работа с базами данных в микросервисах {#task-026-python-microservices-database-access}
**Источник:** [🔥 Python-собес： Это уровень, за который платят 350k+. Разбор от Senior из Avito](https://www.youtube.com/watch?v=U0NgmwjnP3M)

### Условие
Как вы организуете доступ к базам данных в микросервисной архитектуре? Какие паттерны используете?
### Решение кандидата
Кандидат объясняет, что в микросервисах обычно используется паттерн "Сервис-ориентированная архитектура", где каждый сервис имеет свою собственную базу данных. Однако бывают случаи, когда несколько сервисов могут обращаться к одной базе данных для повышения производительности. Также обсуждаются проблемы, связанные с синхронизацией данных между сервисами.
### Эталонное решение (AI)
В микросервисной архитектуре рекомендуется использовать паттерн "Сервис-ориентированная архитектура", где каждый сервис управляет своей базой данных. Это позволяет избежать жесткой связанности между сервисами. В некоторых случаях, когда необходимо повысить производительность, возможно использование общей базы данных, но это может привести к проблемам с синхронизацией и согласованностью данных.

## Задача 27: SQL-инъекция {#task-027-sql-injection-security-prevention}
**Источник:** [Go Live Interview с Senior-разработчиком из Ozon](https://www.youtube.com/watch?v=Yt0M8-hfYYQ)

### Условие
Объясните, что такое SQL-инъекция и как ее можно предотвратить в приложении.
### Решение кандидата
Кандидат объясняет, что SQL-инъекция происходит, когда злоумышленник вставляет вредоносный SQL-код в запрос. Он предлагает использовать подготовленные выражения для предотвращения этой уязвимости.
### Эталонное решение (AI)
SQL-инъекция — это уязвимость, позволяющая злоумышленнику манипулировать запросами к базе данных. Для предотвращения SQL-инъекций следует использовать подготовленные выражения и параметры запроса, что гарантирует, что ввод пользователя не будет интерпретирован как часть SQL-запроса.

## Задача 28: Индексы в PostgreSQL {#task-028-postgresql-database-indexes}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Обсудите различные типы индексов в PostgreSQL и их применение.
### Решение кандидата
Кандидат упомянул, что в PostgreSQL существуют разные типы индексов, такие как B-tree, GiST и GIN. Он объяснил, что B-tree подходит для большинства случаев, GiST используется для полнотекстового поиска, а GIN - для работы с массивами и JSON. Также он отметил, что индексы могут улучшить производительность запросов, но их использование требует понимания структуры данных.
### Эталонное решение (AI)
В PostgreSQL индексы, такие как B-tree, GiST и GIN, используются для оптимизации поиска данных. B-tree является стандартным индексом, GiST подходит для геометрических данных, а GIN эффективен для полнотекстового поиска и работы с массивами. Выбор индекса зависит от типа данных и запросов, которые будут выполняться.

## Задача 29: Нормализация и денормализация данных {#task-029-python-database-normalization-denormalization}
**Источник:** [Python-собес： Middle？ Он почти Senior. Разбор реального собеса в Avito⧸Яндекс с экс-техлидом](https://www.youtube.com/watch?v=TW6ahFOKaZ8)

### Условие
Обсудите, что такое нормализация и денормализация данных, и когда их следует использовать.
### Решение кандидата
Кандидат объяснил, что нормализация данных помогает избежать избыточности и аномалий, в то время как денормализация может быть полезна для повышения производительности в системах с высокими нагрузками, где требуется минимизировать количество соединений между таблицами. Он также упомянул, что в микросервисной архитектуре денормализация может упростить доступ к данным.
### Эталонное решение (AI)
Нормализация данных - это процесс организации данных для уменьшения избыточности, тогда как денормализация - это процесс объединения данных для повышения производительности. Денормализация может быть полезна в системах, где производительность критична, и когда частые соединения между таблицами могут замедлить выполнение запросов.

## Задача 30: Модель библиотеки {#task-030-golang-model-library}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Создайте модель библиотеки, содержащую сущности автор, книга и читатель, с учетом того, что физическая книга может принадлежать только одному читателю.
### Решение кандидата
Необходимо создать три таблицы: Authors, Books и Readers, с соответствующими связями между ними. Книга может быть связана только с одним читателем, а автор может иметь несколько книг.
### Эталонное решение (AI)
Для реализации модели библиотеки создаются три таблицы: 1) Authors (id, name); 2) Books (id, title, author_id); 3) Readers (id, name, book_id). Связь между книгами и читателями реализуется через поле book_id в таблице Readers, что позволяет отслеживать, какая книга находится у какого читателя.

## Задача 31: Запросы к базе данных {#task-031-sql-database-queries}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Напишите SQL-запросы для следующих задач: 1) Найти все книги, которые находятся на руках; 2) Выбрать названия всех книг в библиотеке, у которых более трех авторов; 3) Выбрать имена трех самых читаемых авторов.
### Решение кандидата
1) SELECT title FROM Books WHERE id IN (SELECT book_id FROM Readers); 2) SELECT title FROM Books WHERE id IN (SELECT book_id FROM BookAuthors GROUP BY book_id HAVING COUNT(author_id) > 3); 3) SELECT author_id, COUNT(*) as read_count FROM Readers GROUP BY author_id ORDER BY read_count DESC LIMIT 3;
### Эталонное решение (AI)
1) SELECT title FROM Books WHERE id IN (SELECT book_id FROM Readers); 2) SELECT title FROM Books WHERE id IN (SELECT book_id FROM BookAuthors GROUP BY book_id HAVING COUNT(author_id) > 3); 3) SELECT author_id, COUNT(*) as read_count FROM Readers GROUP BY author_id ORDER BY read_count DESC LIMIT 3;

## Задача 32: Хэш-таблицы и словари {#task-032-python-data-structure-hash-tables}
**Источник:** [Собеседование Python： Senior инженер из Avito сказал ＂Беру в команду＂](https://www.youtube.com/watch?v=9cO7UcqTZMI)

### Условие
Объясните, что такое хэш-таблица и как она реализована в Python. Какие проблемы могут возникнуть при использовании хэш-таблиц?
### Решение кандидата
Кандидат описывает хэш-таблицы как структуры данных, которые используют хэш-функцию для быстрого доступа к данным по ключу. Упоминает о возможных коллизиях и методах их разрешения.
### Эталонное решение (AI)
Хэш-таблица - это структура данных, которая использует хэш-функцию для вычисления индекса, по которому хранятся значения. В Python словари реализованы как хэш-таблицы. Основные проблемы, которые могут возникнуть, это коллизии, когда два ключа имеют одинаковый хэш. Для разрешения коллизий могут использоваться методы цепочек или открытой адресации.

## Задача 33: Индексы в PostgreSQL {#task-033-postgresql-database-indexes}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Объясните, что такое индексы в PostgreSQL и как они влияют на производительность запросов.
### Решение кандидата
Индексы в PostgreSQL используются для ускорения поиска данных в таблицах. Они позволяют избежать полного сканирования таблицы, что значительно увеличивает скорость выполнения запросов. Однако при добавлении или обновлении данных индексы также требуют обновления, что может замедлить операции записи.
### Эталонное решение (AI)
Индексы в PostgreSQL — это структуры данных, которые улучшают скорость выполнения запросов, позволяя базе данных быстро находить строки без необходимости сканирования всей таблицы. Индексы могут значительно ускорить операции чтения, но могут замедлить операции записи, так как при изменении данных индексы также должны обновляться.

## Задача 34: Транзакции в базах данных {#task-034-python-database-transactions}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Объясните, что такое транзакции в контексте баз данных и какие свойства они имеют.
### Решение кандидата
Транзакции — это последовательности операций, которые выполняются как единое целое. Если одна из операций не удается, все изменения, сделанные в рамках транзакции, откатываются. Основные свойства транзакций известны как ACID: атомарность, согласованность, изолированность и долговечность.
### Эталонное решение (AI)
Транзакции в базах данных — это группы операций, которые выполняются как единое целое. Если одна из операций не удается, все изменения откатываются, что обеспечивает целостность данных. Свойства ACID (атомарность, согласованность, изолированность и долговечность) гарантируют надежность и предсказуемость транзакций.

## Задача 35: Репликация и шардирование {#task-035-python-database-replication-sharding}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Объясните, что такое репликация и шардирование в контексте баз данных и как они помогают в управлении большими объемами данных.
### Решение кандидата
Репликация — это процесс создания копий базы данных для распределения нагрузки и повышения доступности. Шардирование — это метод разделения данных на несколько баз данных или серверов для улучшения производительности и масштабируемости. Оба метода помогают справляться с большими объемами данных и увеличивают скорость обработки запросов.
### Эталонное решение (AI)
Репликация в базах данных — это создание копий данных для повышения доступности и распределения нагрузки. Шардирование — это процесс разделения данных на несколько частей (шардов), которые могут храниться на разных серверах, что позволяет улучшить производительность и масштабируемость системы. Оба метода помогают эффективно управлять большими объемами данных и обеспечивают высокую доступность.

## Задача 36: Транзакции в базах данных {#task-036-python-database-transactions}
**Источник:** [Python-собес： провал на собеседовании в X5： Почему разработчик получил грейд Junior？](https://www.youtube.com/watch?v=MWHKF2RTodw)

### Условие
Объясните, что такое транзакции в базах данных и когда они необходимы.
### Решение кандидата
Кандидат объяснил, что транзакции обеспечивают целостность данных и необходимы, когда несколько операций должны быть выполнены как единое целое.
### Эталонное решение (AI)
Транзакции в базах данных обеспечивают атомарность, согласованность, изоляцию и долговечность (ACID). Они необходимы, когда операции зависят друг от друга, чтобы избежать частичного выполнения и сохранить целостность данных.

## Задача 37: Различия между регистрами в 1С {#task-037-1c-database-registers-case-sensitivity}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Каковы различия между измерениями, ресурсами и атрибутами в регистрах 1С?
### Решение кандидата
Измерения - это категории хранения данных, ресурсы - это значения, которые мы храним, а атрибуты - это дополнительная информация.
### Эталонное решение (AI)
В 1С измерения представляют собой категории, в которых хранятся данные, ресурсы - это фактические значения, которые мы отслеживаем, а атрибуты предоставляют дополнительную информацию о данных, позволяя более детально классифицировать и анализировать их.

## Задача 38: Ограничения на ресурсы в регистрах {#task-038-1c-resources-restrictions}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Какие ограничения существуют на ресурсы в регистрах 1С?
### Решение кандидата
В регистрах накопления есть ограничения на типы данных, которые могут храниться, например, только числовые значения.
### Эталонное решение (AI)
В регистрах накопления в 1С существуют ограничения на типы данных, которые могут храниться в ресурсах. Например, в регистрах накопления можно хранить только числовые значения, в то время как в информационных регистрах таких ограничений нет.

## Задача 39: Различия между остатками и оборотами в регистрах {#task-039-1c-difference-registers}
**Источник:** [РЕАЛЬНОЕ СОБЕСЕДОВАНИЕ ПРОГРАММИСТА 1С на 250.000 РУБЛЕЙ](https://www.youtube.com/watch?v=QSxrYt7BbEs)

### Условие
Каковы основные различия между остатками и оборотами в регистрах 1С?
### Решение кандидата
Остатки хранят как остатки, так и обороты, а обороты хранят только обороты. Остатки более универсальны, но обороты оптимизированы для больших конфигураций.
### Эталонное решение (AI)
Остатки в регистрах 1С могут хранить как текущие остатки, так и обороты, тогда как обороты хранят только данные о движениях. Остатки обеспечивают более универсальное хранение данных, в то время как обороты оптимизированы для быстрого доступа к данным о движениях.

## Задача 40: Индексы в PostgreSQL {#task-040-postgresql-database-indexes}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Объясните, что такое индексы в PostgreSQL и как они влияют на производительность запросов.
### Решение кандидата
Кандидат объясняет, что индексы используются для ускорения поиска данных в таблицах. Он упоминает, что индексы хранятся на диске и могут значительно ускорить выполнение запросов, но также могут замедлить операции вставки и обновления данных, так как индексы нужно обновлять при изменении данных.
### Эталонное решение (AI)
Индексы в PostgreSQL - это структуры данных, которые позволяют ускорить поиск строк в таблицах. Они хранятся на диске и обеспечивают быстрый доступ к данным, что значительно улучшает производительность запросов. Однако индексы могут замедлить операции вставки и обновления, так как они требуют дополнительного времени для обновления при изменении данных.

## Задача 41: Транзакции в базах данных {#task-041-python-database-transactions}
**Источник:** [Python-собес： Кандидат, который понравился нанимающему на позицию Middle](https://www.youtube.com/watch?v=g60itOidGck)

### Условие
Что такое транзакции в базах данных и какие свойства они имеют?
### Решение кандидата
Кандидат объясняет, что транзакция - это последовательность операций, которые выполняются как единое целое. Он упоминает свойства ACID (атомарность, согласованность, изолированность, долговечность), которые гарантируют надежность транзакций.
### Эталонное решение (AI)
Транзакции в базах данных - это группы операций, которые выполняются как единое целое. Они имеют свойства ACID: атомарность (все операции выполняются или ни одна), согласованность (транзакция переводит базу данных из одного согласованного состояния в другое), изолированность (параллельные транзакции не влияют друг на друга) и долговечность (результаты транзакции сохраняются даже в случае сбоя системы).

## Задача 42: Сравнение Clickhouse и PostgreSQL {#task-042-sql-comparison-clickhouse-postgresql}
**Источник:** [КРУТЕЙШЕЕ СОБЕСЕДОВАНИЕ на Python-разработчика (кандидат разнес на собеседовании)](https://www.youtube.com/watch?v=avK0RjT8an0)

### Условие
Объясните ключевую архитектурную разницу между Clickhouse и PostgreSQL. Почему Clickhouse лучше подходит для аналитики?
### Решение кандидата
Кандидат объяснил, что PostgreSQL ориентирован на строки, что делает его менее эффективным для аналитических запросов, в то время как Clickhouse хранит данные по столбцам, что позволяет быстро выполнять запросы на большие объемы данных.
### Эталонное решение (AI)
Clickhouse оптимизирован для аналитических запросов благодаря хранению данных по столбцам, что позволяет извлекать только необходимые данные, в то время как PostgreSQL, храня данные по строкам, требует чтения всей строки для получения информации из одного столбца.

## Задача 43: Уровни изоляции транзакций в SQL {#task-043-sql-transaction-isolation-levels}
**Источник:** [Успешное собеседование в Яндекс： Go-разработчик, которого одобрили на мидла. Разбор.](https://www.youtube.com/watch?v=3xNiAjmRSf0)

### Условие
Какие уровни изоляции транзакций существуют в SQL и в чем их отличие?
### Решение кандидата
Кандидат объяснил, что существуют уровни изоляции, такие как read uncommitted, read committed, repeatable read и serializable, каждый из которых имеет свои особенности и гарантии.
### Эталонное решение (AI)
Уровни изоляции транзакций в SQL включают: 1) Read Uncommitted - позволяет читать незавершенные изменения; 2) Read Committed - защищает от грязного чтения; 3) Repeatable Read - защищает от неповторяемого чтения; 4) Serializable - обеспечивает полную изоляцию. Каждый уровень имеет свои гарантии и ограничения по производительности.

## Задача 44: ACID-принципы в базах данных {#task-044-database-acid-principles}
**Источник:** [Успешное собеседование в Яндекс： Go-разработчик, которого одобрили на мидла. Разбор.](https://www.youtube.com/watch?v=3xNiAjmRSf0)

### Условие
Что такое ACID и какие принципы он включает?
### Решение кандидата
Кандидат объяснил, что ACID включает атомарность, консистентность, изолированность и отказоустойчивость.
### Эталонное решение (AI)
ACID - это набор принципов, обеспечивающих надежность транзакций в реляционных базах данных. Атомарность гарантирует, что транзакция выполняется полностью или не выполняется вовсе. Консистентность обеспечивает переход базы данных из одного согласованного состояния в другое. Изолированность гарантирует, что транзакции не влияют друг на друга. Отказоустойчивость обеспечивает сохранение данных в случае сбоя системы.

## Задача 45: Модель библиотеки {#task-045-golang-model-library}
**Источник:** [ОТОЗВАЛИ ОФФЕР за НАКРУТКУ ОПЫТА! Реальное Golang СОБЕСЕДОВАНИЕ на ЗП 350-400к!](https://www.youtube.com/watch?v=Th-dNiOa6Xw)

### Условие
Спроектируйте модель библиотеки с сущностями автор, книга и читатель, учитывая, что физическая книга только одна и может быть у одного читателя.
### Решение кандидата
Создать три таблицы: Authors, Books и Readers. Связь между таблицами: одна книга может принадлежать только одному читателю, а один читатель может иметь только одну книгу.
### Эталонное решение (AI)
Таблицы должны включать внешние ключи для связи между сущностями, а также учитывать ограничения по количеству экземпляров книг.

## Задача 46: Уровни изоляции транзакций в SQL {#task-046-sql-transaction-isolation-levels}
**Источник:** [Успешное собеседование в Яндекс： Go-разработчик, которого одобрили на мидла. Разбор.](https://www.youtube.com/watch?v=3xNiAjmRSf0)

### Условие
Объясните уровни изоляции транзакций в SQL и их особенности.
### Решение кандидата
Существуют несколько уровней изоляции: read uncommitted, read committed, repeatable read и serializable. Каждый уровень имеет свои особенности и гарантии.
### Эталонное решение (AI)
Уровни изоляции транзакций в SQL определяют, как транзакции взаимодействуют друг с другом. Read uncommitted позволяет видеть незавершенные изменения, что может привести к грязным чтениям. Read committed предотвращает грязные чтения, но не защищает от неповторяемых чтений. Repeatable read защищает от неповторяемых чтений, а serializable обеспечивает полную изоляцию, предотвращая все возможные артефакты.

## Задача 47: ACID-принципы в базах данных {#task-047-database-acid-principles}
**Источник:** [Успешное собеседование в Яндекс： Go-разработчик, которого одобрили на мидла. Разбор.](https://www.youtube.com/watch?v=3xNiAjmRSf0)

### Условие
Что такое принципы ACID в базах данных?
### Решение кандидата
ACID - это набор принципов, обеспечивающих надежность транзакций: атомарность, согласованность, изоляция и долговечность.
### Эталонное решение (AI)
Принципы ACID в базах данных гарантируют, что транзакции будут выполнены надежно. Атомарность означает, что транзакция выполняется полностью или не выполняется вовсе. Согласованность гарантирует, что транзакции переводят базу данных из одного согласованного состояния в другое. Изоляция обеспечивает, что транзакции не влияют друг на друга, а долговечность гарантирует, что изменения, внесенные транзакцией, сохранятся даже в случае сбоя системы.

## Задача 48: Классификация баз данных {#task-048-database-classification}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Назовите классификации баз данных и приведите примеры.
### Решение кандидата
Базы данных могут быть реляционными или нереляционными. Реляционные базы данных предназначены для обеспечения целостности данных и сложных запросов, тогда как нереляционные базы данных обеспечивают высокую скорость работы и менее строгую структуру хранения данных.
### Эталонное решение (AI)
Реляционные базы данных используют таблицы для хранения данных и поддерживают сложные запросы, в то время как нереляционные базы данных, такие как NoSQL, хранят данные в более свободной форме, что позволяет быстрее обрабатывать большие объемы информации.

## Задача 49: SQL запрос на сортировку {#task-049-sql-query-sorting}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Напишите SQL запрос, который отсортирует данные в таблице по полю зарплаты в порядке убывания.
### Решение кандидата
SELECT * FROM employees ORDER BY salary DESC;
### Эталонное решение (AI)
SELECT * FROM employees ORDER BY salary DESC;

## Задача 50: SQL запрос на подсчет уникальных зарплат {#task-050-sql-query-unique-salaries}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Напишите SQL запрос, который подсчитает количество различных зарплат в таблице.
### Решение кандидата
SELECT COUNT(DISTINCT salary) FROM employees;
### Эталонное решение (AI)
SELECT COUNT(DISTINCT salary) FROM employees;

## Задача 51: SQL запрос на выборку сотрудников старше 27 лет {#task-051-sql-query-employee-age-over-27}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Напишите SQL запрос, который выберет имена и возраст сотрудников, которые старше 27 лет.
### Решение кандидата
SELECT name, age FROM employees WHERE age > 27;
### Эталонное решение (AI)
SELECT name, age FROM employees WHERE age > 27;

## Задача 52: SQL запрос на группировку зарплат по возрасту {#task-052-sql-query-grouping-salaries-by-age}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Напишите SQL запрос, который подсчитает максимальную зарплату в каждой группе по возрасту.
### Решение кандидата
SELECT age, MAX(salary) FROM employees GROUP BY age;
### Эталонное решение (AI)
SELECT age, MAX(salary) FROM employees GROUP BY age;

## Задача 53: SQL запрос на выборку сотрудников без назначения {#task-053-sql-query-employees-without-assignment}
**Источник:** [ЖЕСТКИЙ собес на Manual QA： 2 часа теории и задач! Реальное интервью тестировщика](https://www.youtube.com/watch?v=QtKN5w_YWr0)

### Условие
Напишите SQL запрос для выборки сотрудников, которые не назначены никуда.
### Решение кандидата
SELECT * FROM employees WHERE office_id IS NULL;
### Эталонное решение (AI)
SELECT * FROM employees WHERE office_id IS NULL;

## Задача 54: Разница между ClickHouse и PostgreSQL {#task-054-sql-database-difference-clickhouse-postgresql}
**Источник:** [КРУТЕЙШЕЕ СОБЕСЕДОВАНИЕ на Python-разработчика (кандидат разнес на собеседовании)](https://www.youtube.com/watch?v=avK0RjT8an0)

### Условие
Объясните ключевое архитектурное отличие ClickHouse от PostgreSQL. Почему ClickHouse лучше подходит для аналитики?
### Решение кандидата
Кандидат отметил, что ClickHouse ориентирован на колонное хранение данных, что позволяет эффективно обрабатывать аналитические запросы, в то время как PostgreSQL использует строковое хранение, что делает его менее эффективным для больших объемов данных.
### Эталонное решение (AI)
ClickHouse хранит данные по колонкам, что позволяет быстро считывать только необходимые данные для аналитики, тогда как PostgreSQL хранит данные по строкам, что требует больше ресурсов для выполнения аналогичных запросов.

## Задача 55: Топ авторов по продажам книг {#task-055-sql-query-authors-top-sales}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Постройте запрос, чтобы выбрать всех авторов, чьи общие продажи книг превышают 500,000 рублей.
### Решение кандидата
Для решения задачи необходимо объединить таблицы authors, books и Books_Authors, используя JOIN по соответствующим идентификаторам. Затем нужно рассчитать общую выручку от продаж книг, используя SUM, и отфильтровать авторов с выручкой более 500,000 рублей.
### Эталонное решение (AI)
SELECT DISTINCT a.id, a.name, SUM(b.price * b.sold) AS total_revenue
FROM authors a
JOIN Books_Authors ba ON a.id = ba.author_id
JOIN books b ON ba.book_id = b.id
GROUP BY a.id, a.name
HAVING SUM(b.price * b.sold) > 500000;

## Задача 56: Учет зарплат сотрудников {#task-056-sql-salary-count}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Необходимо подсчитать количество сотрудников в каждой категории зарплат: низкая (менее 20,000), средняя (от 20,000 до 50,000) и высокая (более 50,000). Итоговая таблица должна включать все категории, даже если в них нет сотрудников.
### Решение кандидата
Для решения задачи можно использовать CASE для определения категории зарплаты и GROUP BY для подсчета количества сотрудников в каждой категории. Также нужно использовать UNION для объединения результатов.
### Эталонное решение (AI)
SELECT 'Low Salary' AS category, COUNT(*) AS count
FROM employees WHERE salary < 20000
UNION ALL
SELECT 'Average Salary', COUNT(*)
FROM employees WHERE salary >= 20000 AND salary < 50000
UNION ALL
SELECT 'High Salary', COUNT(*)
FROM employees WHERE salary >= 50000;

## Задача 57: Пилоты на пассажирских рейсах {#task-057-sql-query-passenger-pilots}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Выведите имена всех пилотов старше 45 лет, которые выполняли рейсы на пассажирских самолетах с вместимостью более 30 человек.
### Решение кандидата
Для решения задачи необходимо объединить таблицы pilots, flights и planes, используя JOIN. Затем нужно отфильтровать пилотов по возрасту и условиям рейсов.
### Эталонное решение (AI)
SELECT DISTINCT p.name
FROM pilots p
JOIN flights f ON p.id = f.pilot_id
JOIN planes pl ON f.plane_id = pl.id
WHERE p.age > 45 AND pl.capacity > 30;

## Задача 58: Средний возраст клиентов, купивших смарт-часы {#task-058-sql-analytics-average-age-smartwatches}
**Источник:** [Решаю SQL задачи с собеседований в Сбербанк, Т-Банк и Альфа-Банк](https://www.youtube.com/watch?v=VfibihTVKE4)

### Условие
Каков средний возраст клиентов, купивших смарт-часы?
### Решение кандидата
Для решения задачи нужно объединить таблицы purchases, customers и products, отфильтровав по названию продукта и дате покупки. Затем необходимо рассчитать средний возраст клиентов, учитывая уникальных клиентов.
### Эталонное решение (AI)
SELECT AVG(c.age) AS average_age
FROM customers c
JOIN purchases p ON c.customer_id = p.customer_id
JOIN products pr ON p.product_id = pr.id
WHERE pr.name = 'Smart Watch' AND EXTRACT(YEAR FROM p.date) = 2024;

## Задача 59: Город с минимальным населением {#task-059-sql-query-city-min-population}
**Источник:** [Решаю SQL задачи с собеседований в Ozon и Wildberries](https://www.youtube.com/watch?v=1ldXxsEpopM)

### Условие
Напишите SQL запрос, который выводит название города с минимальным населением из таблицы.
### Решение кандидата
Используем сортировку по столбцу population в порядке возрастания и выбираем первую строку.
### Эталонное решение (AI)
SELECT city FROM cities ORDER BY population ASC LIMIT 1;

## Задача 60: Уникальные пользователи и товары до бана {#task-060-sql-unique-users-products}
**Источник:** [Решаю SQL задачи с собеседований в Ozon и Wildberries](https://www.youtube.com/watch?v=1ldXxsEpopM)

### Условие
Необходимо посмотреть, сколько уникальных пользователей и уникальных товаров было в системе до бана пользователя. Учитывать все покупки, если пользователь не был забанен.
### Решение кандидата
Используем JOIN для соединения таблиц пользователей и покупок, фильтруем по дате бана.
### Эталонное решение (AI)
SELECT DISTINCT u.user_id, u.first_name, u.last_name, p.sku FROM users u LEFT JOIN purchases p ON u.user_id = p.user_id WHERE p.date < u.ban_date OR u.ban_date IS NULL;

## Задача 61: Дерево узлов {#task-061-sql-tree-node-type}
**Источник:** [Решаю SQL задачи с собеседований в Ozon и Wildberries](https://www.youtube.com/watch?v=1ldXxsEpopM)

### Условие
Представьте таблицу с узлами и родителями как дерево. Определите, какой узел является корнем, внутренним узлом или конечным узлом (листьем).
### Решение кандидата
Используем CASE WHEN для определения типа узла на основе наличия родителя и детей.
### Эталонное решение (AI)
SELECT node, CASE WHEN parent IS NULL THEN 'root' WHEN node NOT IN (SELECT parent FROM nodes) THEN 'leaf' ELSE 'internal' END AS label FROM nodes;

## Задача 62: Работа с базами данных в Go {#task-062-go-database-management}
**Источник:** [Собеседуем Go-разработчика вместе с Senior из Ozon](https://www.youtube.com/watch?v=s1Lo_RQx3xs)

### Условие
Опишите, как вы будете обрабатывать запросы к базе данных в Go, включая управление соединениями и обработку ошибок.
### Решение кандидата
Кандидат предложил использовать пул соединений для управления соединениями с базой данных и проверять ошибки после каждого запроса. Он также упомянул о необходимости закрытия соединений при завершении работы приложения.
### Эталонное решение (AI)
Для работы с базами данных в Go рекомендуется использовать пакет `database/sql` и пул соединений:
```go
db, err := sql.Open("postgres", dsn)
if err != nil {
    log.Fatal(err)
}
defer db.Close()

// Пример выполнения запроса
err = db.QueryRow("SELECT name FROM users WHERE id = $1", userID).Scan(&name)
if err != nil {
    log.Fatal(err)
}
```

## Задача 63: Индексы в базах данных {#task-063-java-database-indexes}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Объясните, как работают B-деревья, хэш-индексы и сложные индексы. Каковы основные принципы работы индексов в PostgreSQL?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 64: Транзакции и уровни изоляции {#task-064-java-database-transaction-isolation-levels}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Объясните, что такое ACID и какие уровни изоляции транзакций существуют. Как они влияют на работу с базами данных?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 65: Уровни изоляции транзакций в SQL {#task-065-sql-transaction-isolation-levels}
**Источник:** [ВСЕ ВОПРОСЫ с ЖЕСТКОГО собеседования на Python-разработчика ЗА 10 МИНУТ (оффер на 260к)](https://www.youtube.com/watch?v=qmvyuwV5lAg)

### Условие
Объяснить уровни изоляции транзакций в SQL и их влияние на работу с базой данных.
### Решение кандидата
Кандидат описал четыре уровня изоляции: read uncommitted, read committed, repeatable read и serializable, объяснив их особенности и применение.
### Эталонное решение (AI)
Уровни изоляции помогают контролировать, как транзакции взаимодействуют друг с другом. Например, read uncommitted позволяет читать незакоммиченные данные, что может привести к ошибкам, тогда как serializable обеспечивает полную изоляцию, предотвращая любые конфликты между транзакциями.

## Задача 66: Проблемы, решаемые уровнями изоляции {#task-066-sql-isolation-levels-issues}
**Источник:** [ВСЕ ВОПРОСЫ с ЖЕСТКОГО собеседования на Python-разработчика ЗА 10 МИНУТ (оффер на 260к)](https://www.youtube.com/watch?v=qmvyuwV5lAg)

### Условие
Какие проблемы решает уровень изоляции serializable в SQL?
### Решение кандидата
Кандидат объяснил, что уровень serializable защищает от неповторяющегося чтения и фантомного чтения, обеспечивая целостность данных.
### Эталонное решение (AI)
Уровень serializable предотвращает ситуации, когда данные изменяются между запросами в рамках одной транзакции, а также защищает от появления новых строк, соответствующих условиям выборки, что критично для обеспечения консистентности данных.

## Задача 67: Запрос на выборку всех свободных книг {#task-067-sql-query-free-books}
**Источник:** [РЕАЛЬНОЕ собеседование Senior Golang Backend на 6000$ ｜ (+ Live-coding)](https://www.youtube.com/watch?v=AKURknsxTwU)

### Условие
Напишите SQL-запрос, который выбирает названия всех книг, которые не находятся у читателей.

### Решение кандидата
Кандидат предложил использовать запрос, который выбирает названия книг из таблицы Books, где поле reader_id равно NULL.

### Эталонное решение (AI)
Запрос может выглядеть следующим образом:
```sql
SELECT title FROM Books WHERE reader_id IS NULL;
```

## Задача 68: Запрос на топ-3 читаемых авторов {#task-068-golang-sql-top-3-authors}
**Источник:** [РЕАЛЬНОЕ собеседование Senior Golang Backend на 6000$ ｜ (+ Live-coding)](https://www.youtube.com/watch?v=AKURknsxTwU)

### Условие
Напишите SQL-запрос, который находит топ-3 автора по количеству книг, которые были взяты читателями.

### Решение кандидата
Кандидат предложил использовать группировку по id автора и подсчет количества книг, а затем сортировку по этому количеству.

### Эталонное решение (AI)
Запрос может выглядеть следующим образом:
```sql
SELECT author_id, COUNT(*) as book_count
FROM BookReaders
GROUP BY author_id
ORDER BY book_count DESC
LIMIT 3;
```

## Задача 69: ACID и уровни изоляции транзакций {#task-069-java-database-acid-isolation-levels}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Что такое ACID и какие уровни изоляции транзакций существуют?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 70: Хэширование и коллизии {#task-070-java-algorithm-hashing-collisions}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Как строится хэш под капотом? Как разрешаются коллизии?
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 71: Индексы в PostgreSQL {#task-071-postgresql-database-indexes}
**Источник:** [ВСЁ про JAVA-СОБЕСЕДОВАНИЯ В 2026. ЗАРПЛАТЫ, ЛОВУШКИ, ВОПРОСЫ](https://www.youtube.com/watch?v=X7Nc1hdcHB8)

### Условие
Объясните, как работают B-tree индексы и какие существуют другие типы индексов в PostgreSQL.
### Решение кандидата
...
### Эталонное решение (AI)
...

## Задача 72: SQL запрос для уникальных комбинаций {#task-072-sql-query-unique-combinations}
**Источник:** [Golang Собеседование в OZON - Технический скрининг на 400к](https://www.youtube.com/watch?v=TXh6ociaJJ4)

### Условие
Напишите SQL запрос для вывода уникальных комбинаций пользователя и ID товара для всех покупок, совершенных пользователями до их бана.
### Решение кандидата
Кандидат обсуждает, как написать запрос с использованием JOIN и DISTINCT, чтобы получить нужные данные, и объясняет логику запроса.
### Эталонное решение (AI)
Запрос должен использовать LEFT JOIN для соединения таблиц пользователей и банов, а также фильтровать результаты по условиям, чтобы получить уникальные комбинации.

## Задача 73: Объяснение типов JOIN в SQL {#task-073-sql-join-explanation}
**Источник:** [Golang Собеседование в OZON - Технический скрининг на 400к](https://www.youtube.com/watch?v=TXh6ociaJJ4)

### Условие
Объясните, какие типы JOIN существуют и когда их использовать.
### Решение кандидата
Кандидат объясняет различия между INNER JOIN и LEFT JOIN, а также упоминает CROSS JOIN и их применение в запросах.
### Эталонное решение (AI)
INNER JOIN возвращает только совпадающие записи, LEFT JOIN возвращает все записи из левой таблицы и совпадающие из правой, а CROSS JOIN создает декартово произведение двух таблиц.

## Задача 74: Выбор базы данных для хранения твитов {#task-074-database-selection-twitter-storage}
**Источник:** [МОК-интервью по System Design ⧸ Проектируем ленту Twitter](https://www.youtube.com/watch?v=ZCDFbrpk3WM)

### Условие
Необходимо выбрать подходящую базу данных для хранения твитов, учитывая, что твиты будут содержать текст, идентификаторы пользователей и медиафайлы. Также нужно учесть, что система будет иметь высокую нагрузку на чтение.
### Решение кандидата
Кандидат предложил использовать MongoDB для хранения твитов, так как это NoSQL база данных, которая хорошо подходит для хранения документов без жесткой схемы. Также обсуждался выбор PostgreSQL для сервиса подписок из-за наличия отношений между пользователями.
### Эталонное решение (AI)
Эталонное решение включает в себя использование MongoDB для хранения твитов из-за его гибкости и масштабируемости, а также PostgreSQL для сервисов, где важны отношения между сущностями, таких как подписки. Рекомендуется также рассмотреть возможность шардирования и репликации для обеспечения отказоустойчивости.

## Задача 75: Вопрос: Индексы в базах данных {#task-075-go-database-indexes}
**Источник:** [Мок-собеседование Middle Go-разработчика： что спрашивают в Avito и Ozon](https://www.youtube.com/watch?v=ArpOzrG0gCM)

### Условие
Объясните, что такое индексы в базах данных, для чего они нужны и как они влияют на производительность.
### Решение кандидата
Кандидат отметил, что индексы - это структуры, которые ускоряют поиск данных в таблицах. Он также упомянул, что индексы могут замедлять операции вставки и обновления, так как их необходимо поддерживать.
### Эталонное решение (AI)
Индексы в базах данных - это специальные структуры, которые позволяют ускорить поиск записей. Они могут значительно улучшить производительность запросов, но при этом увеличивают время выполнения операций вставки и обновления, так как индексы должны быть обновлены при каждом изменении данных.

## Задача 76: Транзакции и уровни изоляции {#task-076-go-database-transaction-isolation-levels}
**Источник:** [Разбираю ТОП-12 вопросов с собеседований на Go-разработчика в Ozon](https://www.youtube.com/watch?v=MyBpFrMLBaQ)

### Условие
Что такое транзакция и какие уровни изоляции существуют?
### Решение кандидата
Существуют четыре уровня изоляции: read uncommitted, read committed, repeatable read и serializable.
### Эталонное решение (AI)
1. Read uncommitted: видит незакомиченные изменения.
2. Read committed: видит только закомиченные.
3. Repeatable read: данные стабильны в транзакциях.
4. Serializable: полная изоляция.

## Задача 77: Уровни изоляции в PostgreSQL {#task-077-postgresql-isolation-levels}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Обсудить уровни изоляции транзакций в PostgreSQL и их влияние на консистентность данных.
### Решение кандидата
Кандидат упоминает, что в PostgreSQL существуют уровни изоляции, такие как Read Committed, Repeatable Read и Serializable, и объясняет их различия.
### Эталонное решение (AI)
Уровни изоляции в PostgreSQL определяют, как транзакции взаимодействуют друг с другом. Read Committed позволяет видеть изменения, сделанные другими транзакциями, в то время как Repeatable Read и Serializable обеспечивают более строгую изоляцию, предотвращая проблемы с конкурентным доступом и обеспечивая консистентность данных.

## Задача 78: Индексы в PostgreSQL {#task-078-postgresql-database-indexes}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Какие типы индексов существуют в PostgreSQL и как они влияют на производительность запросов?
### Решение кандидата
Кандидат упоминает, что наиболее распространённый тип индекса - это B-tree, и объясняет, как он работает и когда его следует использовать.
### Эталонное решение (AI)
В PostgreSQL существуют различные типы индексов, включая B-tree, Hash, GiST, SP-GiST и GIN. Каждый тип индекса оптимизирован для определённых типов запросов и данных. Например, B-tree индексы хорошо подходят для диапазонных запросов, в то время как GIN индексы эффективны для полнотекстового поиска.

## Задача 79: Кэширование данных {#task-079-python-interview-cache-data}
**Источник:** [Собеседование Python Middle ⧸ Senior. Вопросы и ответы + разбор от Техлида (IVI, VK, Avito)](https://www.youtube.com/watch?v=zZOnhVGQ05U)

### Условие
Обсудить, как кэширование данных может улучшить производительность приложений и какие есть риски.
### Решение кандидата
Кандидат объясняет, что кэширование позволяет быстро получать данные из памяти, что снижает нагрузку на базу данных, но также может привести к проблемам с консистентностью данных.
### Эталонное решение (AI)
Кэширование данных может значительно улучшить производительность, позволяя приложениям быстро получать часто запрашиваемые данные. Однако, это также увеличивает сложность управления данными, так как необходимо следить за их актуальностью и синхронизацией между кэшем и основной базой данных.