# 123YUK AI Support Agent — data dictionary

**Muhim farq:** bu fayl production schema’ni tasvirlamaydi. Faqat tekshirilgan demo UI va assistent uchun taklif etilgan sun’iy read-only modelni hujjatlashtiradi.

## Tasdiqlangan repo/UI faktlari

| UI fakt | Repo asos | Cheklov |
|---|---|---|
| Zavod static route’lari `zavod/.../index.html`, production build JS/CSS `zavod/assets/`da | GitHub Pages daraxti va build HTML | Original source/prod API aniqlanmadi |
| `/123yuk-demo/` GitHub Pages project path | `zavod/dashboard/index.html` asset/favicons | API server URL noma’lum |
| Boshqaruv panelida DEMO belgisi va “Parkingda — shahar/viloyat” summary bor | Deployed `/zavod/dashboard` DOM/screenshot | DOMdagi sonlar faqat Zavod brauzeri demo seedidan; backend bilan sinxron emas |
| Menyuda “Navbat matritsasi”, “Rollar”, dashboard/queue operations bor | Compiled `zavod/assets/index-CCddAlX0.js`, visible nav | Bu ishlab chiqarish ruxsati, arifmetika yoki API sxemasi degani emas |
| Kirish sahifasida xodim faqat o‘z roliga ruxsat etilgan bo‘limni ko‘rishi, administrator rol belgilashi haqida matn bor | Verified demo Zavod `/zavod/login` UI | Yordamchi authenticated user yoki rolni serverdan tekshirmaydi |
| Bundle’dagi order timestamps `arrivedAtParkingAt`, `enteredLoadingAt`, `departedLoadingAt` kabi nomlardan foydalanadi | Compiled `zavod` bundle excerpts | Bu browser demo internal field; server production field/schema emas va AI tool’da ishlatilmaydi |

Backend model, endpoint, `factory_id`, vehicle identifier, queue ID va snapshot timestamplar quyida **proposal**. Ular production tasdiqlangan maydon deb talqin qilinmaydi.

## Sun’iy backend fixture modeli (proposal)

### `ParkingSession`

| Maydon | Demo turi | Ma’no/validatsiya |
|---|---|---|
| `session_id` | `str` | Fixture’dagi noyob sessiya ID |
| `factory_id` | `str` enum | Sun’iy demo factory scope; client tomonidan qabul qilinmaydi |
| `vehicle_id` | `str` enum | Sun’iy pseudonymous ID; davlat raqami/ism/telefon yo‘q |
| `entered_at` | aware `datetime` UTC | Parkingga kirish instant |
| `exited_at` | `datetime | null` | Chiqish; null = snapshotdagi active. Exit ≥ entry va exit ≤ snapshot |

Parking count snapshotda active valid sessiyalarni unique `vehicle_id` bo‘yicha sanaydi. Duplicate same-vehicle activity deterministik ravishda bittaga sanaladi va chiqarilgan record hisobiga kiradi. Production’da bunday merge real source qoidalariga bog‘liq.

### `QueueTicket` va `QueueEvent`

| Maydon | Demo turi | Ma’no/validatsiya |
|---|---|---|
| `ticket_id` / `event_id` | `str` | Noyob synthetic ID; duplicate event bir marta |
| `factory_id` | demo enum | Bir site konteksti; client-controlled emas |
| `queue_id` | `loading|unloading|other` | Alohida xizmat jarayoni; mustaqil hisoblash partition’i |
| `service_type` | `loading|unloading|other` | Bitta queue’ning operational meaning |
| `vehicle_id` | `str` enum | Sun’iy vehicle ID; null/PII yo‘q |
| `queue_joined_at` | UTC datetime | Queue arrival instant |
| `service_started_at` | UTC datetime or null | Waitingdan chiqarish; ≥ join, ≤ snapshot |
| `cancelled_at` | UTC datetime or null | Canceled session; cancelled ticket waiting countga qo‘shilmaydi |

`QueueEvent` turlari `queue_join`, `service_start`; har `event` ichida `event_id`, `factory_id`, `queue_id`, `service_type`, `vehicle_id`, `occurred_at`. Process/FK partition mosligi majburiy. Fixture session jadvallari kross-tekshirilib arrival ≤ service_start va service_start ≤ data_as_of.

Active queue count: snapshotda valid, canceled bo‘lmagan, `service_started_at=null` unique vehicle. Bir vehicle bir queue’da bir martadan ortiq valid waiting ticketga ega bo‘lsa, ambiguous state prognozni `INCONSISTENT_DATA` qiladi.

### `DemoSnapshot` / controllable clock

| Maydon | Tip | Ma’no |
|---|---|---|
| `demo_now` | timezone-aware `datetime` UTC | O‘zgarmas application/test clock; default `2026-10-10T07:00:00Z` |
| `data_as_of` | timezone-aware `datetime` UTC | Fixture snapshot instant; alohida, immutable default `2026-10-10T07:00:00Z` |
| `coverage_start`, `coverage_end` | UTC datetimes | Tarix uzluksiz to‘liq kuzatilgan bounds |
| `parking_sessions` | `tuple[ParkingSession, ...]` | Immutable fixture records |
| `queue_tickets/events` | tuple of typed records | Immutable fixture state/history |
| `source` | literal `demo_snapshot` | Har metric/queue provenance marker |

Env `DEMO_NOW` timezone/offsetsiz bo‘lsa config startup’da fail-closed. Testlar adapterga to‘g‘ridan-to‘g‘ri UTC fixture/clock inject qiladi. `data_as_of` fixture qiymati config clock’dan derive qilinmaydi. `0≤demo_now−data_as_of≤300s` fresh, `>300s` stale, `data_as_of>demo_now` future. Soatni mijoz body/query orqali o‘zgartira olmaydi.

## Derived fields va vaqt qoidalari

| Output | Qoidalar |
|---|---|
| `active_parking_vehicle_count` | Snapshot vaqtida parkingda active valid unique vehicle |
| `waiting_vehicle_count` | Bitta queue uchun waiting, non-canceled unique vehicle |
| parking `average_minutes` | Exit > `as_of−24h`, exit ≤ `data_as_of`, valid entry/exit; `sum(exit-entry)/count`; empty => null |
| rate window | `(data_as_of−60m, data_as_of]`; arriving `queue_join`, departing wait queue `service_start`; per factory+queue+service only |
| `arrival_rate_per_hour` | valid arrivals / covered hours |
| `service_start_rate_per_hour` | valid service_start / same covered hours |
| `net_service_rate` | service-start rate − same-queue arrival rate; never sum different queue rates |
| `estimated_clear_minutes` | waiting / net rate × 60; requires ≥10 starts, full coverage, fresh snapshot, consistent process, net rate >0. Never average parking duration. |

Invalid/excluded counts are separate. Invalid includes duplicate IDs, naive/inverted/inconsistent timestamps, event after `data_as_of`, wrong factory/queue/service type and multiple concurrent active tickets for one vehicle. Late/future events are not silently admitted to the observation window.

## Manba va ishonch

Assistant evidence sources are strictly one of curated public `documentation`, synthetic adapter `demo_snapshot`, or `none`. Provider outputs are not a source. Real source types, real fields, actual timezone and real queue semantics remain unconfirmed; a verified backend/API and read-only auth/data contract are required before production fields may be added.
