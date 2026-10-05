/* 中英双语：window.__lang = 'zh' | 'en'（存在 localStorage 'dgy-lang'）。
   - T(中文) → 当前语言的文字（查 I18N 表，查不到原样返回）
   - applyLang(root)：把 root 下界面文字节点与 aria-label / title / placeholder 换成当前语言（记住原中文，可来回切）
   - setLang(l)：切换并广播 window 事件 'dgy-lang'（index.html、game.js 各自重绘动态内容）
   园中匾额、对联、画上题字属于场景本身，始终保留中文。 */
(function () {
  let lang = 'zh';
  try { lang = localStorage.getItem('dgy-lang') || (/^zh/i.test(navigator.language || 'zh') ? 'zh' : 'en'); } catch (e) {}
  window.__lang = lang === 'en' ? 'en' : 'zh';
  const I18N = {
    '大观园': 'Grand View Garden', '《红楼梦》省亲别墅 · 全园漫游': 'Dream of the Red Chamber · The whole garden, on foot',
    '景点': 'Places', '收起说明': 'Close', '进馆细看 →': 'Look inside →', '时辰': 'Time of day',
    '步行': 'Walk', '步行 (F)': 'Walk (F)', '季节': 'Season', '春': 'Spr', '夏': 'Sum', '秋': 'Aut', '冬': 'Win',
    '声音': 'Sound', '声音 (M)': 'Sound (M)', '漫游': 'Tour', '设置': 'Settings', '设置 (H)': 'Settings (H)',
    '画质': 'Quality', '低': 'Low', '中': 'Med', '高': 'High', '时辰流转': 'Time flows', '关': 'Off', '开': 'On',
    '渲染比例': 'Render scale', '帧率': 'Frame rate', '雾气': 'Mist', '画风': 'Look', '梦幻': 'Dreamy', '写实': 'Realistic',
    '题签': 'Name tags', '语言': 'Language',
    // 设置里的按键说明（按文字片段替换）
    '步行 ·': 'walk ·', '前行 ·': 'move ·', '快走 ·': 'run ·', '空格': 'Space', '跳 ·': 'jump ·', '第一/第三人称 · 滚轮 镜头远近 ·': 'first / third person · wheel: zoom ·',
    '退出': 'exit', '声音 ·': 'sound ·', '时辰流转 ·': 'time flows ·', '拍照（隐藏界面） ·': 'photo (hide UI) ·', '设置': 'Settings',
    '渲染手法参考': 'Rendering approach after', '（MIT）：高度雾、ACES 调色、叶簇树冠、草地分层淡出、步行碰撞。园中声音全部由程序实时合成。布局依原著描写示意，并非实测复原。':
      ' (MIT): height fog, ACES grading, clustered tree crowns, layered grass fade-out, walking collision. All sounds in the garden are synthesized live. The layout follows the novel’s descriptions; it is an illustration, not a surveyed reconstruction.',
    '拖动旋转 · 滚轮缩放 ·': 'Drag to rotate · wheel to zoom ·', '步行 · ': 'walk · ',
    'WASD 行走 · Shift 快走 · 鼠标转头 · Esc 退出': 'WASD walk · Shift run · mouse to look · Esc exit',
    '琉璃世界': 'A World of Glass', '白雪红梅 · 第四十九回': 'White snow, red plum · Chapter 49',
    '正在营造大观园': 'Building the Grand View Garden', '备料': 'Gathering materials',
    '三维库加载得比较慢': 'The 3D library is loading slowly', '请检查网络，或稍后刷新页面': 'Check your connection, or refresh in a moment',
    '堆山凿池': 'Raising hills, digging pools', '铺石子路，架桥': 'Laying pebble paths, building bridges', '起楼阁，砌粉墙': 'Raising halls, plastering walls',
    '修馆舍，筑茅屋': 'Building lodges and thatched cottages', '种树栽竹，植荷，叠驳岸': 'Planting trees, bamboo and lotus; piling the banks',
    '搬入楼阁精模': 'Moving in the detailed buildings', '上瓦挂匾': 'Tiling roofs, hanging plaques', '铺草': 'Laying grass',
    '点野花，种蕨草': 'Scattering wildflowers and ferns', '调天光': 'Tuning the light',
    '左下摇杆前行 · 右侧拖动转视角 · 再点“步行”退出': 'Left stick to move · drag on the right to look · tap "Walk" again to exit',
    'WASD 前行 · 鼠标转视角 · 滚轮远近 · Shift 快走 · 空格 跳 · V 第一人称 · K 存图 · Esc 退出': 'WASD move · mouse to look · wheel to zoom · Shift run · Space jump · V first person · K save image · Esc exit',
    'WASD 前行 · 鼠标转头 · Shift 快走 · 空格 跳 · V 第三人称 · K 存图 · Esc 退出': 'WASD move · mouse to look · Shift run · Space jump · V third person · K save image · Esc exit',
    '点击画面继续 · Esc 退出步行': 'Click to continue · Esc to stop walking', '已存图': 'Image saved', '在浏览器的下载里': 'In your browser downloads', '存图 ·': 'save image ·',
    '前往': 'Go to', '见《红楼梦》': 'See Dream of the Red Chamber, ', '第二十三回': 'Chapter 23',
    '春夜即事': 'A Spring Night', '夏夜即事': 'A Summer Night', '秋夜即事': 'An Autumn Night', '冬夜即事': 'A Winter Night',
    '霞绡云幄任铺陈，隔巷蟆更听未真': 'Rosy gauze and cloudy curtains spread at will; the watchman’s clapper beyond the lane is faint',
    '倦绣佳人幽梦长，金笼鹦鹉唤茶汤': 'Weary of embroidery, the beauty dreams long; the parrot in its golden cage calls for tea',
    '绛芸轩里绝喧哗，桂魄流光浸茜纱': 'All noise is hushed in Crimson Rue Studio; the cassia moon soaks the madder gauze',
    '梅魂竹梦已三更，锦罽鹴衾睡未成': 'Plum souls and bamboo dreams at the third watch; under brocade quilts, sleep will not come',
  };
  const ZH_HOURS = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
  const EN_HOURS = ['Rat', 'Ox', 'Tiger', 'Rabbit', 'Dragon', 'Snake', 'Horse', 'Goat', 'Monkey', 'Rooster', 'Dog', 'Pig'];
  window.I18N = I18N;
  window.T = (s) => (window.__lang === 'en' && I18N[s] != null) ? I18N[s] : s;
  window.tr = window.T;
  window.hourName = (i) => window.__lang === 'en' ? EN_HOURS[i] + ' hr' : ZH_HOURS[i] + '时';
  const ATTRS = ['aria-label', 'title', 'placeholder'];
  function swapText(n) {
    if (n.__zh == null) { if (!/[一-鿿]/.test(n.nodeValue)) return; n.__zh = n.nodeValue; }
    const zh = n.__zh, core = zh.trim();
    if (window.__lang !== 'en') { n.nodeValue = zh; return; }
    const en = I18N[core];
    if (en != null) n.nodeValue = zh.replace(core, en);
  }
  window.applyLang = function (root) {
    root = root || document.body;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => n.parentElement && n.parentElement.closest('[data-noi18n],script,style,canvas') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    let n; while ((n = w.nextNode())) swapText(n);
    root.querySelectorAll('*').forEach((el) => {
      if (el.closest('[data-noi18n]')) return;
      for (const a of ATTRS) {
        if (!el.hasAttribute(a)) continue;
        const k = '__zh_' + a; if (el[k] == null) { const v = el.getAttribute(a); if (!/[一-鿿]/.test(v)) continue; el[k] = v; }
        el.setAttribute(a, window.__lang === 'en' ? (I18N[el[k]] ?? el[k]) : el[k]);
      }
    });
    document.documentElement.lang = window.__lang === 'en' ? 'en' : 'zh-CN';
    document.title = window.__lang === 'en' ? 'Grand View Garden' : '大观园';
  };
  window.setLang = function (l) {
    window.__lang = l === 'en' ? 'en' : 'zh';
    try { localStorage.setItem('dgy-lang', window.__lang); } catch (e) {}
    window.applyLang(document.body);
    window.dispatchEvent(new Event('dgy-lang'));
  };
  document.addEventListener('DOMContentLoaded', () => window.applyLang(document.body));
})();
