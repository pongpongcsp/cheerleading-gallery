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
- 大圖集最佳化：每場挑約 50 張 → 縮圖 + lightbox、Cloudinary `f_auto,q_auto`

## 線上網址

https://pongpongcsp.github.io/cheerleading-gallery/

## 大容量分享流程（推薦 · Cursor Desktop）

不要把原圖 commit 進 GitHub。在 **Windows PC**（可讀 `D:\Photo\...`）跑：

```text
D:\Photo\<event>
  → cull（每場最多 ~50 keepers）
  → compress（q85 / max-edge 2000）
  → upload Cloudinary
  → generate js/photos.js
  → git push（只推 metadata）
```

### 1. 安裝

```bash
npm install
pip install pillow
copy .env.example .env
REM 填入 Cloudinary 憑證
```

### 2. 一次處理全部 9 場（推薦）

活動清單在 [`tools/gallery-folders.json`](tools/gallery-folders.json)。

```bat
publish-all.bat
```

或：

```bash
node tools/publish-events.js --max-keepers 50
```

常用參數：

```bat
publish-all.bat --skip-upload
publish-all.bat --only 20250928_桃園_樂天女孩
publish-all.bat --photo-root "D:\Photo"
```

預算：目前先跑 **8 場** × ~50 ≈ **400** 張（`PassionSister` 已設 `skip: true`，之後再跑）。

### 3. 單場

```bat
publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩" 50
```

### 4. 人工確認後上線

打開每個 `culling\<folder>\culling-report.html` 看 keepers，然後：

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
