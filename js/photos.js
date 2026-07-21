const allPhotos = [
  // ── 2024 全國賽 ──
  { id: 1,  title: '全國賽 — 開場演出',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer1/800/1000', width: 800, height: 1000, tags: ['啦啦隊', '比賽'] },
  { id: 2,  title: '全國賽 — 團體技巧',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer2/800/1200', width: 800, height: 1200, tags: ['啦啦隊', '比賽'] },
  { id: 3,  title: '全國賽 — 金字塔組合', category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer3/800/900',  width: 800, height: 900,  tags: ['啦啦隊', '比賽'] },
  { id: 4,  title: '全國賽 — 頒獎時刻',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer4/800/1100', width: 800, height: 1100, tags: ['啦啦隊', '頒獎'] },
  { id: 5,  title: '全國賽 — 彩球舞蹈',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer5/800/950',  width: 800, height: 950,  tags: ['啦啦隊', '舞蹈'] },
  { id: 6,  title: '全國賽 — 隊服寫真',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer6/800/1050', width: 800, height: 1050, tags: ['啦啦隊', '服裝'] },

  // ── 校園寫真 ──
  { id: 7,  title: '校園 — 陽光操場',     category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus1/800/1200', width: 800, height: 1200, tags: ['校園', '陽光'] },
  { id: 8,  title: '校園 — 圖書館一角',   category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus2/800/800',  width: 800, height: 800,  tags: ['校園', '氣質'] },
  { id: 9,  title: '校園 — 球場邊',       category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus3/800/1100', width: 800, height: 1100, tags: ['校園', '運動'] },
  { id: 10, title: '校園 — 教室肖像',     category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus4/800/950',  width: 800, height: 950,  tags: ['校園', '教室'] },
  { id: 11, title: '校園 — 樹蔭下',       category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus5/800/1000', width: 800, height: 1000, tags: ['校園', '自然'] },
  { id: 12, title: '校園 — 走廊回眸',     category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus6/800/850',  width: 800, height: 850,  tags: ['校園', '時尚'] },

  // ── 商業拍攝 ──
  { id: 13, title: '商業 — 棚拍時尚',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com1/800/1100', width: 800, height: 1100, tags: ['商業', '時尚'] },
  { id: 14, title: '商業 — 品牌代言',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com2/800/950',  width: 800, height: 950,  tags: ['商業', '代言'] },
  { id: 15, title: '商業 — 街頭風格',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com3/800/1000', width: 800, height: 1000, tags: ['商業', '街頭'] },
  { id: 16, title: '商業 — 黑白寫真',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com4/800/1200', width: 800, height: 1200, tags: ['商業', '黑白'] },
  { id: 17, title: '商業 — 香水系列',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com5/800/900',  width: 800, height: 900,  tags: ['商業', '質感'] },
  { id: 18, title: '商業 — 運動品牌',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com6/800/1050', width: 800, height: 1050, tags: ['商業', '運動'] },

  // ── 幕後花絮 ──
  { id: 19, title: '幕後 — 化妝準備',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind1/800/900',  width: 800, height: 900,  tags: ['幕後', '化妝'] },
  { id: 20, title: '幕後 — 排練花絮',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind2/800/1100', width: 800, height: 1100, tags: ['幕後', '排練'] },
  { id: 21, title: '幕後 — 休息時刻',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind3/800/800',  width: 800, height: 800,  tags: ['幕後', '日常'] },
  { id: 22, title: '幕後 — 攝影師視角',   category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind4/800/1000', width: 800, height: 1000, tags: ['幕後', '拍攝'] },
  { id: 23, title: '幕後 — 服裝調整',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind5/800/950',  width: 800, height: 950,  tags: ['幕後', '服裝'] },
  { id: 24, title: '幕後 — 歡笑瞬間',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind6/800/1050', width: 800, height: 1050, tags: ['幕後', '歡樂'] },

  // ── 更多混合內容 ──
  { id: 25, title: '舞台 — 聚光燈下',     category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/stage1/800/1150', width: 800, height: 1150, tags: ['舞台', '比賽'] },
  { id: 26, title: '校園 — 畢業紀念',     category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus7/800/900',  width: 800, height: 900,  tags: ['校園', '畢業'] },
  { id: 27, title: '商業 — 飾品特寫',     category: 'commercial', categoryLabel: '商業拍攝', url: 'https://picsum.photos/seed/com7/800/1000', width: 800, height: 1000, tags: ['商業', '飾品'] },
  { id: 28, title: '幕後 — 道具準備',     category: 'behind', categoryLabel: '幕後花絮', url: 'https://picsum.photos/seed/behind7/800/1100', width: 800, height: 1100, tags: ['幕後', '道具'] },
  { id: 29, title: '全國賽 — 謝幕合影',   category: 'competition', categoryLabel: '2024全國賽', url: 'https://picsum.photos/seed/cheer7/800/850',  width: 800, height: 850,  tags: ['啦啦隊', '謝幕'] },
  { id: 30, title: '校園 — 社團宣傳',     category: 'campus', categoryLabel: '校園寫真', url: 'https://picsum.photos/seed/campus8/800/1050', width: 800, height: 1050, tags: ['校園', '社團'] },
];
