# Golden Gallery — 攝影藝廊

黑金主題的啦啦隊與模特兒攝影作品集網站，使用純 HTML + CSS + JavaScript 打造，可直接部署至 GitHub Pages。

## 功能特色

- Masonry 瀑布流照片展示
- 多分類 Tab 切換（全部 / 2024全國賽 / 校園寫真 / 商業拍攝 / 幕後花絮）
- 即時搜尋過濾
- 全螢幕燈箱瀏覽（鍵盤左右鍵導航）
- 響應式設計（手機 / 平板 / 桌機）
- 黑金奢華主題配色
- 無限滾動載入

## 如何自訂照片

編輯 `js/photos.js` 檔案中的 `allPhotos` 陣列，每張照片格式如下：

```javascript
{
  id: 1,
  title: '照片名稱',
  category: 'competition',       // 分類代號（對應 tab data-category）
  categoryLabel: '2024全國賽',    // 顯示的名稱
  url: 'images/your-photo.jpg',  // 照片路徑
  width: 800,
  height: 1200,
  tags: ['啦啦隊', '比賽']       // 搜尋用標籤
}
```

### 分類對照表

| data-category | Tab 名稱 |
|---------------|---------|
| competition   | 2024 全國賽 |
| campus        | 校園寫真 |
| commercial    | 商業拍攝 |
| behind        | 幕後花絮 |

## 部署到 GitHub Pages

1. 建立 GitHub 倉儲
2. 將此資料夾內容 push 到 `main` 分支
3. 到倉儲 Settings → Pages → 選擇 `main` 分支，根目錄
4. 完成，網址為 `https://<帳號>.github.io/<倉儲名稱>/`

## 顏色系統

| 用途 | 色碼 |
|------|------|
| 背景主色 | `#0A0A0A` |
| 次要背景 | `#1A1A1A` |
| 金色主色 | `#D4AF37` |
| 亮金色 | `#FFD700` |

## 授權

© 2025 Golden Gallery
"# cheerleading" 
"# cheerleading" 
