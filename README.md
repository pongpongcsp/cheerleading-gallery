# Cheerleading Gallery — 啦啦隊攝影藝廊

黑金主題的啦啦隊與模特兒攝影作品集網站，使用純 HTML + CSS + JavaScript 打造，部署於 GitHub Pages。大容量相片走 **Cloudinary CDN**，repo 只放網站程式與 `js/photos.js` 中繼資料。

## 功能特色

- Masonry 瀑布流照片展示
- 多活動 Tab 切換（9 個已確認場次 + 全部）
- 即時搜尋過濾
- 全螢幕燈箱瀏覽（鍵盤左右鍵導航）
- 響應式設計（手機 / 平板 / 桌機）
- 黑金奢華主題配色
- 無限滾動載入
- 大圖集最佳化：PixCull 離線 AI 選片（keep → keepers）→ 縮圖 + lightbox、Cloudinary `f_auto,q_auto`

## 線上網址

https://pongpongcsp.github.io/cheerleading-gallery/

## 大容量分享流程（推薦 · Cursor Desktop）

不要把原圖 commit 進 GitHub。在 **Windows PC**（可讀 `D:\Photo\...`）跑：

```text
D:\Photo\<event>
  → cull（PixCull offline CLI，預設不設硬上限）
  → manual confirm（看 culling-report.html，必要時改 keepers/）
  → compress（q85 / max-edge 2000）
  → upload Cloudinary
  → generate js/photos.js
  → git push（只推 metadata）
```

### 1. 安裝

需要 **Python 3.11 或 3.12**（PixCull 不支援 3.13+）。建議專案 venv：

```bash
npm install
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
REM 填入 Cloudinary 憑證
```

`requirements.txt` 從 GitHub 安裝 PixCull（尚未穩定上 PyPI）。首次 `pixcull run` 會下載本機模型到 `~/.pixcull`。Gallery publish 只用離線 CLI，不要跑 `pixcull serve` / LAN / DeepSeek。Windows 上若 YAML 編碼出錯，請設 `PYTHONUTF8=1`（adapter 已自動設定）。

### 2. 一次處理全部 9 場（推薦）

活動清單在 [`tools/gallery-folders.json`](tools/gallery-folders.json)。

```bat
publish-all.bat
```

或：

```bash
node tools/publish-events.js
```

常用參數：

```bat
publish-all.bat --skip-upload
publish-all.bat --skip-confirm
publish-all.bat --only 20250928_桃園_樂天女孩
publish-all.bat --photo-root "D:\Photo"
```

預設 **不設硬上限**（PixCull `keep` → keepers；`maybe`/`cull` 不進上傳）。每場 cull 完會 **暫停人工確認**（開報告、可刪 keepers 內不要的檔），確認後才 compress。自動化可加 `--skip-confirm`。Cloudinary 用量隨 keepers 增加；可選 `--max-keepers N` 強制上限。

### 3. 單場

```bat
publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩"
```

### 4. 人工確認後上線

Pipeline 已在 cull 後暫停確認。全部上傳完成後：

```bash
git add js/photos.js tools/gallery-folders.json index.html
git commit -m "Publish culled event galleries"
git push
```

Cursor skills：`photo-culling`、`compress-photo`、`gallery-publish`。

## 已確認場次

| folder | Tab |
|--------|-----|
| 20250809_台北南港_TRE | 南港 TRE |
| 20250810_台北大巨蛋_樂天女孩 | 大巨蛋 樂天女孩 08/10 |
| 20250824_電腦節_樂天女孩 | 電腦節 樂天女孩 |
| 20250928_桃園_樂天女孩 | 桃園 樂天女孩 |
| 20260328_台北大巨蛋_樂天女孩 | 大巨蛋 樂天女孩 03/28 |
| 20260329_台北大巨蛋_樂天女孩 | 大巨蛋 樂天女孩 03/29 |
| 20260606_台中洲際_PassionSister | 台中 PassionSister |
| 20260607_台北大巨蛋_UniGirls | 大巨蛋 UniGirls |
| 20260607_台北南港_金佳垠 | 南港 金佳垠 |
| 20260704_台中洲際_PassionSister | 台中 PassionSister 07/04 |
| 20260705_台北南港_TRE | 南港 TRE 07/05 |
| 20260731_新北新莊_FubonAngel | 新莊 Fubon Angels 07/31 |
| 20260801_台北大巨蛋_DragonBeauties | 大巨蛋 Dragon Beauties 08/01 |
| 20260802_新北新莊_FubonAngel | 新莊 Fubon Angels 08/02 |
| 20260815_台中新光三越_金泰希 | 台中 金泰希 |
| 20260815_台中洲際_PassionSister | 台中 PassionSister 08/15 |
| 20260816_台北大巨蛋_DragonBeauties | 大巨蛋 Dragon Beauties 08/16 |
| 20260823_電腦節_FubonAngel | 電腦節 Fubon Angels |
| 20260823_電腦節_小迪 | 電腦節 小迪 |

## 相關 repo

| Repo | 用途 |
|------|------|
| [cheerleading-gallery](https://github.com/pongpongcsp/cheerleading-gallery) | 本站：黑金主題，分享給朋友 |
| [photo-website](https://github.com/pongpongcsp/photo-website) | Quiet Frame 作品集 |

## 顏色系統

| 用途 | 色碼 |
|------|------|
| 背景主色 | `#0A0A0A` |
| 次要背景 | `#1A1A1A` |
| 金色主色 | `#D4AF37` |
| 亮金色 | `#FFD700` |

## 授權

© 2025 Cheerleading Gallery
