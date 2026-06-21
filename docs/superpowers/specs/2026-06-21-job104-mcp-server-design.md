# 104 Jobs MCP Server — 設計文件

- **日期**: 2026-06-21
- **狀態**: 設計已確認,待寫實作計畫
- **Repo 定位**: 開源,公開於 GitHub,個人/教育用途

## 1. 目標

做一個 MCP server,讓 AI(Claude Desktop / Cursor / Claude Code)能用**人話**查詢 104 人力銀行的職缺,涵蓋關鍵字、地區、薪資、職類、工作型態、遠端、經驗、學歷、排序與分頁等過濾條件。

非目標(YAGNI):投遞履歷、登入帳號、爬取並重新散布資料集、商業化服務、多人 HTTP 部署(架構預留但不在第一版)。

## 2. 核心技術決策(已實測驗證)

### 2.1 資料來源:104 內部 JSON API
直接呼叫 104 網站前端在用的 JSON 端點,**不需要 API key**:

- **搜尋**: `GET https://www.104.com.tw/jobs/search/api/jobs`
  - 已知 query 參數:`keyword`、`area`、`jobcat`、`order`、`page`、`pagesize`、`mode=s`、`jobsource`、`remoteWork`、`s5`(薪資類型)、`isnew` 等
  - 回傳結構化 JSON:`data[]`(職缺陣列)+ `metadata.pagination.total`(總筆數)
- **單一職缺詳情**: `GET https://www.104.com.tw/job/ajax/content/{job_no}`
  - 回傳完整職缺:職務說明、條件要求、福利、聯絡方式、公司資訊

### 2.2 關鍵:用 curl_cffi 通過 Cloudflare bot 偵測
104 整站在 Cloudflare bot 防護後面。**同一條 URL,從瀏覽器打得到 JSON,從一般程式打回 403。**

實測結果(同一條 URL `.../api/jobs?...keyword=軟體主管...&remoteWork=2,1`):

| 方式 | 結果 |
|---|---|
| 一般 `curl` / Python `requests` / `httpx` / Node `fetch` | ❌ 403(Cloudflare "Just a moment" challenge) |
| 舊端點 `/jobs/search/list` | ❌ 403 |
| **`curl_cffi`,`impersonate="chrome"`** → `api/jobs` | ✅ 200,完整 JSON(total 400) |
| **`curl_cffi`,`impersonate="chrome"`** → `job/ajax/content/{id}` | ✅ 200,完整 detail |

原因:Cloudflare 的被動 bot 偵測看的是連線的 **TLS/JA3 指紋、HTTP/2 frame 與 header 順序**,而非網址。一般 HTTP client 的指紋一看就是腳本。`curl_cffi`(底層 curl-impersonate)把這些指紋偽裝成真 Chrome,Cloudflare 因此放行。

**這不是破解或入侵**:資料是公開可瀏覽的職缺,沒有繞過登入或存取非公開後台。但它確實是「偽裝瀏覽器指紋以通過 Cloudflare 的 bot 偵測」,屬於灰色地帶(見第 6 節風險)。

選 `curl_cffi` 而非替代方案的理由:
- 比 headless 瀏覽器(Playwright)輕量、快、無需安裝 Chromium
- 比手動複製 `cf_clearance` cookie 穩定(cookie 會過期)
- 一個套件 + 一行 `impersonate="chrome"` 即可

### 2.3 技術棧
- Python 3.11 + uv(專案/依賴管理)
- FastMCP(`mcp` 套件,decorator 定義 tool)
- `curl_cffi`(HTTP client,Cloudflare 繞過)
- stdio transport(本機,接 Claude Desktop / Cursor / Claude Code)

## 3. 模組架構

每個檔案單一職責,可獨立測試:

```
job104-mcp/
  pyproject.toml
  README.md                    # 含 open-source disclaimer
  LICENSE                      # MIT
  src/job104_mcp/
    client.py    # 用 curl_cffi 打 104 兩個端點,回 raw JSON。集中處理 headers/重試/rate limit/Cloudflare
    codes.py     # 載入內建代碼表 + 名稱↔代碼模糊比對
    models.py    # 把 raw JSON 收斂成乾淨 dataclass(只留有用欄位),容錯
    server.py    # FastMCP tool 定義,組合上述三者
    data/
      jobcat.json  # 職類代碼表
      area.json    # 地區代碼表
  scripts/
    fetch_codes.py  # 重抓代碼表的腳本(不把爬下來的資料當主要產物 commit)
  tests/
    test_codes.py    # 純單元測試,不碰網路
    test_models.py   # 用真實 JSON fixture,不碰網路
    test_client.py   # @pytest.mark.live,真打 104,平常 skip
    fixtures/        # 真實 JSON 樣本(搜尋 + detail 各一,去識別化)
```

職責邊界:
- `client.py` 對外打 API,是唯一碰網路與 Cloudflare 的地方;104 改端點時只改這裡
- `codes.py` 的名稱→代碼比對純邏輯,可離線測試
- `models.py` 把 110KB raw JSON 收斂成精簡結構,用 `.get()` 容錯
- `server.py` 只做組裝,不含商業邏輯

## 4. MCP Tools 介面

對外暴露 3 個 tool,參數一律用人類可讀值,內部自動轉 104 代碼。

### 4.1 `search_jobs` — 主力查詢
```python
search_jobs(
    keyword: str = "",            # 關鍵字
    area: list[str] = [],         # 地區名稱,如 ["台北市","新竹市"] → 自動轉 area 代碼
    jobcat: list[str] = [],       # 職類名稱,如 ["軟體工程師"] → 自動轉 jobcat 代碼
    salary_min: int | None = None,# 月薪下限(對應 104 薪資級距)
    job_type: str | None = None,  # 全職/兼職/高階/派遣/接案
    remote: bool | None = None,   # 只看遠端
    is_new: bool = False,         # 只看近期新職缺
    exp_years: int | None = None, # 需要年資上限
    edu: str | None = None,       # 學歷:高中/專科/大學/碩士...
    sort: str = "relevance",      # relevance | date | salary
    page: int = 1,
    page_size: int = 20,
) -> SearchResult
```

回傳精簡結果(非原始 110KB),每筆只留:
`job_no, job_name, company, salary(文字化:"月薪 4-6萬"/"面議"), location, job_type, remote, applied_count, description_snippet, url, appear_date`

外加 `total`、`page`、`has_next`,讓 AI 判斷是否翻頁深挖。

### 4.2 `get_job_detail` — 單一職缺完整內容
```python
get_job_detail(job_no: str) -> JobDetail
```
打 `job/ajax/content/{job_no}`,回完整職務說明、條件要求、福利、聯絡方式、公司資訊。

### 4.3 `lookup_code` — 代碼查詢(安全網)
```python
lookup_code(kind: str, query: str) -> list[{name, code}]
```
`kind` = `"jobcat"` | `"area"`。平常 AI 不需主動呼叫(`search_jobs` 已內建模糊比對),用於模糊/歧義情況的確認。

設計重點:代碼表對 AI 隱形。AI 講「台北的遠端 Python 後端,月薪 5 萬以上」,`search_jobs` 內部完成 `台北→area碼`、`Python 後端→jobcat碼 + keyword`。

## 5. 資料流與錯誤處理

### 資料流(一次 search_jobs)
```
AI 講人話
 → server.py 收參數
 → codes.py 把 area/jobcat 名稱模糊比對成代碼(查不到 → 回明確錯誤讓 AI 自我修正)
 → client.py 組 query,curl_cffi(impersonate=chrome)打 api/jobs
 → models.py 收斂成精簡 dataclass
 → 回傳 AI
```

### 錯誤處理(每種失敗都回 AI 可行動的訊息)
| 情況 | 處理 |
|---|---|
| Cloudflare 偶發擋下(403 / challenge HTML) | client 重試 2 次(換 impersonate 版本),仍失敗回「104 暫時拒絕存取,請稍後再試」 |
| 代碼查無對應 | 回「找不到地區 'XXX',你是不是指:台北市/新北市?」附近似選項 |
| 查無職缺 | 正常回 `total: 0`,非錯誤 |
| 網路逾時 | timeout 20s,回明確逾時訊息 |
| 104 改 JSON 結構 | models.py 用 `.get()` 容錯,缺欄位回 `None` 不 crash |

### Rate limit
client 內建基本節流(每次查詢間最小間隔),避免被當爬蟲、避免 ban IP。

## 6. 風險與邊界(開源公開定位)

整體風險「低但非零」,屬民事/平台層面而非刑事。GitHub 已有多個公開 104 爬蟲先例。

緩解措施(寫入 repo):
1. **不 commit 爬下來的職缺資料**。代碼表(jobcat/area)用 `scripts/fetch_codes.py` 生成,職缺內容只即時查詢轉發,不重新散布成資料庫。
2. **商標**:repo 名用純文字 `job104-mcp`,不使用 104 logo/品牌圖,README 明確 "Not affiliated with 104 Corporation"。
3. **Disclaimer**:README 標明 educational / personal-use,提醒使用者尊重 104 ToS 與合理使用頻率。
4. **內建 rate limit**,不鼓勵高頻存取。
5. **MIT license**,as-is no warranty。
6. 心理準備:極低機率收到 GitHub 下架請求,真收到即配合下架,無後續責任。

技術變動風險:
- 104 改 API 路徑或 Cloudflare 升級規則 → 需更新 `client.py`(集中於單一檔案)。
- jobcat/area 代碼偶有增修 → 用 `fetch_codes.py` 重抓。

## 7. 測試策略(TDD)
- `test_codes.py`:名稱→代碼模糊比對,純單元測試,不碰網路。
- `test_models.py`:餵真實 JSON fixture(搜尋 + detail),驗證收斂正確,不碰網路。
- `test_client.py`:`@pytest.mark.live` 整合測試,真打 104,平常 skip,手動驗證用。
- `server.py`:用 mock 的 client/codes 驗證 tool 組裝。

## 8. 開放問題 / 待實作時確認
- `search_jobs` 各參數對應的確切 104 query 參數名與值(`s5` 薪資級距、`edu`/`exp` 對應碼、`job_type` 對應 `jobsource`/`mode` 等)— 實作時對照真實請求確認。
- jobcat/area 完整代碼表的抓取來源(104 提供的代碼 API 或前端 bundle)。
