# Cheerleading Gallery — 啦啦隊攝影藝廊

黑金主題的啦啦隊與模特兒攝影作品集網站，使用純 HTML + CSS + JavaScript 打造，部署於 GitHub Pages。大容量相片走 **Cloudinary CDN**，repo 只放網站程式與 `js/photos.js` 中繼資料。

## 功能特色

- Masonry 瀑布流照片展示
- 多分類 Tab 切換（全部 / 2024全國賽 / 校園寫真 / 商業拍攝 / 幕後花絮）
- 即時搜尋過濾
- 全螢幕燈箱瀏覽（鍵盤左右鍵導航）
- 響應式設計（手機 / 平板 / 桌機）
- 黑金奢華主題配色
- 無限滾動載入
- 大圖集最佳化：縮圖 + lightbox 分離、Cloudinary `f_auto,q_auto` 轉檔

## 線上網址

https://pongpongcsp.github.io/cheerleading-gallery/

## 大容量分享流程（推薦）

把大量活動照分享給朋友時，**不要把原圖 commit 進 GitHub**。用這條流水線：

```text
RAW 拍攝
  → cull（挑片）
  → compress（壓成網頁尺寸）
  → upload Cloudinary
  → generate js/photos.js
  → git push（只推 metadata）
```

### 1. 安裝

```bash
npm install
pip install pillow
cp .env.example .env   # 填入 Cloudinary 憑證
```

### 2. 挑片（可選但強烈建議）

```bash
python tools/cull-photos.py "D:/Photo/EVENT" "./culling/EVENT" --copy-keepers
```

打開 `culling/EVENT/culling-report.html` 人工確認後，用 `keepers/`。

### 3. 壓縮

```bash
python tools/compress-photos.py "./culling/EVENT/keepers" "./compressed/EVENT" --quality 85 --max-edge 2000
```

### 4. 上傳 Cloudinary

```bash
node tools/upload-to-cloudinary.js "./compressed/EVENT" "EVENT_FOLDER_NAME"
```

### 5. 登記資料夾對應

編輯 `tools/gallery-folders.json`：

```json
[
  {
    "folder": "EVENT_FOLDER_NAME",
    "category": "competition",
    "categoryLabel": "2024全國賽",
    "titlePrefix": "全國賽",
    "tags": ["啦啦隊", "比賽"]
  }
]
```

### 6. 產生 gallery 資料並上線

```bash
node tools/generate-photos.js
git add js/photos.js tools/gallery-folders.json
git commit -m "Add EVENT photos"
git push
```

Cursor Agent 可用 skills：`photo-culling`、`compress-photo`、`gallery-publish`（在 `.cursor/skills/`）。

## 如何手動自訂照片

編輯 `js/photos.js` 的 `allPhotos` 陣列：

```javascript
{
  id: 1,
  title: '照片名稱',
  category: 'competition',
  categoryLabel: '2024全國賽',
  url: 'https://res.cloudinary.com/.../c_limit,w_2000,f_auto,q_auto/...jpg',
  thumbUrl: 'https://res.cloudinary.com/.../c_limit,w_800,f_auto,q_auto/...jpg',
  width: 800,
  height: 1200,
  tags: ['啦啦隊', '比賽']
}
```

### 分類對照表

| data-category | Tab 名稱 |
|---------------|---------|
| competition   | 2024 全國賽 |
| campus        | 校園寫真 |
| commercial    | 商業拍攝 |
| behind        | 幕後花絮 |

## 相關 repo

| Repo | 用途 |
|------|------|
| [cheerleading-gallery](https://github.com/pongpongcsp/cheerleading-gallery) | 本站：黑金主題，分享給朋友 |
| [photo-website](https://github.com/pongpongcsp/photo-website) | Quiet Frame 作品集；已用 Cloudinary 托管 ~2900 張 |

## 顏色系統

| 用途 | 色碼 |
|------|------|
| 背景主色 | `#0A0A0A` |
| 次要背景 | `#1A1A1A` |
| 金色主色 | `#D4AF37` |
| 亮金色 | `#FFD700` |

## 授權

© 2025 Cheerleading Gallery
