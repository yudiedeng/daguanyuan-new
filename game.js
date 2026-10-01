/* =====================================================================
   我们的大观园 · 赠礼玩法
   选一个人入园 → 心事 → 寻物 → 送礼 → 原著片段揭示 → 赠一份礼给现实中的人
   依赖主页面暴露的 window.__dgy
   ===================================================================== */
const wait = () => new Promise(r => { const t = () => window.__dgy && window.__DGY_OK ? r(window.__dgy) : setTimeout(t, 200); t(); });
const D = await wait();
const { THREE, scene, hero, walk, blockedAt, groundAt, setSeason, applyTime, enterWalk, exitWalk, camera, PLACES, isTouch, hourEl } = D;
const V3 = THREE.Vector3;

/* ---------------------------------------------------------------------
   人物与心事（全部取自原著；诗句为原文，其余为转述）
   --------------------------------------------------------------------- */
const CHARS = {
  baoyu: {
    name: '贾宝玉', short: '宝玉', home: '怡红院', start: 'yihong', season: 1, hour: 16,
    look: { robe: '#a8342b', robe2: '#8b2b24', sash: '#c9a24a', crown: true },
    line: '衔玉而生，住怡红院。心里装着一园子的姊妹。',
    quests: [
      {
        title: '两条旧帕', at: [1, 16], want: '挨打后养伤，想让林妹妹放心。',
        pick: { place: 'yihong', kind: 'item', item: 'pa', label: '两条旧帕子', verb: '取出', tip: '先在怡红院找到那两条半新不旧的帕子。' },
        give: { place: 'xiaoxiang', who: '林黛玉', color: '#b9c9b4', verb: '送给', tip: '把帕子送到潇湘馆，交给林妹妹。' },
        reveal: {
          title: '题帕三绝', ch: '第三十四回 · 情中情因情感妹妹',
          poem: ['眼空蓄泪泪空垂，暗洒闲抛却为谁？', '尺幅鲛绡劳解赠，叫人焉得不伤悲！'],
          prose: '原著里是宝玉打发晴雯送去的，不带一句话。黛玉体贴出帕子的意思，又喜又悲，研墨蘸笔，在两块旧帕上一连写了三首绝句。',
          hour: 20.5
        }
      },
      {
        title: '乞红梅', at: [3, 10.5], want: '芦雪庵联诗落了第，社长李纨罚你去栊翠庵讨一枝红梅。',
        pick: { place: 'longcui', kind: 'npc', who: '妙玉', color: '#d8d2c4', item: 'mei', label: '一枝红梅', verb: '向妙玉讨', tip: '去栊翠庵，向妙玉讨一枝红梅。' },
        give: { place: 'daoxiang', who: '李纨', color: '#8e8a80', verb: '交给', tip: '把红梅带回去交给李纨。（芦雪庵尚未建出，暂在稻香村）' },
        reveal: {
          title: '访妙玉乞红梅', ch: '第五十回 · 芦雪庵争联即景诗',
          poem: ['酒未开樽句未裁，寻春问腊到蓬莱。', '不求大士瓶中露，为乞孀娥槛外梅。'],
          prose: '宝玉扛着一枝二尺来高的红梅回来，众人都笑着赏玩。李纨又命他就此事作诗一首，便是这首。',
          hour: 11
        }
      }
    ]
  },
  daiyu: {
    name: '林黛玉', short: '黛玉', home: '潇湘馆', start: 'xiaoxiang', season: 0, hour: 16.5,
    look: { robe: '#b7c8b6', robe2: '#98ae9a', sash: '#6f8c7c', crown: false },
    line: '寄居外祖母家，住潇湘馆。千百竿翠竹，一道曲栏。',
    quests: [
      {
        title: '葬花', at: [0, 16.5], want: '春残了，沁芳闸桥边的落花被人践踏，不如收起来葬了。',
        pick: { place: 'qinfang', kind: 'petals', n: 3, label: '落花', verb: '拾起', tip: '在沁芳亭一带拾起三捧落花。' },
        give: { place: 'qinfang', kind: 'mound', who: '花冢', verb: '葬入', tip: '把落花葬入花冢。' },
        reveal: {
          title: '葬花吟', ch: '第二十三回 · 第二十七回',
          poem: ['花谢花飞花满天，红消香断有谁怜？', '尔今死去侬收葬，未卜侬身何日丧？'],
          prose: '黛玉肩上担着花锄，锄上挂着花囊，手里拿着花帚。她说花撂在水里，流出园子仍旧糟蹋，不如装在绢袋里埋起来，日久随土化了，岂不干净。',
          season: 0, hour: 17.5
        }
      },
      {
        title: '借书与香菱', at: [2, 16], want: '香菱一心想学作诗，来求你教。',
        pick: { place: 'xiaoxiang', kind: 'item', item: 'book', label: '王右丞五言律', verb: '取出', tip: '在潇湘馆取出王维的五言律诗集。' },
        give: { place: 'hengwu', who: '香菱', color: '#c9a88a', verb: '借给', tip: '把诗集借给住在蘅芜苑的香菱。' },
        reveal: {
          title: '香菱咏月', ch: '第四十八回 · 第四十九回',
          poem: ['精华欲掩料应难，影自娟娟魄自寒。'],
          prose: '黛玉让她先读透王维的五言律一百首，再读杜甫、李白。香菱茶饭无心，坐卧不定，连作三首咏月诗，第三首梦中得来，众人都说新巧有意趣。',
          hour: 21.5
        }
      }
    ]
  },
  xiangyun: {
    name: '史湘云', short: '湘云', home: '史侯府（客居园中）', start: 'gate', season: 1, hour: 15,
    look: { robe: '#c98a4e', robe2: '#a86d3b', sash: '#3f5f6e', crown: false },
    line: '贾母的侄孙女，常来园中小住。心直口快，爱说爱笑。',
    quests: [
      {
        title: '绛纹石戒指', at: [1, 15], want: '上回打发人送了戒指给姐妹们，这回亲自带来给袭人她们。',
        pick: { place: 'gate', kind: 'item', item: 'ring', label: '绛纹石戒指', verb: '取出', tip: '在正门进园前，取出带来的绛纹石戒指。' },
        give: { place: 'yihong', who: '袭人', color: '#c7a3a0', verb: '送给', tip: '把戒指送到怡红院，交给袭人。' },
        reveal: {
          title: '因麒麟伏白首双星', ch: '第三十一回',
          poem: [],
          prose: '湘云来园中，特意带了绛纹石戒指，一包四个，分给袭人、鸳鸯、金钏、平儿。袭人笑说前日已收过她打发人送来的，知她心里时时记着人。',
          season: 1, hour: 15.5
        }
      },
      {
        title: '螃蟹宴', at: [2, 14.5], want: '起了诗社要做东，可手头短。宝姐姐说替你张罗螃蟹。',
        pick: { place: 'hengwu', kind: 'npc', who: '薛宝钗', color: '#e5d9b6', item: 'crab', label: '几篓螃蟹', verb: '从宝钗处领', tip: '去蘅芜苑，从宝钗处领几篓肥螃蟹。' },
        give: { place: 'ouxiang', who: '贾母', color: '#6d5a48', verb: '摆给', tip: '把螃蟹带到藕香榭，请老太太和众人赏桂吃蟹。' },
        reveal: {
          title: '菊花诗', ch: '第三十七回 · 第三十八回',
          poem: ['欲讯秋情众莫知，喃喃负手叩东篱。'],
          prose: '宝钗让家里伙计送来几篓极肥极大的螃蟹，替湘云在藕香榭做东。众人赏桂吃蟹，又作菊花诗十二题，黛玉《咏菊》《问菊》《菊梦》夺魁。',
          hour: 15.5
        }
      }
    ]
  }
};

/* ---------------------------------------------------------------------
   解谜：园中各处是“谜位”（空匾、谜灯），手里或园中别处是“谜底”。
   走到谜位前，从手中的谜底里挑一件；全部对上即揭示原著。
   pieces：无 place 的开局就在手里；有 place 的要先去那里拾取。
   strikes：允许错几次（0 = 不限）。谜面、诗句为原文，其余为转述。
   --------------------------------------------------------------------- */
const PUZZLES = {
  tidui: {
    title: '试才题对额', ch: '第十七回', start: 'gate', season: 0, hour: 10, color: '#2f4a4c', look: CHARS.baoyu.look,
    line: '园子刚落成，各处还没有名字。贾政带着宝玉和一班清客进园，命他一路题来。',
    rule: '袖中有十块匾：六块是宝玉拟的，四块是清客拟的。走到各处空匾前，看景挑匾。挂错三次，就要被叉出去。',
    want: '园子新成，各处还没有名字。贾政命你一路题来。',
    tip: '去各处空匾前，看景挑匾。先去哪处都可以。', doneTip: '六处都题好了。',
    ask: '挂哪一块？', bagName: '袖中匾', strikes: 3,
    wrong: ['贾政摇头道：“不妥。”', '贾政喝道：“胡说！”'],
    other: '这块匾另有更合适的去处。',
    out: { title: '叉出去！', text: '贾政气的喝命：“叉出去！”刚出去，又喝命：“回来！”——已经题好的匾都还挂着，从园门再来。' },
    pieces: [
      { id: 'qujing', label: '曲径通幽处' }, { id: 'qinfang', label: '沁芳' }, { id: 'youfeng', label: '有凤来仪' },
      { id: 'xinglian', label: '杏帘在望' }, { id: 'hengzhi', label: '蘅芷清芬' }, { id: 'hongxiang', label: '红香绿玉' },
      { id: 'xieyu', label: '泻玉', why: '这是清客拟的。宝玉说此处是省亲驻跸之地，用“泻”字粗陋不雅。' },
      { id: 'xinghua', label: '杏花村', why: '这是清客拟的。贾政说“杏花村”犯了正名，村名要等贵妃来定。' },
      { id: 'lanfeng', label: '兰风蕙露', why: '这是清客拟的。宝玉嫌它泛泛，没有说出此处异草的好处。' },
      { id: 'chongguang', label: '崇光泛彩', why: '这是清客拟的，只顾了海棠一边。' }
    ],
    slots: [
      { place: 'rock', kind: 'plaque', tag: '空匾', title: '一带翠嶂', answer: 'qujing',
        clue: '一进园门，一带翠嶂挡在面前，白石崚嶒，或如鬼怪，或如猛兽，其中微露羊肠小径。贾政说：非此一山，一进来园中所有之景悉入目中，则有何趣？',
        ok: '宝玉说：编新不如述旧，刻古终胜雕今。此处不过是探景一进步，不如直书旧句“曲径通幽处”，倒还大方气派。' },
      { place: 'qinfang', kind: 'plaque', tag: '空匾', title: '桥上有亭', answer: 'qinfang',
        clue: '清溪泻雪，石磴穿云，白石为栏，环抱池沼，石桥三港，桥上有亭。一带清流从花木深处泻于石隙之下。',
        ok: '清客们拟了“泻玉”。宝玉说：用“泻玉”二字，莫若“沁芳”二字，岂不新雅？又拟一联：“绕堤柳借三篙翠，隔岸花分一脉香。”贾政点头微笑。' },
      { place: 'xiaoxiang', kind: 'plaque', tag: '空匾', title: '千竿翠竹', answer: 'youfeng',
        clue: '一带粉垣，数楹修舍，有千百竿翠竹遮映，后院有大株梨花兼着芭蕉。贾政说：若能月夜坐此窗下读书，不枉虚生一世。宝玉却说：这是第一处行幸之处，必须颂圣方可。',
        ok: '凤凰非竹实不食。此处翠竹千竿，又是贵妃头一处行幸之所，故题“有凤来仪”。宝玉又拟一联：“宝鼎茶闲烟尚绿，幽窗棋罢指犹凉。”' },
      { place: 'daoxiang', kind: 'plaque', tag: '空匾', title: '数楹茅屋', answer: 'xinglian',
        clue: '一带黄泥筑就的矮墙，墙头皆用稻茎掩护。有几百株杏花，如喷火蒸霞一般。里面数楹茅屋，外面分畦列亩，佳蔬菜花。贾政说：此处还少一个酒幌，明日竟做一个来，用竹竿挑在树梢。',
        ok: '宝玉说：旧诗有云“红杏梢头挂酒旗”，如今莫若“杏帘在望”四字。他还说村名可用“稻香村”，取古人“柴门临水稻花香”之句。' },
      { place: 'hengwu', kind: 'plaque', tag: '空匾', title: '异草清香', answer: 'hengzhi',
        clue: '一所清凉瓦舍，一色水磨砖墙。迎面突出插天的玲珑山石，把里面房屋悉皆遮住。一株花木也无，只见许多异草，或牵藤，或引蔓，味香气馥，非凡花之可比。',
        ok: '宝玉认得这些异草：香的是杜若蘅芜，那一种大约是茝兰，这一种大约是清葛。故题“蘅芷清芬”，对联是：“吟成豆蔻才犹艳，睡足酴醾梦也香。”' },
      { place: 'yihong', kind: 'plaque', tag: '空匾', title: '蕉棠两植', answer: 'hongxiang',
        clue: '粉墙环护，绿柳周垂。院中点衬几块山石，一边种几本芭蕉，那一边是一树西府海棠，其势若伞，丝垂翠缕，葩吐丹砂。',
        ok: '清客拟了“蕉鹤”“崇光泛彩”。宝玉说：此处蕉棠两植，其意暗蓄“红”“绿”二字在内。若只说蕉，则棠无着落；若只说棠，蕉亦无着落。故题“红香绿玉”。' }
    ],
    reveal: {
      title: '天上人间诸景备', ch: '第十七回 · 第十八回',
      poem: ['衔山抱水建来精，多少工夫筑始成。', '天上人间诸景备，芳园应锡大观名。'],
      prose: '这一路题下来，贾政嘴上喝他“无知的业障”，心里却是得意的。这些匾原是暂且挂上，等元妃省亲时再定。元妃回府那晚，把“有凤来仪”赐名潇湘馆，“红香绿玉”改作“怡红快绿”，又题了这首诗，赐园名“大观园”。',
      hour: 19.5
    }
  },
  dengmi: {
    title: '元宵灯谜', ch: '第二十二回', start: 'gate', season: 3, hour: 18.5, color: '#a8322a', look: CHARS.baoyu.look,
    line: '上元佳节，宫里的元妃送出灯谜，家里姊妹也各制一个，贾政也来凑趣。',
    rule: '五盏谜灯挂在园中各处，谜底散落在别处。先把谜底拾来，再到灯下猜。猜错了不要紧，再读一遍谜面。',
    want: '上元佳节，姊妹们各制灯谜。贾政也来凑趣。',
    tip: '园中有五盏谜灯、五件谜底。先拾谜底，再去灯下猜。', doneTip: '五个谜都猜中了。',
    ask: '谜底是哪一件？', bagName: '手里', strikes: 0,
    empty: '手里还没有可猜的东西。去园中别处找找谜底。',
    wrong: ['不是这个。再读一遍谜面。'],
    pieces: [
      { id: 'baozhu', label: '爆竹', item: 'baozhu', place: 'yihong' },
      { id: 'suanpan', label: '算盘', item: 'suanpan', place: 'daoxiang' },
      { id: 'fengzheng', label: '风筝', item: 'fengzheng', place: 'hengwu' },
      { id: 'haideng', label: '佛前海灯', item: 'haideng', place: 'longcui' },
      { id: 'yantai', label: '砚台', item: 'yantai', place: 'xiaoxiang' }
    ],
    slots: [
      { place: 'daguan', kind: 'lantern', tag: '元妃的灯谜', title: '元妃的灯谜', answer: 'baozhu',
        poem: ['能使妖魔胆尽摧，身如束帛气如雷。', '一声震得人方恐，回首相看已化灰。'], ok: '是爆竹。一声震响，回头再看，已经化成了灰。' },
      { place: 'qinfang', kind: 'lantern', tag: '迎春的灯谜', title: '迎春的灯谜', answer: 'suanpan',
        poem: ['天运人功理不穷，有功无运也难逢。', '因何镇日纷纷乱，只为阴阳数不同。'], ok: '是算盘。上下两档珠子，镇日拨来拨去。' },
      { place: 'huapu', kind: 'lantern', tag: '探春的灯谜', title: '探春的灯谜', answer: 'fengzheng',
        poem: ['阶下儿童仰面时，清明妆点最堪宜。', '游丝一断浑无力，莫向东风怨别离。'], ok: '是风筝。清明时节放起来，线一断，就飘远了。' },
      { place: 'ouxiang', kind: 'lantern', tag: '惜春的灯谜', title: '惜春的灯谜', answer: 'haideng',
        poem: ['前身色相总无成，不听菱歌听佛经。', '莫道此生沉黑海，性中自有大光明。'], ok: '是佛前海灯。长明在佛前，一盏孤灯。' },
      { place: 'rock', kind: 'lantern', tag: '贾政的灯谜', title: '贾政的灯谜', answer: 'yantai',
        poem: ['身自端方，体自坚硬。', '虽不能言，有言必应。'], ok: '是砚台。原著里这谜是贾政出给贾母猜的，宝玉悄悄把谜底告诉了老太太。' }
    ],
    reveal: {
      title: '制灯谜贾政悲谶语', ch: '第二十二回 · 听曲文宝玉悟禅机 制灯谜贾政悲谶语',
      poem: [],
      prose: '贾政一一猜着，心里却越想越闷：娘娘作的爆竹，是一响而散之物；迎春作的算盘，是打动乱如麻；探春作的风筝，是飘飘浮荡之物；惜春作的海灯，一发清净孤独。今乃上元佳节，如何皆作此不祥之物为戏耶？回到房中，只是思索，翻来覆去，竟难成寐。',
      season: 3, hour: 21
    }
  }
};
const pieceOf = (P, id) => P.pieces.find(p => p.id === id);

/* ---------------------------------------------------------------------
   样式 & 界面
   --------------------------------------------------------------------- */
const css = `
#g-start{position:fixed;inset:0;z-index:40;display:flex;align-items:center;justify-content:center;padding:24px;background:radial-gradient(ellipse at 50% 40%,rgba(18,21,27,.35),rgba(18,21,27,.78));overflow:auto}
#g-start[hidden],#g-modal[hidden],#g-quest[hidden],#g-compass[hidden],#g-prompt[hidden]{display:none}
.g-sheet{background:var(--glass);border:1px solid var(--line);box-shadow:0 20px 60px rgba(0,0,0,.35);border-radius:3px;padding:28px 30px 24px;max-width:860px;width:100%;color:var(--ink)}
.g-sheet h2{margin:0;font-family:var(--f-disp);font-weight:400;font-size:44px;letter-spacing:.1em;line-height:1.1}
.g-sheet .g-lead{margin:10px 0 22px;font-size:15px;line-height:1.9;color:var(--ink-2);max-width:620px}
.g-chars{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.g-char{all:unset;box-sizing:border-box;cursor:pointer;padding:16px 16px 14px;border:1px solid var(--line);border-radius:2px;background:rgba(255,255,255,.35);display:flex;flex-direction:column;gap:6px;transition:background .15s,border-color .15s}
.g-char:hover,.g-char:focus-visible{background:rgba(255,255,255,.7);border-color:var(--cinnabar)}
.g-char b{font-family:var(--f-disp);font-weight:400;font-size:28px;letter-spacing:.1em}
.g-char .sw{width:26px;height:4px;border-radius:2px}
.g-char small{font-size:12px;color:var(--cinnabar);letter-spacing:.12em}
.g-char p{margin:0;font-size:13px;line-height:1.75;color:var(--ink-2)}
.g-char ol{margin:4px 0 0;padding-left:18px;font-size:12.5px;line-height:1.8;color:var(--ink-2)}
.g-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:18px;flex-wrap:wrap}
.g-link{all:unset;cursor:pointer;font-size:13px;color:var(--ink-2);border-bottom:1px solid var(--line)}
.g-link:hover{color:var(--ink)}
.g-recv{display:flex;gap:8px;align-items:center}
.g-recv input,.g-form input,.g-form select,.g-form textarea{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:2px;background:rgba(255,255,255,.6);color:var(--ink);min-width:0}
.g-btn{all:unset;cursor:pointer;box-sizing:border-box;padding:8px 16px;border-radius:2px;background:var(--ink);color:var(--paper);font-size:14px;letter-spacing:.08em;text-align:center}
.g-btn:hover{background:#000}
.g-btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
#g-quest{position:fixed;left:16px;top:calc(16px + env(safe-area-inset-top,0px));width:min(300px,calc(100% - 32px));padding:14px 16px 12px;border-radius:3px;z-index:6}
#g-quest .who{display:flex;justify-content:space-between;align-items:baseline;font-size:12px;letter-spacing:.14em;color:var(--cinnabar)}
#g-quest .who b{font-family:var(--f-disp);font-weight:400;font-size:22px;color:var(--ink);letter-spacing:.1em}
#g-quest .want{margin:8px 0 6px;font-size:13px;line-height:1.75;color:var(--ink-2)}
#g-quest .tip{margin:0;font-size:14.5px;line-height:1.7;padding-left:10px;border-left:2px solid var(--cinnabar)}
#g-quest .dots{display:flex;gap:5px;margin-top:10px}
#g-quest .dots i{width:18px;height:3px;border-radius:2px;background:var(--line)}
#g-quest .dots i.on{background:var(--cinnabar)}
#g-quest .bag{margin-top:8px;font-size:12px;color:var(--ink-2)}
#g-compass{position:fixed;left:50%;top:calc(16px + env(safe-area-inset-top,0px));transform:translateX(-50%);display:flex;align-items:center;gap:10px;padding:6px 14px;border-radius:20px;font-size:13px;letter-spacing:.06em;z-index:5;pointer-events:none}
#g-compass svg{width:18px;height:18px;transition:transform .1s linear}
#g-compass b{font-family:var(--f-disp);font-weight:400;font-size:18px}
#g-prompt{all:unset;position:fixed;left:50%;bottom:calc(128px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);padding:10px 18px;border-radius:3px;font-size:15px;letter-spacing:.06em;cursor:pointer;z-index:7;display:flex;align-items:center;gap:10px}
#g-prompt kbd{font:inherit;font-size:13px;padding:1px 8px;border:1px solid var(--ink-2);border-radius:3px}
#g-modal{position:fixed;inset:0;z-index:45;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(10,12,16,.45);overflow:auto}
.g-scroll{max-height:calc(100vh - 48px);overflow:auto}
.g-scroll{max-width:560px;text-align:center;padding:34px 34px 26px}
.g-scroll .ey{font-size:12px;letter-spacing:.2em;color:var(--cinnabar)}
.g-scroll h3{margin:6px 0 18px;font-family:var(--f-disp);font-weight:400;font-size:40px;letter-spacing:.14em}
.g-scroll .poem{font-family:var(--f-disp);font-size:24px;line-height:1.85;letter-spacing:.08em;margin:0 0 16px}
.g-scroll .prose{font-size:14.5px;line-height:1.95;text-align:justify;color:var(--ink-2);margin:0 0 14px}
.g-scroll .ch{font-size:12px;color:var(--ink-2);letter-spacing:.08em;padding-top:10px;border-top:1px solid var(--line)}
.g-scroll .g-btn{margin-top:16px;min-width:140px}
.g-form{display:grid;grid-template-columns:auto 1fr;gap:10px 12px;align-items:center;text-align:left;margin:6px 0 4px}
.g-form label{font-size:13px;color:var(--ink-2)}
.g-form textarea{resize:vertical;min-height:70px}
.g-code{margin-top:14px;padding:10px 12px;background:rgba(255,255,255,.55);border:1px dashed var(--line);font-size:12px;word-break:break-all;text-align:left;user-select:all}
.g-tag{position:fixed;left:0;top:0;transform:translate(-50%,-100%);padding:2px 9px;border-radius:2px;font-family:var(--f-disp);font-size:16px;letter-spacing:.1em;color:var(--ink);background:var(--glass);border:1px solid var(--line);pointer-events:none;white-space:nowrap;z-index:4}
.g-tag.goal{border-color:var(--cinnabar);color:var(--cinnabar)}
.g-sec{margin:22px 0 10px;font-family:var(--f-disp);font-weight:400;font-size:24px;letter-spacing:.14em}
.g-sec small{font-family:var(--f-body,inherit);font-size:12px;letter-spacing:.1em;color:var(--ink-2);margin-left:10px}
.g-scroll .ask{font-size:13px;letter-spacing:.16em;color:var(--cinnabar);margin:6px 0 0}
.g-opts{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:12px 0 0}
.g-opt{all:unset;box-sizing:border-box;cursor:pointer;position:relative;padding:9px 12px;border:1px solid var(--line);border-radius:2px;background:rgba(255,255,255,.4);font-family:var(--f-disp);font-size:21px;letter-spacing:.12em;text-align:center;color:var(--ink)}
.g-opt:hover,.g-opt:focus-visible{border-color:var(--cinnabar);background:rgba(255,255,255,.75)}
.g-opt i{position:absolute;left:8px;top:5px;font:normal 11px/1 sans-serif;color:var(--ink-2)}
#g-quest .strk{margin-top:6px;font-size:12px;color:var(--ink-2)}
#g-quest .strk b{color:var(--cinnabar);font-weight:400;letter-spacing:.1em}
body.g-playing .card{display:none!important}
@media (max-width:760px){.g-chars{grid-template-columns:1fr}.g-sheet{padding:20px 18px}.g-sheet h2{font-size:34px}.g-char ol{display:none}#g-quest{top:auto;bottom:calc(170px + env(safe-area-inset-bottom,0px));width:auto;right:16px}#g-prompt{bottom:calc(150px + env(safe-area-inset-bottom,0px))}.g-scroll{padding:24px 20px}.g-scroll .poem{font-size:20px}}
@media (prefers-reduced-motion:reduce){#g-compass svg{transition:none}}
`;
document.head.insertAdjacentHTML('beforeend', `<style>${css}</style>`);
document.body.insertAdjacentHTML('beforeend', `
<div id="g-start" hidden></div>
<aside id="g-quest" class="panel ui" hidden aria-live="polite"></aside>
<div id="g-compass" class="panel ui" hidden><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l6 16-6-4-6 4z" fill="currentColor"/></svg><b></b><span></span></div>
<button id="g-prompt" class="panel ui" hidden></button>
<div id="g-modal" hidden><div class="g-sheet g-scroll" role="dialog" aria-modal="true"></div></div>`);
const $ = id => document.getElementById(id);
const startEl = $('g-start'), questEl = $('g-quest'), compassEl = $('g-compass'), promptEl = $('g-prompt'), modalEl = $('g-modal'), scrollEl = modalEl.firstElementChild;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* dock 按钮：随时回到选人界面 */
{ const b = document.createElement('button'); b.className = 'tbtn'; b.id = 'btn-game'; b.textContent = '入园'; b.title = '选一个人入园';
  b.addEventListener('click', () => showStart()); const w = $('btn-walk'); w.parentNode.insertBefore(b, w); }

/* ---------------------------------------------------------------------
   场景锚点：从每个地点的步行出生点朝建筑走，找一块能站人的空地
   --------------------------------------------------------------------- */
const placeById = id => PLACES.find(p => p.id === id);
function spawnOf(id) { const p = placeById(id); if (p.spawn) return p.spawn; return [p.pos[0] + 6, p.pos[2] + 10, 0]; }
function okAt(x, z) { const [g, fromT] = groundAt(x, z, 99); if (fromT && g < 0.25) return null; if (blockedAt(x, g + 1.0, z) || blockedAt(x, g + 0.4, z)) return null; return g; }
const anchorCache = {};
/* 从出生点做一次可达搜索（0.5 米网格，考虑台阶高差与碰撞），取离建筑中心最近、四周留有余地的一格 */
function reachable(sx, sz, R = 34) {
  const N = Math.round(R * 2 / 0.5), cell = 0.5, ox = sx - R, oz = sz - R;
  const H = new Float32Array(N * N).fill(NaN), seen = new Uint8Array(N * N);
  const hAt = (i, j) => { const k = i * N + j; if (!Number.isNaN(H[k])) return H[k]; const x = ox + i * cell, z = oz + j * cell; const g = okAt(x, z); H[k] = g == null ? -1e9 : g; return H[k]; };
  const si = Math.round((sx - ox) / cell), sj = Math.round((sz - oz) / cell); const q = [si * N + sj]; seen[q[0]] = 1; const out = [];
  while (q.length) { const k = q.shift(), i = (k / N) | 0, j = k % N, h = hAt(i, j); out.push(k);
    for (const [a, b] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ni = i + a, nj = j + b; if (ni < 0 || nj < 0 || ni >= N || nj >= N) continue; const nk = ni * N + nj; if (seen[nk]) continue; const nh = hAt(ni, nj); if (nh < -1e8 || Math.abs(nh - h) > 0.45) continue; seen[nk] = 1; q.push(nk); } }
  return { N, cell, ox, oz, seen, H, list: out };
}
function anchor(id) {
  if (anchorCache[id]) return anchorCache[id];
  const p = placeById(id), [sx, sz] = spawnOf(id);
  const RG = reachable(sx, sz); const { N, cell, ox, oz, seen, H } = RG;
  const clear = (i, j, r) => { for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) { const ni = i + a, nj = j + b; if (ni < 0 || nj < 0 || ni >= N || nj >= N || !seen[ni * N + nj]) return false; } return true; };
  let best = null, bd = 1e9;
  for (const k of RG.list) { const i = (k / N) | 0, j = k % N; if (!clear(i, j, 2)) continue; const x = ox + i * cell, z = oz + j * cell; const d = Math.hypot(x - p.pos[0], z - p.pos[2]); const fromSpawn = Math.hypot(x - sx, z - sz); if (fromSpawn < 3) continue; if (d < bd) { bd = d; best = [i, j]; } }
  let x, z; if (best) { x = ox + best[0] * cell; z = oz + best[1] * cell; } else { x = sx; z = sz; }
  let dx = p.pos[0] - x, dz = p.pos[2] - z; const L = Math.hypot(dx, dz) || 1; dx /= L; dz /= L;
  const side = [-dz, dx];
  const a = { x, z, y: groundAt(x, z, 99)[0], dir: [dx, dz], side, spawn: [sx, sz], RG };
  const reach = (x2, z2) => { const i = Math.round((x2 - ox) / cell), j = Math.round((z2 - oz) / cell); return i >= 1 && j >= 1 && i < N - 1 && j < N - 1 && clear(i, j, 1); };
  a.reach = reach;
  a.off = (k) => { // 在锚点旁边找一个可达的位置（先侧向，再往回退）
    const tries = []; for (const s of [k, -k, k * 0.6, -k * 0.6, k * 1.4, -k * 1.4]) tries.push([x + side[0] * s, z + side[1] * s]);
    for (const s of [k, k * 1.5, k * 2]) tries.push([x - dx * s, z - dz * s]);
    for (const [ox2, oz2] of tries) if (reach(ox2, oz2)) return new V3(ox2, groundAt(ox2, oz2, 99)[0], oz2);
    return new V3(x - dx * 1.5, groundAt(x - dx * 1.5, z - dz * 1.5, 99)[0], z - dz * 1.5); };
  return anchorCache[id] = a;
}
function ringPoints(id, n) { // 在出生点周围的可达地面上撒点（落花）
  const [sx, sz] = spawnOf(id), a = anchor(id), out = [];
  for (let i = 0; i < 60 && out.length < n; i++) { const ang = i * 2.39996 + 0.7, r = 4 + (i % 5) * 1.5; const x = sx + Math.cos(ang) * r, z = sz + Math.sin(ang) * r;
    if (!a.reach(x, z)) continue; if (out.some(v => Math.hypot(v.x - x, v.z - z) < 3)) continue; if (Math.hypot(x - a.x, z - a.z) < 3) continue; out.push(new V3(x, groundAt(x, z, 99)[0], z)); }
  while (out.length < n) { const v = a.off(2 + out.length); out.push(v); }
  return out;
}

/* ---------------------------------------------------------------------
   道具与人物（人物为占位小像，后续换 Tripo 生成的模型）
   --------------------------------------------------------------------- */
const std = (c, r = .7, x = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: new THREE.Color(c), roughness: r, metalness: 0 }, x));
function makeItem(kind) {
  const g = new THREE.Group();
  if (kind === 'pa') { for (let i = 0; i < 2; i++) { const m = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.02, 0.24), std(i ? '#e9e3d3' : '#dfe6ea', .9)); m.position.set(i * 0.05, i * 0.022, i * 0.04); m.rotation.y = i * 0.35; g.add(m); } }
  else if (kind === 'book') { const m = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.05, 0.36), std('#3c5566', .8)); g.add(m); const s = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.3, 0.012), std('#e8e0cc', .8)); s.position.set(0.06, 0.027, 0); s.rotation.x = -Math.PI / 2; g.add(s); }
  else if (kind === 'ring') { const m = new THREE.Mesh(new THREE.TorusGeometry(0.08, 0.02, 10, 24), std('#8a2f2a', .35, { metalness: .2 })); m.rotation.x = Math.PI / 2; g.add(m); const box = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.08, 0.16), std('#a8322a', .7)); box.position.y = -0.06; g.add(box); }
  else if (kind === 'mei') { const br = std('#3a2a20', .9), fl = std('#c2253a', .6); const main = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.022, 0.8, 6), br); main.position.y = 0.4; main.rotation.z = 0.25; g.add(main);
    for (let i = 0; i < 16; i++) { const f = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 5), fl); const t = 0.2 + (i / 16) * 0.6; f.position.set(-Math.sin(0.25) * t + Math.sin(i * 2.1) * 0.06, t * Math.cos(0.25) + 0.02, Math.cos(i * 1.7) * 0.06); g.add(f); } }
  else if (kind === 'crab') { const bk = std('#8a6a3c', .9); const b = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.15, 0.22, 14, 1, true), bk); b.material.side = THREE.DoubleSide; b.position.y = 0.11; g.add(b);
    for (let i = 0; i < 4; i++) { const c = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 6), std('#c1452b', .6)); c.scale.y = 0.45; c.position.set(Math.cos(i * 1.6) * 0.08, 0.22, Math.sin(i * 1.6) * 0.08); g.add(c); } }
  else if (kind === 'petal') { const m = std('#f2b6c4', .8, { side: THREE.DoubleSide }); for (let i = 0; i < 9; i++) { const p = new THREE.Mesh(new THREE.CircleGeometry(0.05, 6), m); p.rotation.set(-Math.PI / 2 + Math.sin(i) * 0.4, 0, i); p.position.set(Math.sin(i * 2.4) * 0.22, 0.01 + i * 0.004, Math.cos(i * 1.9) * 0.22); g.add(p); } }
  else if (kind === 'mound') { const m = new THREE.Mesh(new THREE.SphereGeometry(0.55, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), std('#5a4a36', 1)); m.scale.y = 0.45; g.add(m); const s = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.5, 0.06), std('#8d8a80', .9)); s.position.set(0, 0.25, -0.55); g.add(s); }
  else if (kind === 'gift') { const b = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.26, 0.3), std('#6b2a2a', .5)); b.position.y = 0.13; g.add(b); const r1 = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.27, 0.05), std('#c9a24a', .35, { metalness: .5 })); r1.position.y = 0.13; g.add(r1); const r2 = r1.clone(); r2.rotation.y = Math.PI / 2; r2.scale.x = 0.76; g.add(r2); }
  else if (kind === 'plaque') { const wood = std('#3a2418', .8); for (const s of [-1, 1]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.055, 2.05, 8), wood); p.position.set(s * 0.72, 1.02, 0); g.add(p); }
    const board = new THREE.Mesh(new THREE.BoxGeometry(1.56, 0.52, 0.07), std('#1f2a2c', .6)); board.position.y = 1.78; g.add(board);
    const face = new THREE.Mesh(new THREE.PlaneGeometry(1.48, 0.46), new THREE.MeshStandardMaterial({ roughness: .55 })); face.position.set(0, 1.78, 0.037); g.add(face); g.userData.face = face; drawPlaque(g, ''); }
  else if (kind === 'lantern') { const wood = std('#3a2418', .8); const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 2.4, 8), wood); p.position.y = 1.2; g.add(p);
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.04, 0.04), wood); arm.position.set(0.29, 2.32, 0); g.add(arm);
    const prof = [[0.02, 0], [0.16, 0.05], [0.22, 0.2], [0.16, 0.36], [0.02, 0.4]].map(q => new THREE.Vector2(q[0], q[1]));
    const lamp = new THREE.Mesh(new THREE.LatheGeometry(prof, 16), std('#c8321e', .7, { emissive: new THREE.Color('#ff5a2a'), emissiveIntensity: .7 })); lamp.position.set(0.55, 1.82, 0); g.add(lamp);
    const slip = new THREE.Mesh(new THREE.PlaneGeometry(0.1, 0.36), std('#efe6d2', .9, { side: THREE.DoubleSide })); slip.position.set(0.55, 1.6, 0); g.add(slip); g.userData.slip = slip; }
  else if (kind === 'baozhu') { const red = std('#b8261c', .6); for (let i = 0; i < 5; i++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.028, 0.2, 10), red); c.position.set(Math.cos(i * 1.26) * 0.05, 0.1, Math.sin(i * 1.26) * 0.05); g.add(c); }
    const band = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.085, 0.05, 14), std('#d9b45a', .5)); band.position.y = 0.1; g.add(band); }
  else if (kind === 'suanpan') { const wood = std('#5a3a22', .7); for (const [w, h, x, y] of [[0.42, 0.03, 0, 0.12], [0.42, 0.03, 0, -0.12], [0.03, 0.27, -0.2, 0], [0.03, 0.27, 0.2, 0], [0.42, 0.02, 0, 0.06]]) { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.04), wood); b.position.set(x, y, 0); g.add(b); }
    const bead = std('#2a1a12', .5); for (let i = 0; i < 7; i++) { const x = -0.15 + i * 0.05; const r = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.24, 4), wood); r.position.x = x; g.add(r);
      for (const y of [0.09, -0.02, -0.055, -0.09]) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.02, 8, 6), bead); b.scale.y = 0.6; b.position.set(x, y, 0); g.add(b); } } }
  else if (kind === 'fengzheng') { const sh = new THREE.Shape(); sh.moveTo(0, 0.3); sh.lineTo(0.22, 0.02); sh.lineTo(0, -0.3); sh.lineTo(-0.22, 0.02); sh.closePath();
    g.add(new THREE.Mesh(new THREE.ShapeGeometry(sh), std('#e7cf8e', .8, { side: THREE.DoubleSide })));
    const stick = std('#5a3a22', .8); const v = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.6, 0.01), stick); g.add(v); const h = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.01, 0.01), stick); h.position.y = 0.02; g.add(h);
    for (let i = 0; i < 3; i++) { const t = new THREE.Mesh(new THREE.PlaneGeometry(0.04, 0.12), std(i % 2 ? '#c2253a' : '#3f5f6e', .8, { side: THREE.DoubleSide })); t.position.set(Math.sin(i) * 0.02, -0.38 - i * 0.12, 0); t.rotation.z = Math.sin(i * 2) * 0.3; g.add(t); } g.position.y = 0.3; }
  else if (kind === 'haideng') { const prof = [[0, 0], [0.1, 0.01], [0.14, 0.08], [0.15, 0.1]].map(q => new THREE.Vector2(q[0], q[1]));
    const bowl = new THREE.Mesh(new THREE.LatheGeometry(prof, 18), std('#9c7a3c', .35, { metalness: .6, side: THREE.DoubleSide })); g.add(bowl);
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), new THREE.MeshBasicMaterial({ color: '#ffd27a' })); f.scale.y = 1.8; f.position.y = 0.15; g.add(f); }
  else if (kind === 'yantai') { const s = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.06, 0.2), std('#2a2a2e', .5)); g.add(s); const w = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.012, 0.1), std('#101014', .2)); w.position.set(0, 0.026, 0.02); g.add(w); }
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; } });
  return g;
}
/* 匾面：石青底、金边、金字；先用系统楷体，园中书法字体加载好后重画 */
function drawPlaque(obj, text) {
  const face = obj.userData.face; if (!face) return; obj.userData.text = text;
  const c = face.userData.canvas || (face.userData.canvas = Object.assign(document.createElement('canvas'), { width: 512, height: 160 })); const x = c.getContext('2d');
  x.fillStyle = '#1f2a2c'; x.fillRect(0, 0, 512, 160); x.strokeStyle = '#c9a24a'; x.lineWidth = 8; x.strokeRect(10, 10, 492, 140); x.lineWidth = 2; x.strokeRect(22, 22, 468, 116);
  if (text) { const fs = text.length > 4 ? 76 : 92; x.fillStyle = '#d9b45a'; x.font = `${fs}px "Ma Shan Zheng","STKaiti","KaiTi","Kaiti SC",serif`; x.textAlign = 'center'; x.textBaseline = 'middle';
    const n = [...text].length, step = Math.min(fs * 1.08, 440 / n); [...text].forEach((ch, i) => x.fillText(ch, 256 + (i - (n - 1) / 2) * step, 84)); }
  if (!face.material.map) { face.material.map = new THREE.CanvasTexture(c); face.material.map.colorSpace = THREE.SRGBColorSpace; face.material.map.anisotropy = 4; face.material.needsUpdate = true; } else face.material.map.needsUpdate = true;
}
try { document.fonts?.load('80px "Ma Shan Zheng"').then(() => { for (const o of S.objects) if (o.userData.text) drawPlaque(o, o.userData.text); }); } catch (e) {}
function makeFigure(color, female = true) {
  const g = new THREE.Group(), robe = std(color, .85), dark = std(new THREE.Color(color).multiplyScalar(0.8).getStyle(), .85), skin = std('#efd3bb', .6), hair = std('#16130f', .5);
  const prof = [[0, 0], [0.31, 0], [0.29, 0.15], [0.25, 0.55], [0.2, 0.9], [0.18, 1.08]].map(p => new THREE.Vector2(p[0], p[1]));
  const sk = new THREE.Mesh(new THREE.LatheGeometry(prof, 18), robe); sk.position.y = 0.05; g.add(sk);
  const to = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.19, 0.42, 14), robe); to.position.y = 1.3; g.add(to);
  for (const s of [-1, 1]) { const a = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.12, 0.5, 10), dark); a.position.set(s * 0.2, 1.24, 0.04); a.rotation.set(-0.35, 0, s * 0.12); g.add(a); }
  const hd = new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 14), skin); hd.scale.y = 1.1; hd.position.y = 1.67; g.add(hd);
  const hr = new THREE.Mesh(new THREE.SphereGeometry(0.117, 18, 10, 0, Math.PI * 2, 0, Math.PI * 0.55), hair); hr.rotation.x = -0.35; hr.position.set(0, 1.69, -0.012); g.add(hr);
  if (female) { for (const s of [-1, 1]) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.055, 12, 8), hair); b.position.set(s * 0.08, 1.8, -0.04); g.add(b); } }
  else { const b = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 8), hair); b.position.set(0, 1.81, -0.03); g.add(b); }
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}
/* 远处可见的淡金色光柱，指示下一个去处 */
const beaconMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  uniforms: { t: { value: 0 }, a: { value: 1 } },
  vertexShader: 'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
  fragmentShader: 'varying vec2 vU;uniform float t,a;void main(){float e=pow(1.-vU.y,1.6)*(0.55+0.45*sin(vU.y*14.-t*2.));float s=1.-abs(vU.x*2.-1.);gl_FragColor=vec4(vec3(1.,.78,.42)*e*s*s*a*.55,1.);}' });
const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.9, 26, 20, 1, true), beaconMat); beacon.geometry.translate(0, 13, 0); beacon.visible = false; beacon.renderOrder = 5; scene.add(beacon);
const ringMat = new THREE.MeshBasicMaterial({ color: '#ffd28a', transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending });
const groundRing = new THREE.Mesh(new THREE.RingGeometry(0.55, 0.7, 40), ringMat); groundRing.rotation.x = -Math.PI / 2; groundRing.visible = false; scene.add(groundRing);

/* ---------------------------------------------------------------------
   状态
   --------------------------------------------------------------------- */
const S = { char: null, q: 0, stage: 'pick', petals: 0, carrying: null, objects: [], targets: [], tags: [], gift: null, done: {}, puz: null, solved: {}, bag: [], found: {}, strikes: 0 };
try { Object.assign(S.done, JSON.parse(localStorage.getItem('dgy-game-done') || '{}')); } catch (e) {}
const saveDone = () => { try { localStorage.setItem('dgy-game-done', JSON.stringify(S.done)); } catch (e) {} };

function clearWorld() { for (const o of S.objects) scene.remove(o); S.objects = []; S.targets = []; for (const t of S.tags) t.el.remove(); S.tags = []; beacon.visible = groundRing.visible = false; }
function addTag(text, obj, dy, goal) { const el = document.createElement('div'); el.className = 'g-tag ui' + (goal ? ' goal' : ''); el.textContent = text; document.body.appendChild(el); const t = { el, obj, dy, goal }; S.tags.push(t); return t; }
function place(obj, v, faceTo) { obj.position.copy(v); if (faceTo) obj.rotation.y = Math.atan2(faceTo.x - v.x, faceTo.z - v.z); scene.add(obj); S.objects.push(obj); return obj; }

/* 根据当前阶段布置场景：本阶段要互动的东西 + 光柱 */
function stageWorld() {
  clearWorld(); if (!S.char) return;
  const Q = CHARS[S.char].quests[S.q]; if (!Q) return;
  const P = Q.pick, G = Q.give;
  // 收礼人/花冢一直在场，让玩家先认得去处
  const ga = anchor(G.place);
  if (G.kind === 'mound') { const v = ga.off(2.4); const m = place(makeItem('mound'), v); S.targets.push({ stage: 'give', obj: m, pos: v, r: 2.2, label: G.verb + G.who }); addTag('花冢', m, 1.0, S.stage === 'give'); }
  else { const v = new V3(ga.x, ga.y, ga.z); const f = place(makeFigure(G.color, G.who !== '李纨' ? true : true), v, new V3(ga.spawn[0], 0, ga.spawn[1])); S.targets.push({ stage: 'give', obj: f, pos: v, r: 2.4, label: G.verb + G.who }); addTag(G.who, f, 2.15, S.stage === 'give'); }
  if (S.stage === 'pick') {
    if (P.kind === 'petals') { ringPoints(P.place, P.n).forEach((v, i) => { if (i < S.petals) return; const o = place(makeItem('petal'), v); S.targets.push({ stage: 'pick', obj: o, pos: v, r: 1.8, label: '拾起落花', petal: true, bob: 0 }); }); }
    else if (P.kind === 'npc') { const a = anchor(P.place); const v = P.place === G.place ? a.off(3) : new V3(a.x, a.y, a.z); const f = place(makeFigure(P.color, true), v, new V3(a.spawn[0], 0, a.spawn[1])); S.targets.push({ stage: 'pick', obj: f, pos: v, r: 2.4, label: P.verb + P.label }); addTag(P.who, f, 2.15, true); }
    else { const a = anchor(P.place); const v = P.place === G.place ? a.off(3) : a.off(2.2); v.y += 0.85; const o = place(makeItem(P.item), v); o.userData.baseY = v.y; S.targets.push({ stage: 'pick', obj: o, pos: v, r: 2.0, label: P.verb + P.label, bob: 1 }); addTag(P.label, o, 0.55, true); }
  }
  renderQuest();
}
/* 解谜场景：未解的谜位、尚未拾取的谜底都是目标；已解的谜位留在原地显示答案 */
function puzWorld() {
  clearWorld(); const P = PUZZLES[S.puz]; if (!P) return;
  P.slots.forEach((sl, i) => {
    const a = anchor(sl.place), v = a.off(2.6), o = place(makeItem(sl.kind), v, new V3(a.spawn[0], 0, a.spawn[1])), where = placeById(sl.place).name;
    if (S.solved[i]) { const pc = pieceOf(P, sl.answer); if (sl.kind === 'plaque') drawPlaque(o, pc.label); else o.userData.slip.material.color.set('#d9b45a'); addTag(sl.kind === 'plaque' ? where : pc.label, o, 2.35, false); return; }
    S.targets.push({ stage: 'puz', obj: o, pos: v, r: 2.6, label: sl.kind === 'plaque' ? '看景题匾' : '读谜面', slot: i, where }); addTag(sl.tag, o, 2.35, true);
  });
  for (const pc of P.pieces) { if (!pc.place || S.found[pc.id]) continue;
    const a = anchor(pc.place), v = a.off(2.2); v.y += 0.85; const o = place(makeItem(pc.item), v); o.userData.baseY = v.y;
    S.targets.push({ stage: 'puz', obj: o, pos: v, r: 2.0, label: '拾起' + pc.label, piece: pc.id, bob: 1, where: placeById(pc.place).name }); addTag(pc.label, o, 0.55, true); }
  renderQuest();
}
function currentGoal() { const t = S.targets.filter(t => t.stage === S.stage); if (!t.length) return null; const p = walk.pos; t.sort((a, b) => a.pos.distanceToSquared(p) - b.pos.distanceToSquared(p)); return t[0]; }

/* ---------------------------------------------------------------------
   界面渲染
   --------------------------------------------------------------------- */
function renderQuest() {
  if (S.puz) { const P = PUZZLES[S.puz], n = P.slots.filter((_, i) => S.solved[i]).length, all = n >= P.slots.length;
    const dots = P.slots.map((_, i) => `<i class="${S.solved[i] ? 'on' : ''}"></i>`).join('');
    const bag = S.bag.length ? `<div class="bag">${esc(P.bagName)}：${S.bag.map(id => esc(pieceOf(P, id).label)).join('、')}</div>` : '';
    const strk = P.strikes && !all ? `<div class="strk">贾政 <b>${'●'.repeat(S.strikes)}${'○'.repeat(P.strikes - S.strikes)}</b></div>` : '';
    questEl.innerHTML = `<div class="who"><b>${esc(P.title)}</b><span>${esc(P.ch)} · ${n}/${P.slots.length}</span></div><p class="want">${esc(P.want)}</p><p class="tip">${esc(all ? P.doneTip : P.tip)}</p>${bag}${strk}<div class="dots">${dots}</div>`;
    questEl.hidden = !walk.on; return; }
  if (!S.char) { questEl.hidden = true; return; }
  const C = CHARS[S.char], Q = C.quests[S.q];
  const dots = C.quests.map((_, i) => `<i class="${i < S.q || (i === S.q && S.stage === 'done') ? 'on' : ''}"></i>`).join('');
  if (!Q) { questEl.innerHTML = `<div class="who"><b>${C.name}</b><span>心事已了</span></div><p class="tip">在园中随意走走，或按「入园」换一个人。</p><div class="dots">${dots}</div>`; questEl.hidden = !walk.on; return; }
  const tip = S.stage === 'pick' ? (Q.pick.kind === 'petals' ? `${Q.pick.tip}（${S.petals}/${Q.pick.n}）` : Q.pick.tip) : Q.give.tip;
  questEl.innerHTML = `<div class="who"><b>${C.name}</b><span>心事 ${S.q + 1}/${C.quests.length} · ${Q.title}</span></div><p class="want">${esc(Q.want)}</p><p class="tip">${esc(tip)}</p>${S.carrying ? `<div class="bag">随身：${esc(S.carrying)}</div>` : ''}<div class="dots">${dots}</div>`;
  questEl.hidden = !walk.on;
  for (const t of S.tags) t.el.classList.toggle('goal', t.goal || (S.stage === 'give' && t.obj === (S.targets.find(x => x.stage === 'give') || {}).obj));
}
function charCard(k) { const C = CHARS[k]; const done = S.done[k] ? ' · 已完成' : '';
  return `<button class="g-char" data-k="${k}"><span class="sw" style="background:${C.look.robe}"></span><b>${C.name}</b><small>${esc(C.home)}${done}</small><p>${esc(C.line)}</p><ol>${C.quests.map(q => `<li>${esc(q.title)}</li>`).join('')}</ol></button>`; }
function puzCard(k) { const P = PUZZLES[k]; const done = S.done['p:' + k] ? ' · 已解' : '';
  return `<button class="g-char" data-p="${k}"><span class="sw" style="background:${P.color}"></span><b>${P.title}</b><small>${esc(P.ch)}${done}</small><p>${esc(P.line)}</p><p>${esc(P.rule)}</p></button>`; }
function showStart(giftMode) {
  pauseGame(true);
  if (walk.on) exitWalk();
  if (giftMode && S.gift) {
    const g = S.gift, p = placeById(g.p) || placeById('qinfang');
    startEl.innerHTML = `<div class="g-sheet"><h2>园中有礼</h2><p class="g-lead"><b>${esc(g.f || '有人')}</b>在大观园的<b>${esc(p.name)}</b>给${esc(g.t ? g.t : '你')}留了一份礼：${esc(g.n || '一只锦盒')}。进园走到那里，就能打开它。</p><div class="g-foot"><button class="g-btn" id="g-go-gift">入园寻礼</button><button class="g-link" id="g-skip">先不打开，随便看看</button></div></div>`;
    startEl.hidden = false;
    $('g-go-gift').onclick = () => { startEl.hidden = true; beginGift(); };
    $('g-skip').onclick = () => { startEl.hidden = true; pauseGame(false); };
    return;
  }
  startEl.innerHTML = `<div class="g-sheet"><h2>我们的大观园</h2>
   <p class="g-lead">大观园本是贾府为元妃省亲造的一份礼。园中人也总以物寄情：一方旧帕，一枝红梅，几篓螃蟹。选一个人入园，替园中人把心意送到。</p>
   <div class="g-chars">${Object.keys(CHARS).map(charCard).join('')}</div>
   <h4 class="g-sec">解谜<small>照着原著的线索，把园中的谜一一解开</small></h4>
   <div class="g-chars">${Object.keys(PUZZLES).map(puzCard).join('')}</div>
   <div class="g-foot"><button class="g-link" id="g-skip">只是逛逛</button><form class="g-recv" id="g-recv"><input id="g-code-in" placeholder="有赠礼码？贴在这里" aria-label="赠礼码"><button class="g-btn ghost" type="submit">收礼</button></form></div></div>`;
  startEl.hidden = false;
  startEl.querySelectorAll('.g-char').forEach(b => b.onclick = () => { startEl.hidden = true; if (b.dataset.p) beginPuz(b.dataset.p); else beginChar(b.dataset.k); });
  $('g-skip').onclick = () => { startEl.hidden = true; pauseGame(false); document.body.classList.remove('g-playing'); };
  $('g-recv').onsubmit = (e) => { e.preventDefault(); const g = decodeGift($('g-code-in').value.trim()); if (!g) { $('g-code-in').value = ''; $('g-code-in').placeholder = '这个码打不开，再检查一下'; return; } S.gift = g; showStart(true); };
}

/* ---------------------------------------------------------------------
   流程
   --------------------------------------------------------------------- */
function dressHero(look) {
  hero.torso.material.color.set(look.robe); hero.arms.forEach(a => a.children[0].material.color.set(look.robe2)); hero.tail.material.color.set(look.sash);
  hero.head.traverse(o => { if (o.isMesh && o.material.metalness > 0.5) o.visible = look.crown; });
  hero.g.traverse(o => { if (o.isMesh && o.geometry.type === 'CylinderGeometry' && Math.abs(o.position.y - 1.12) < 0.01) o.material.color.set(look.sash); });
}
function setWorld(season, hour) { if (season != null) setSeason(season); if (hour != null) { hourEl.value = hour; hourEl.dispatchEvent(new Event('input')); } }
function spawnAt(id) { const s = spawnOf(id); return [s[0], s[1], s[2] ?? 0]; }
function beginChar(k) {
  S.char = k; S.q = 0; S.stage = 'pick'; S.petals = 0; S.carrying = null; S.giftMode = false; S.puz = null;
  const C = CHARS[k]; dressHero(C.look); const a0 = C.quests[0].at; setWorld(a0[0], a0[1]);
  document.body.classList.add('g-playing'); pauseGame(false);
  stageWorld(); enterWalk(spawnAt(C.start)); renderQuest();
}
function beginGift() {
  S.char = null; S.puz = null; S.giftMode = true; clearWorld(); document.body.classList.add('g-playing'); pauseGame(false);
  const g = S.gift, id = placeById(g.p) ? g.p : 'qinfang', a = anchor(id); const v = a.off(2.2);
  const o = place(makeItem('gift'), v); S.targets = [{ stage: 'gift', obj: o, pos: v, r: 2.2, label: '打开' + (g.f ? g.f + '的' : '') + '礼' }]; S.stage = 'gift'; addTag('给你的礼', o, 0.7, true);
  questEl.innerHTML = `<div class="who"><b>收礼</b><span>${esc(placeById(id).name)}</span></div><p class="tip">${esc(g.f || '有人')}把礼放在了${esc(placeById(id).name)}。跟着光柱走过去。</p>`;
  enterWalk(spawnAt(id)); questEl.hidden = false;
}
function beginPuz(k) {
  const P = PUZZLES[k];
  S.char = null; S.giftMode = false; S.puz = k; S.stage = 'puz'; S.solved = {}; S.found = {}; S.strikes = 0; S.carrying = null;
  S.bag = P.pieces.filter(p => !p.place).map(p => p.id);
  dressHero(P.look); setWorld(P.season, P.hour);
  document.body.classList.add('g-playing'); pauseGame(false);
  puzWorld(); enterWalk(spawnAt(P.start)); renderQuest();
  openModal(`<div class="ey">${esc(P.ch)} · 解谜</div><h3>${esc(P.title)}</h3><p class="prose">${esc(P.line)}</p><p class="prose">${esc(P.rule)}</p><button class="g-btn" id="g-next">入园</button>`, null);
}
/* 走到谜位前：展示谜面，从手里挑一件 */
function openSlot(i) {
  const P = PUZZLES[S.puz], sl = P.slots[i], where = placeById(sl.place).name;
  const opts = S.bag.map((id, n) => `<button class="g-opt" data-id="${id}"><i>${(n + 1) % 10}</i>${esc(pieceOf(P, id).label)}</button>`).join('');
  openModal(`<div class="ey">${esc(where)} · ${esc(sl.tag)}</div><h3>${esc(sl.title)}</h3>${sl.poem ? `<p class="poem">${sl.poem.map(esc).join('<br>')}</p>` : ''}${sl.clue ? `<p class="prose">${esc(sl.clue)}</p>` : ''}
   ${opts ? `<p class="ask">${esc(P.ask)}</p><div class="g-opts">${opts}</div>` : `<p class="prose">${esc(P.empty)}</p>`}<button class="g-btn ghost" id="g-next">${opts ? '再想想' : '知道了'}</button>`, null);
  scrollEl.querySelectorAll('.g-opt').forEach(b => b.onclick = () => choose(i, b.dataset.id));
}
function choose(i, id) {
  const P = PUZZLES[S.puz], sl = P.slots[i], pc = pieceOf(P, id), where = placeById(sl.place).name;
  if (id === sl.answer) {
    S.solved[i] = 1; S.bag = S.bag.filter(x => x !== id); blip(880); puzWorld();
    const all = P.slots.every((_, j) => S.solved[j]);
    openModal(`<div class="ey">${esc(where)}</div><h3>${esc(pc.label)}</h3><p class="prose">${esc(sl.ok)}</p><button class="g-btn" id="g-next">${all ? '看原著' : '继续'}</button>`, all ? puzReveal : null);
    return;
  }
  blip(220);
  if (!P.strikes) { openModal(`<div class="ey">${esc(where)} · ${esc(sl.tag)}</div><h3>${esc(pc.label)}？</h3><p class="prose">${esc(P.wrong[0])}</p><button class="g-btn" id="g-next">回去再看</button>`, () => openSlot(i)); return; }
  S.strikes++; const out = S.strikes >= P.strikes;
  const why = pc.why || (P.slots.some(x => x.answer === id) ? P.other : '');
  if (out) openModal(`<div class="ey">${esc(where)}</div><h3>${esc(P.out.title)}</h3><p class="prose">${esc(why)}</p><p class="prose">${esc(P.out.text)}</p><button class="g-btn" id="g-next">回园门</button>`, kickOut);
  else openModal(`<div class="ey">${esc(where)} · 挂上“${esc(pc.label)}”</div><h3>${esc(P.wrong[(S.strikes - 1) % P.wrong.length])}</h3><p class="prose">${esc(why)}</p><p class="prose">还能错 ${P.strikes - S.strikes} 次。</p><button class="g-btn" id="g-next">再看看</button>`, () => openSlot(i));
  renderQuest();
}
function kickOut() { const P = PUZZLES[S.puz]; S.strikes = 0; exitWalk(); enterWalk(spawnAt(P.start)); renderQuest(); flash('贾政又喝命：“回来！”'); }
function puzReveal() {
  const k = S.puz, P = PUZZLES[k], R = P.reveal; S.done['p:' + k] = 1; saveDone(); S.stage = 'done'; S.targets = []; setWorld(R.season, R.hour);
  openModal(`<div class="ey">${esc(R.ch)}</div><h3>${esc(R.title)}</h3>${R.poem.length ? `<p class="poem">${R.poem.map(esc).join('<br>')}</p>` : ''}<p class="prose">${esc(R.prose)}</p><div class="ch">见《红楼梦》${esc(R.ch.split(' · ')[0])}</div><button class="g-btn" id="g-next">继续</button>`,
    () => giftForm(P.title, P.start));
}
function interact() {
  const t = S.near; if (!t || t.stage !== S.stage || !t.obj.parent) return; S.near = null;
  if (S.stage === 'gift') { openGift(); return; }
  if (S.stage === 'puz') {
    if (t.piece) { const pc = pieceOf(PUZZLES[S.puz], t.piece); S.found[t.piece] = 1; S.bag.push(t.piece); scene.remove(t.obj); S.targets = S.targets.filter(x => x !== t); blip(660); flash('拾得' + pc.label); renderQuest(); }
    else openSlot(t.slot);
    return; }
  const C = CHARS[S.char], Q = C.quests[S.q];
  if (S.stage === 'pick') {
    if (t.petal) { scene.remove(t.obj); S.targets = S.targets.filter(x => x !== t); S.petals++; S.carrying = `落花 ${S.petals} 捧`; blip(660);
      if (S.petals >= Q.pick.n) { S.stage = 'give'; S.carrying = '一囊落花'; flash('收了一囊落花'); }
      renderQuest(); return; }
    S.carrying = Q.pick.label; S.stage = 'give'; blip(660);
    flash(Q.pick.kind === 'npc' ? `${Q.pick.who}给了你${Q.pick.label}` : `取了${Q.pick.label}`);
    stageWorld(); return;
  }
  if (S.stage === 'give') { S.stage = 'done'; S.carrying = null; blip(880); clearWorld(); reveal(Q); }
}
function reveal(Q) {
  const R = Q.reveal; setWorld(R.season, R.hour);
  openModal(`<div class="ey">${esc(R.ch)}</div><h3>${esc(R.title)}</h3>${R.poem.length ? `<p class="poem">${R.poem.map(esc).join('<br>')}</p>` : ''}<p class="prose">${esc(R.prose)}</p><div class="ch">见《红楼梦》${esc(R.ch.split(' · ')[0])}</div><button class="g-btn" id="g-next">继续</button>`,
    () => { S.q++; S.stage = 'pick'; S.petals = 0; const C = CHARS[S.char];
      if (S.q >= C.quests.length) { S.done[S.char] = 1; saveDone(); giftForm(C.name, C.start); } else { const n = C.quests[S.q]; setWorld(n.at[0], n.at[1]); stageWorld(); flash('新的心事 · ' + n.title); } });
}

/* ---------------------------------------------------------------------
   赠一份礼：写给现实中的一个人，生成赠礼码
   --------------------------------------------------------------------- */
function encodeGift(g) { const s = btoa(unescape(encodeURIComponent(JSON.stringify(g)))); return 'DGY-' + s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function decodeGift(code) { try { let s = code.replace(/^.*#gift=/, '').replace(/^DGY-/, '').replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const g = JSON.parse(decodeURIComponent(escape(atob(s)))); return g && g.p ? g : null; } catch (e) { return null; } }
function giftForm(name, start) {
  const opts = PLACES.filter(p => p.pos).map(p => `<option value="${p.id}"${p.id === start ? ' selected' : ''}>${esc(p.name)}</option>`).join('');
  openModal(`<div class="ey">${esc(name)} · ${S.puz ? '谜已解' : '心事已了'}</div><h3>赠一份礼</h3>
   <p class="prose">大观园是元妃的礼，园中人又以物互赠。现在轮到你：把园子里的一处地方，连同一份礼和一句话，送给现实中的一个人。</p>
   <div class="g-form"><label for="gf-f">你是</label><input id="gf-f" maxlength="12" placeholder="署名">
   <label for="gf-t">送给</label><input id="gf-t" maxlength="12" placeholder="对方的名字">
   <label for="gf-n">礼物</label><input id="gf-n" maxlength="24" placeholder="想送的东西，如：一枝红梅">
   <label for="gf-p">放在</label><select id="gf-p">${opts}</select>
   <label for="gf-m">留言</label><textarea id="gf-m" maxlength="140" placeholder="一句话"></textarea></div>
   <div id="gf-out"></div><button class="g-btn" id="gf-make">生成赠礼码</button> <button class="g-btn ghost" id="g-next">以后再说</button>`, null);
  $('gf-make').onclick = () => {
    const g = { f: $('gf-f').value.trim(), t: $('gf-t').value.trim(), n: $('gf-n').value.trim(), p: $('gf-p').value, m: $('gf-m').value.trim() };
    const code = encodeGift(g); let link = ''; try { link = location.href.split('#')[0] + '#gift=' + code.slice(4); } catch (e) {}
    $('gf-out').innerHTML = `<div class="g-code" id="gf-code">${esc(code)}</div><p class="prose" style="margin-top:8px">把赠礼码发给对方。对方打开大观园，点「入园」，把码贴进「收礼」，就会被带到${esc(placeById(g.p).name)}，找到你的礼。</p>`;
    try { navigator.clipboard.writeText(code); $('gf-make').textContent = '已复制'; } catch (e) {}
    void link;
  };
}
function openGift() {
  const g = S.gift; clearWorld(); blip(990); S.stage = 'none';
  openModal(`<div class="ey">${esc(placeById(g.p)?.name || '')}</div><h3>${esc(g.n || '一份礼')}</h3>${g.m ? `<p class="poem" style="font-size:22px">${esc(g.m)}</p>` : ''}<p class="prose" style="text-align:center">${g.t ? esc(g.t) + '：' : ''}这是${esc(g.f || '有人')}在大观园里留给你的。</p><button class="g-btn" id="g-next">收下</button>`,
    () => { S.giftMode = false; questEl.hidden = true; flash('也选一个人入园看看？'); setTimeout(() => { if (!walk.on) return; }, 0); });
}

/* ---------------------------------------------------------------------
   暂停 / 弹窗 / 小提示
   --------------------------------------------------------------------- */
function pauseGame(on) { window.__gamePause = on; if (on) { walk.keys = {}; walk.stick.x = walk.stick.y = 0; } }
let modalDone = null;
function openModal(html, onDone) {
  pauseGame(true); walk.keys = {}; if (document.pointerLockElement) document.exitPointerLock();
  scrollEl.innerHTML = html; modalEl.hidden = false; modalDone = onDone; promptEl.hidden = true;
  const n = $('g-next'); if (n) { n.onclick = closeModal; setTimeout(() => n.focus(), 50); }
}
function closeModal() {
  modalEl.hidden = true; pauseGame(false); const f = modalDone; modalDone = null;
  if (walk.on && !isTouch) D.renderer.domElement.requestPointerLock?.();
  if (f) f(); renderQuest();
}
const toastEl = $('toast'); let flashT = 0;
function flash(msg) { toastEl.innerHTML = `<b>${esc(msg)}</b>`; toastEl.style.opacity = 1; clearTimeout(flashT); flashT = setTimeout(() => toastEl.style.opacity = 0, 2600); }
let actx = null;
function blip(f) { try { actx = actx || new (window.AudioContext || window.webkitAudioContext)(); const t = actx.currentTime, o = actx.createOscillator(), g = actx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * 1.5, t + 0.25); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.08, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9); o.connect(g); g.connect(actx.destination); o.start(t); o.stop(t + 1); } catch (e) {} }

/* 键盘：弹窗时拦截所有按键，避免角色乱走；E / 回车 交互 */
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') { if (!modalEl.hidden || !startEl.hidden) e.stopImmediatePropagation(); return; }
  if (!modalEl.hidden) { e.stopImmediatePropagation();
    const m = /^Digit(\d)$/.exec(e.code), opt = m && scrollEl.querySelectorAll('.g-opt')[(+m[1] + 9) % 10]; if (opt) { e.preventDefault(); opt.click(); return; }
    if (e.target.classList?.contains('g-opt')) return; // 让回车 / 空格按下聚焦的选项
    if ((e.code === 'KeyE' || e.code === 'Enter' || e.code === 'Space') && $('g-next') && !$('gf-make')) { e.preventDefault(); closeModal(); } return; }
  if (!startEl.hidden) { e.stopImmediatePropagation(); return; }
  if (e.code === 'KeyE' && walk.on && S.near) { e.preventDefault(); interact(); }
}, true);
promptEl.addEventListener('click', interact);

/* ---------------------------------------------------------------------
   每帧：指引、提示、标签、道具浮动
   --------------------------------------------------------------------- */
const _v = new V3(); let last = performance.now();
function tick(now) {
  requestAnimationFrame(tick); const dt = Math.min(0.05, (now - last) / 1000); last = now; beaconMat.uniforms.t.value = now / 1000;
  const playing = (S.char || S.giftMode || S.puz) && walk.on;
  questEl.hidden = !(playing || (S.giftMode && walk.on));
  if (!playing) { compassEl.hidden = true; promptEl.hidden = true; beacon.visible = groundRing.visible = false; for (const t of S.tags) t.el.style.display = 'none'; return; }
  for (const t of S.targets) if (t.bob) t.obj.position.y = t.obj.userData.baseY + Math.sin(now / 500) * 0.06, t.obj.rotation.y += dt * 0.6;
  const goal = currentGoal(); const p = walk.pos;
  if (goal) {
    const d = Math.hypot(goal.pos.x - p.x, goal.pos.z - p.z);
    beacon.visible = d > 7; beacon.position.set(goal.pos.x, goal.pos.y, goal.pos.z); beaconMat.uniforms.a.value = Math.min(1, (d - 7) / 12);
    groundRing.visible = d < 18; groundRing.position.set(goal.pos.x, goal.pos.y + 0.04, goal.pos.z); ringMat.opacity = 0.35 + Math.sin(now / 300) * 0.2;
    // 指南：相对镜头朝向的方位
    const ang = Math.atan2(goal.pos.x - p.x, goal.pos.z - p.z); const camYaw = Math.atan2(-(Math.sin(walk.yaw)), -(Math.cos(walk.yaw)));
    let rel = ang - camYaw; rel = Math.atan2(Math.sin(rel), Math.cos(rel));
    const Q = S.char ? CHARS[S.char].quests[S.q] : null; const where = goal.where || (S.giftMode ? placeById(S.gift.p)?.name : placeById(S.stage === 'pick' ? Q.pick.place : Q.give.place).name);
    compassEl.hidden = d < 5; compassEl.querySelector('svg').style.transform = `rotate(${-rel}rad)`; compassEl.querySelector('b').textContent = where; compassEl.querySelector('span').textContent = Math.round(d / 0.75) + ' 步';
  } else { compassEl.hidden = true; beacon.visible = groundRing.visible = false; }
  // 最近的可交互目标
  let near = null; for (const t of S.targets) { if (t.stage !== S.stage) continue; const d = Math.hypot(t.pos.x - p.x, t.pos.z - p.z); if (d < t.r && Math.abs(t.pos.y - p.y) < 2.5) { near = t; break; } }
  S.near = modalEl.hidden ? near : null;
  if (S.near) { promptEl.innerHTML = isTouch ? `<span>点这里</span>${esc(S.near.label)}` : `<kbd>E</kbd>${esc(S.near.label)}`; promptEl.hidden = false; } else promptEl.hidden = true;
  // 头顶名签
  const W = innerWidth, H = innerHeight;
  for (const t of S.tags) { if (!t.obj.parent) { t.el.style.display = 'none'; continue; } _v.copy(t.obj.position); _v.y += t.dy; const dist = camera.position.distanceTo(_v); _v.project(camera);
    const vis = _v.z < 1 && dist < 60 && Math.abs(_v.x) < 1.1 && Math.abs(_v.y) < 1.1; t.el.style.display = vis ? '' : 'none';
    if (vis) { t.el.style.transform = `translate(${(_v.x * 0.5 + 0.5) * W}px,${(-_v.y * 0.5 + 0.5) * H}px) translate(-50%,-100%)`; t.el.style.opacity = dist > 35 ? 0.6 : 1; } }
}
requestAnimationFrame(tick);

/* 调试接口（测试用） */
window.__game = { S, CHARS, PUZZLES, beginPuz, choose, openSlot, beginChar, interact, anchor, stageWorld, encodeGift, decodeGift, showStart, closeModal, beginGift };

/* 开场：链接里带礼 → 收礼；否则显示选人 */
{ const g = decodeGift(location.hash || ''); if (g) { S.gift = g; showStart(true); } else showStart(); }
