# 123YUK AI Support Agent — PRD

## Maqsad va tekshirilgan holat

**Maqsad:** Zavod ilovasi foydalanuvchilariga 123YUK imkoniyatlari haqida o‘zbekcha, manbaga tayangan yordam berish. O‘lchovlarga faqat backenddagi typed funksiya javob beradi. Sun’iy raqam, taxmin va haqiqiy operatsion ma’lumot ajratib ko‘rsatiladi.

Repo tekshiruvida `zavod/` ichida Zavod sahifalarining HTML shellari va kompilyatsiya qilingan JS/CSS assetlari topildi. Tekshirilgan GitHub Pages manzili `/123yuk-demo/`; Zavod build assetlari `zavod/assets/` ostida. Source frontend, loyihaga tegishli backend, API yoki ishlab chiqarish database aniqlanmadi. Dashboard brauzer DEMO ma’lumotini ko‘rsatadi, lekin bu ma’lumot backendga ulanmagan. Production sxemasi va autentifikatsiya provayderi noma’lum.

## Muammo va mahsulot tamoyili

Foydalanuvchi tizimdagi vazifalar, parking holati yoki navbat haqida savol beradi. Yordamchi faqat tekshirilgan FAQ matni yoki ruxsatli backend natijasini ko‘rsatadi. Demo ma’lumoti dashboard qiymatlariga tenglashtirilmaydi.

## Foydalanuvchi va safarlar

- **Zavod xodimi:** tizimdan foydalanish, parking va navbat hisoblarini so‘raydi.
- **Zavod administratori:** rollar va sozlamalar bo‘yicha yo‘l-yo‘riq izlaydi. Rolga asoslangan bo‘lim ko‘rinishi UI kirish sahifasida hujjatlashtirilgan; serverdagi haqiqiy huquqlar tasdiqlanmagan.
- **Safarlar:** FAQ topish; parking soni va davomiyligini so‘rash; aniq navbatdagi kutayotgan avtomobillar yoki bo‘shashish taxminini so‘rash; aniqlashtirishga javob berish; yordamni vaqtincha to‘xtatib keyin davom ettirish.

## MVP talablari

| ID | Talab | Qabul mezoni |
|---|---|---|
| FR-001 | Widget faqat Zavod HTML sahifalariga ulanadi. | Zavod ichidagi har bir `zavod/**/*.html` sahifasida launcher ko‘pi bilan bir marta bo‘ladi; boshqa ilovalar va mavjud compiled JS/CSS bundle’lar o‘zgarmaydi. |
| FR-002 | Widget Shadow DOM’da ishlaydi, o‘zbekcha, keyboard/accessibility va mobil holatlarni qo‘llaydi. | Open, close, reset, Enter, loading, error, timeout va accessible labels tekshiriladi. |
| FR-003 | Normalizer va o‘zbek lotin sinonimlaridan foydalanadigan lokal intent classifier savolni modelga jo‘natmay aniqlaydi. | Supported intentlar to‘g‘ri ajraladi; noaniq intent aniqlashtirish so‘raydi; tashqi savol exact scope rejection oladi. |
| FR-004 | Noma’lum intent va model chiqishi soha tekshiruvini chetlab o‘tmaydi. | Testlarda faqat explicit allowlisted tools va tanlangan intent uchun mos valid arguments ishlaydi. |
| FR-005 | FAQ faqat tasdiqlangan matn va uning source ID/URI’siga tayanadi. | Tasdiqlanmagan yoki topilmagan manbaga aniq “manbalarda topilmadi” javobi qaytadi. |
| FR-006 | Demo parking soni va navbatdagi kutayotgan mashinalarni alohida hisoblaydi. | Bitta mashina takror hisoblanmaydi; javobda demo provenance bor. |
| FR-007 | Parking o‘rtacha va navbat prognozini deterministic servis hisoblaydi. | Formula, sample, kuzatuv oralig‘i, exclusions, data_as_of va null sababi tekshiriladi. |
| FR-008 | Har navbat alohida jarayon; navbat prognozi shu `factory_id`,`queue_id`,`service_type` oqimidan hisoblanadi. | Boshqa queue/process bilan tezlik aralashtirilganda estimate qaytarilmaydi. |
| FR-009 | `DemoDataAdapter` timezone-aware, o‘zgarmas fixture va boshqariladigan `demo_now` ishlatadi. | Takroriy fixture soat bir xil natija beradi; system clock ishlatilmaydi; snapshot va fixture hodisalari soatni siljitish bilan qayta vaqtlanmaydi. |
| FR-010 | `data_as_of` ga nisbatan 60 daqiqalik kuzatuv va >300 soniya stale qoidasi demo rejimida ham amal qiladi. | 300 soniya yaroqli; 301 soniya va kelajak snapshot forecastni sabab kodi bilan null qiladi. |
| FR-011 | Har demo-data javobi alohida, dashboard bilan sinxron bo‘lmagan backend demo ekanini ochiq ko‘rsatadi. | Status, metrikaning har turi, forecast, FAQ chat envelope va demo-mode capabilities `mode=demo`; demo-data xabari aniq ko‘rinadi. |
| FR-012 | Gemini alohida HTTPX provider adapteridan, faqat operator tasdiqlagan bepul rejimda va allowlisted modelda chaqiriladi. | `GEMINI_FREE_TIER_CONFIRMED=false` yoki API kaliti bo‘sh bo‘lsa zero upstream requests. |
| FR-013 | Gemini’ga tasniflangan intent, public FAQ snippets va ruxsat etilgan nomzod IDlarigina chiqadi. | Xom message, history, private/customer data va tool outputs outbound body/headers/loglarda yo‘q. |
| FR-014 | Provider ishlamasa, o‘chirilgan yoki kvota tugasa lokal FAQ/parking ishlaydi. | Offline provider API FAQ/parking smoke testlari o‘tadi; user-facing API state tushunarli. |
| FR-015 | Readiness kerakli demo componentlariga qaraydi; production integratsiyaga yolg‘on claim berilmaydi. | API contractda demo mode va AI/provider holati farqlanadi. |

## Intent va doira

MVP intentlari: `PARKING_STATUS`, `PARKING_DURATION`, `QUEUE_STATUS`, `QUEUE_FORECAST`, `FAQ_LOOKUP`, `GREETING`, `OUT_OF_SCOPE`, `IN_SCOPE_NOT_FOUND`, `CLARIFICATION_REQUIRED`. Lokal aliases va JSON FAQ index ishlatiladi. Qo‘llab-quvvatlanmagan xulq-atvor taxmin qilinmaydi; model yangi javob matni, function nomi, argument, SQL yoki huquq uydirmaydi. Gemini faqat aniq `FAQ_LOOKUP` intentidagi bir nechta mos public article nomzodidan ID tanlash zarur bo‘lsa chaqiriladi. Aniq FAQ va parking intentlari model ishlatmaydi.

Scope tashqarisidagi javob: **“Men faqat 123YUK tizimi va uning funksiyalari bo‘yicha yordam bera olaman.”**

Scope ichida manba yoki amaliy natija yo‘q bo‘lsa: **“Bu ma’lumot hozircha mavjud manbalarda topilmadi.”**

Noaniq savol aynan topilmagan xabar bilan bir xil emas: aniqlashtirish uchun savol va kerak bo‘lsa `intent_code`/`queue_id` nomzodlari qaytariladi. Qarama-qarshi/taqiqlangan so‘rov mavjud FAQni topish holatida ham ishonchli kontentga aylantirilmaydi.

## Park metrika ta’riflari

- **Parkingdagi avtomobillar soni:** snapshot vaqtida physical parkingda faol bo‘lgan, valid va noyob `vehicle_id` lar.
- **Xizmat navbatida kutish:** faqat shu `queue_id` va `service_type`ga biriktirilgan, bekor qilinmagan va xizmat boshlanmagan unique vehicle sessiyalari.
- **Parking davomiyligi:** oxirgi 24 soatda tugagan valid `exited_at − entered_at` qiymatlarining o‘rtachasi. Musbat yoki nol bo‘lmagan, timezone-aware timestamp; snapshotdan keyingi hodisalar va tugallanmagan sessiyalar chiqariladi. Chiqarilgan yozuvlar soni va namuna soni qaytariladi.
- **Navbat prognozi:** snapshotga nisbatan to‘liq `(data_as_of − 60 min, data_as_of]` oraliqdagi aynan shu jarayonning kelishlari (`queue_join`) va navbatdan xizmat boshlanishlari (`service_start`); `waiting / (start_rate − arrival_rate)`. Kamida 10 valid service start, to‘liq coverage va musbat sof xizmat tezligi talab qilinadi. Bo‘ш navbat `EMPTY_QUEUE`; nomaqbul data alohida reason code; bu holatlarda `estimated_clear_minutes=null`.

`DEMO_NOW` standart `2026-10-10T07:00:00Z`; fixture `data_as_of` ham shu anchor’da alohida, o‘zgarmas `2026-10-10T07:00:00Z`. Konfiguratsiyalangan `demo_now` unga nisbatan oldin bo‘lsa `FUTURE_DATA`. Fixture’ning default loading navbatida `waiting=12`, `arrivals=4/hour`, `service_starts=10/hour`, shu sabab deterministic forecast `120 min`. Bu faqat sun’iy fixture, haqiqiy dashboard raqami yoki statistika emas.

## Non-functional talablar

- Python 3.13, FastAPI, Pydantic v2, HTTPX; pytest/pytest-asyncio, Playwright, ruff va mypy.
- Chat current message max 2,000 Unicode character; history max 12 ta `user`/`assistant` turn, har biri max 2,000; body max 32 KiB.
- CORS faqat `.env` allowlist. Local process fixed-window limit: umumiy API 60/minute/IP, chat 10/minute/IP; single-worker demo cheklovi hujjatlashtiriladi.
- Gemini request timeout 15 s; avtomatik retry va pullik fallback yo‘q. Xatolar structured; raw message va credential log qilinmaydi.
- Demo `.env` Gitdan ignore; `.env.example` da secret placeholder bo‘sh.

## Xavf va dependency

Production identity, factory isolation policy, source-of-truth data source, source timestamps, real queue operational semantics, hosting/API origin va AI Studio key project billing holati aniqlanmagan. `GEMINI_FREE_TIER_CONFIRMED` operator self-attestation bo‘lib, Google billing verification API emas; ulangan active billing project access’ni Paid Services shartlariga o‘tkazishi mumkin. Operator API chaqiruvidan oldin loyiha free tier’da va billing o‘chiq ekanini tekshiradi. Gemini Unpaid Services input/outputni mahsulotlarni yaxshilashda ishlatishi va insonlar ko‘rib chiqishi mumkin; shuning uchun faqat curated public topic/FAQ matni yuboriladi. [Terms](https://ai.google.dev/gemini-api/terms). `gemini-3.5-flash-lite` Standard input/output narxi hozir bepul ko‘rsatilgan, lekin request va token limitlari AI Studio project/account holatiga qarab o‘zgaradi. [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Faza va tayyorlik mezoni

1. Yuqoridagi oltita tasdiqlangan hujjat va verified UI/baseline facts.
2. Typed demo adapter, immutable fixtures, controllable clock, parking/queue metrikalari va unit tests.
3. Normalizer, local intent/scope gate, FAQ search va allowlisted tools.
4. Versioned API, structured errors, CORS, limits, redacted logging.
5. Bepul Gemini adapter + privacy/offline tests.
6. Zavod Web Component, safe injection, direct-route/mobile/browser checks, deployment/rollback docs.

Exit: `GEMINI_FREE_TIER_CONFIRMED=false`da ishlaydigan demo API; UI boshqa joyi o‘zgarmagan; test va type/lint buyruqlari bajarilgan va natijalari rost hisobot qilingan. Go-live uchun alohida production auth, data source, billing-free project, secret va API deployment bloklarini yechish kerak.
