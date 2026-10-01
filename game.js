/* =====================================================================
   我们的大观园 · 赠礼玩法
   选一个人入园 → 心事 → 寻物 → 送礼 → 原著片段揭示 → 赠一份礼给现实中的人
   依赖主页面暴露的 window.__dgy
   ===================================================================== */
const wait = () => new Promise(r => { const t = () => window.__dgy && window.__DGY_OK ? r(window.__dgy) : setTimeout(t, 200); t(); });
const D = await wait();
const { THREE, scene, hero, walk, blockedAt, groundAt, setSeason, applyTime, enterWalk, exitWalk, camera, PLACES, isTouch, hourEl } = D;
const V3 = THREE.Vector3;
/* 中英双语：window.__lang 由主页面设置；切换时触发 'dgy-lang' */
const EN = () => window.__lang === 'en'; const L = (zh, en) => EN() ? en : zh;
const T = (o, k) => EN() && o && o[k + 'En'] != null ? o[k + 'En'] : o && o[k];   // 取数据字段的当前语言版本
const pname = p => (EN() && p && p.en) ? p.en.name : (p && p.name);
const txt = v => typeof v === 'function' ? v() : v;   // 标签/随身物可为函数，渲染时按当前语言求值
const pickDo = P => EN() ? (P.doEn || `${P.verbEn} ${P.labelEn}`) : P.verb + P.label;
const giveDo = G => EN() ? (G.doEn || `${G.verbEn} ${G.whoEn}`) : G.verb + G.who;

/* ---------------------------------------------------------------------
   人物与心事（全部取自原著；诗句为原文，其余为转述）
   --------------------------------------------------------------------- */
const CHARS = {
  baoyu: {
    name: '贾宝玉', short: '宝玉', home: '怡红院', start: 'yihong', season: 1, hour: 16,
    nameEn: 'Jia Baoyu', shortEn: 'Baoyu', homeEn: 'Happy Red Court',
    look: { robe: '#a8342b', robe2: '#8b2b24', sash: '#c9a24a', crown: true },
    line: '衔玉而生，住怡红院。心里装着一园子的姊妹。',
    lineEn: 'Born with a jade in his mouth, he lives at Happy Red Court, and carries a whole garden of girl cousins in his heart.',
    quests: [
      {
        title: '两条旧帕', at: [1, 16], want: '挨打后养伤，想让林妹妹放心。',
        titleEn: 'Two Old Handkerchiefs', wantEn: 'Laid up after your beating, you want to set Cousin Lin’s mind at rest.',
        pick: { place: 'yihong', kind: 'item', item: 'pa', label: '两条旧帕子', verb: '取出', tip: '先在怡红院找到那两条半新不旧的帕子。',
          labelEn: 'two old handkerchiefs', verbEn: 'Take out', tipEn: 'First find the two well-worn handkerchiefs at Happy Red Court.' },
        give: { place: 'xiaoxiang', who: '林黛玉', color: '#b9c9b4', verb: '送给', tip: '把帕子送到潇湘馆，交给林妹妹。',
          whoEn: 'Lin Daiyu', verbEn: 'Give to', tipEn: 'Take the handkerchiefs to Bamboo Lodge and give them to Cousin Lin.' },
        reveal: {
          title: '题帕三绝', ch: '第三十四回 · 情中情因情感妹妹',
          titleEn: 'Three Quatrains on a Handkerchief', chEn: 'Chapter 34 · Love within love: his feeling moves his cousin',
          poem: ['眼空蓄泪泪空垂，暗洒闲抛却为谁？', '尺幅鲛绡劳解赠，叫人焉得不伤悲！'],
          poemEn: ['Eyes brim with tears, and tears fall all in vain; / shed in secret, spilled at idle hours, for whom?', 'This foot of mermaid silk, so kindly sent: / how could it fail to break my heart with grief?'],
          prose: '原著里是宝玉打发晴雯送去的，不带一句话。黛玉体贴出帕子的意思，又喜又悲，研墨蘸笔，在两块旧帕上一连写了三首绝句。',
          proseEn: 'In the novel Baoyu sends Qingwen with them, and not a word of message. Daiyu divines what the handkerchiefs mean, and is glad and grieved at once; she grinds ink, dips her brush, and writes three quatrains, one after another, on the two old handkerchiefs.',
          hour: 20.5
        }
      },
      {
        title: '乞红梅', at: [3, 10.5], want: '芦雪庵联诗落了第，社长李纨罚你去栊翠庵讨一枝红梅。',
        titleEn: 'Begging for Red Plum', wantEn: 'You came last in the linked verses at Reed Snow Cottage, and Li Wan, president of the poetry club, sends you as forfeit to Green Lattice Nunnery to beg a sprig of red plum.',
        pick: { place: 'longcui', kind: 'npc', who: '妙玉', color: '#d8d2c4', item: 'mei', label: '一枝红梅', verb: '向妙玉讨', tip: '去栊翠庵，向妙玉讨一枝红梅。',
          whoEn: 'Miaoyu', labelEn: 'a sprig of red plum', verbEn: 'Beg Miaoyu for', doEn: 'Beg a sprig of red plum from Miaoyu', tipEn: 'Go to Green Lattice Nunnery and beg a sprig of red plum from Miaoyu.' },
        give: { place: 'luxue', who: '李纨', color: '#8e8a80', verb: '交给', tip: '把红梅带回芦雪广，交给李纨。',
          whoEn: 'Li Wan', verbEn: 'Hand to', tipEn: 'Bring the plum back to Reed Snow Cottage and hand it to Li Wan.' },
        reveal: {
          title: '访妙玉乞红梅', ch: '第五十回 · 芦雪庵争联即景诗',
          titleEn: 'Begging Red Plum Blossom of Miaoyu', chEn: 'Chapter 50 · Rival linked verses on the snow at Reed Snow Cottage',
          poem: ['酒未开樽句未裁，寻春问腊到蓬莱。', '不求大士瓶中露，为乞孀娥槛外梅。'],
          poemEn: ['The wine still sealed, the verses still unmade, / I seek out spring in winter, at the Isle of the Blest.', 'Not for the dew in Guanyin’s holy vase: / I come to beg the moon-maid’s plum beyond the rail.'],
          prose: '宝玉扛着一枝二尺来高的红梅回来，众人都笑着赏玩。李纨又命他就此事作诗一首，便是这首。',
          proseEn: 'Baoyu comes back shouldering a branch of red plum some two feet high, and everyone crowds round, laughing and admiring it. Li Wan then sets him to write a poem on the errand, and this is the poem.',
          hour: 11
        }
      }
    ]
  },
  daiyu: {
    name: '林黛玉', short: '黛玉', home: '潇湘馆', start: 'xiaoxiang', season: 0, hour: 16.5,
    nameEn: 'Lin Daiyu', shortEn: 'Daiyu', homeEn: 'Bamboo Lodge',
    look: { robe: '#b7c8b6', robe2: '#98ae9a', sash: '#6f8c7c', crown: false },
    line: '寄居外祖母家，住潇湘馆。千百竿翠竹，一道曲栏。',
    lineEn: 'Living under her grandmother’s roof, she has Bamboo Lodge: a thousand stems of green bamboo and a winding balustrade.',
    quests: [
      {
        title: '葬花', at: [0, 16.5], want: '春残了，沁芳闸桥边的落花被人践踏，不如收起来葬了。',
        titleEn: 'Burying the Blossoms', wantEn: 'Spring is fading, and the fallen petals by the Drenched Blossoms weir are being trodden underfoot. Better to gather them up and bury them.',
        pick: { place: 'qinfang', kind: 'petals', n: 3, label: '落花', verb: '拾起', tip: '在沁芳亭一带拾起三捧落花。',
          labelEn: 'fallen petals', verbEn: 'Gather', tipEn: 'Gather three handfuls of fallen petals around Drenched Blossoms Pavilion.' },
        give: { place: 'qinfang', kind: 'mound', who: '花冢', verb: '葬入', tip: '把落花葬入花冢。',
          whoEn: 'Flower Grave', verbEn: 'Bury in the', doEn: 'Bury the petals in the Flower Grave', tipEn: 'Bury the petals in the Flower Grave.' },
        reveal: {
          title: '葬花吟', ch: '第二十三回 · 第二十七回',
          titleEn: 'Song of Burying Flowers', chEn: 'Chapter 23 · Chapter 27',
          poem: ['花谢花飞花满天，红消香断有谁怜？', '尔今死去侬收葬，未卜侬身何日丧？'],
          poemEn: ['Flowers fade and fly, flowers fill the sky; / their red is spent, their scent is gone: who pities them?', 'Now you are dead, and I am here to bury you; / who knows the day when I myself shall die?'],
          prose: '黛玉肩上担着花锄，锄上挂着花囊，手里拿着花帚。她说花撂在水里，流出园子仍旧糟蹋，不如装在绢袋里埋起来，日久随土化了，岂不干净。',
          proseEn: 'Daiyu carries a flower-hoe on her shoulder, a gauze bag hung from it, and a broom in her hand. Throw the petals in the water, she says, and they only drift out of the garden to be spoiled; better to put them in a silk bag and bury them, to go back to earth in time. Isn’t that cleaner?',
          season: 0, hour: 17.5
        }
      },
      {
        title: '借书与香菱', at: [2, 16], want: '香菱一心想学作诗，来求你教。',
        titleEn: 'A Book for Xiangling', wantEn: 'Xiangling has set her heart on learning to write poetry, and comes to beg you to teach her.',
        pick: { place: 'xiaoxiang', kind: 'item', item: 'book', label: '王右丞五言律', verb: '取出', tip: '在潇湘馆取出王维的五言律诗集。',
          labelEn: 'Wang Wei’s regulated verse', verbEn: 'Take out', tipEn: 'At Bamboo Lodge, take out your volume of Wang Wei’s five-character regulated verse.' },
        give: { place: 'hengwu', who: '香菱', color: '#c9a88a', verb: '借给', tip: '把诗集借给住在蘅芜苑的香菱。',
          whoEn: 'Xiangling', verbEn: 'Lend to', tipEn: 'Lend the book to Xiangling, who is staying at Alpinia Park.' },
        reveal: {
          title: '香菱咏月', ch: '第四十八回 · 第四十九回',
          titleEn: 'Xiangling Sings of the Moon', chEn: 'Chapter 48 · Chapter 49',
          poem: ['精华欲掩料应难，影自娟娟魄自寒。'],
          poemEn: ['Such radiance would be hidden, but how could it be? / Its shadow so lovely, and its soul so cold.'],
          prose: '黛玉让她先读透王维的五言律一百首，再读杜甫、李白。香菱茶饭无心，坐卧不定，连作三首咏月诗，第三首梦中得来，众人都说新巧有意趣。',
          proseEn: 'Daiyu has her first master a hundred of Wang Wei’s five-character regulated poems, then go on to Du Fu and Li Bai. Xiangling forgets to eat and cannot sit or lie still; she writes three poems on the moon one after another, the third of them found in a dream, and everyone declares it fresh, clever and full of feeling.',
          hour: 21.5
        }
      }
    ]
  },
  xiangyun: {
    name: '史湘云', short: '湘云', home: '史侯府（客居园中）', start: 'gate', season: 1, hour: 15,
    nameEn: 'Shi Xiangyun', shortEn: 'Xiangyun', homeEn: 'the Shi mansion (a guest in the garden)',
    look: { robe: '#c98a4e', robe2: '#a86d3b', sash: '#3f5f6e', crown: false },
    line: '贾母的侄孙女，常来园中小住。心直口快，爱说爱笑。',
    lineEn: 'Grandniece of the Matriarch, often in the garden for a stay. Frank and quick of tongue, always talking, always laughing.',
    quests: [
      {
        title: '绛纹石戒指', at: [1, 15], want: '上回打发人送了戒指给姐妹们，这回亲自带来给袭人她们。',
        titleEn: 'The Carnelian Rings', wantEn: 'Last time you sent rings to the girls by a servant; this time you have brought some yourself, for Xiren and the others.',
        pick: { place: 'gate', kind: 'item', item: 'ring', label: '绛纹石戒指', verb: '取出', tip: '在正门进园前，取出带来的绛纹石戒指。',
          labelEn: 'the carnelian rings', verbEn: 'Take out', tipEn: 'At the Main Gate, before you go in, take out the carnelian rings you brought.' },
        give: { place: 'yihong', who: '袭人', color: '#c7a3a0', verb: '送给', tip: '把戒指送到怡红院，交给袭人。',
          whoEn: 'Xiren', verbEn: 'Give to', tipEn: 'Take the rings to Happy Red Court and give them to Xiren.' },
        reveal: {
          title: '因麒麟伏白首双星', ch: '第三十一回',
          titleEn: 'A Kylin Foretells a White-Haired Pair', chEn: 'Chapter 31',
          poem: [], poemEn: [],
          prose: '湘云来园中，特意带了绛纹石戒指，一包四个，分给袭人、鸳鸯、金钏、平儿。袭人笑说前日已收过她打发人送来的，知她心里时时记着人。',
          proseEn: 'Coming to the garden, Xiangyun has brought carnelian rings on purpose, four to a packet, for Xiren, Yuanyang, Jinchuan and Pinger. Xiren laughs that she already had the ones sent over the other day, and knows that Xiangyun keeps people always in her thoughts.',
          season: 1, hour: 15.5
        }
      },
      {
        title: '螃蟹宴', at: [2, 14.5], want: '起了诗社要做东，可手头短。宝姐姐说替你张罗螃蟹。',
        titleEn: 'The Crab Feast', wantEn: 'The poetry club is founded and it is your turn to host, but your purse is thin. Cousin Baochai says she will see to the crabs for you.',
        pick: { place: 'hengwu', kind: 'npc', who: '薛宝钗', color: '#e5d9b6', item: 'crab', label: '几篓螃蟹', verb: '从宝钗处领', tip: '去蘅芜苑，从宝钗处领几篓肥螃蟹。',
          whoEn: 'Xue Baochai', labelEn: 'baskets of crabs', verbEn: 'Collect from Baochai', doEn: 'Collect the baskets of crabs from Baochai', tipEn: 'Go to Alpinia Park and collect a few baskets of fat crabs from Baochai.' },
        give: { place: 'ouxiang', who: '贾母', color: '#6d5a48', verb: '摆给', tip: '把螃蟹带到藕香榭，请老太太和众人赏桂吃蟹。',
          whoEn: 'Grandmother Jia', verbEn: 'Serve to', doEn: 'Set the feast before Grandmother Jia', tipEn: 'Bring the crabs to Lotus Fragrance Pavilion and invite the Matriarch and everyone to eat crabs beneath the osmanthus.' },
        reveal: {
          title: '菊花诗', ch: '第三十七回 · 第三十八回',
          titleEn: 'The Chrysanthemum Poems', chEn: 'Chapter 37 · Chapter 38',
          poem: ['欲讯秋情众莫知，喃喃负手叩东篱。'],
          poemEn: ['I would ask autumn’s heart, but no one knows; / murmuring, hands behind me, I knock at the eastern hedge.'],
          prose: '宝钗让家里伙计送来几篓极肥极大的螃蟹，替湘云在藕香榭做东。众人赏桂吃蟹，又作菊花诗十二题，黛玉《咏菊》《问菊》《菊梦》夺魁。',
          proseEn: 'Baochai has the men from her family’s shop send over several baskets of the biggest, fattest crabs, so that Xiangyun can play host at Lotus Fragrance Pavilion. They eat crabs beneath the osmanthus and write chrysanthemum poems on twelve themes; Daiyu’s “Ode to the Chrysanthemum”, “Questioning the Chrysanthemum” and “Chrysanthemum Dream” carry off the prize.',
          hour: 15.5
        }
      }
    ]
  }
};

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
const dockBtn = document.createElement('button');
const dockLang = () => { dockBtn.textContent = L('入园', 'Play'); dockBtn.title = L('选一个人入园', 'Choose someone and enter the garden'); };
{ const b = dockBtn; b.className = 'tbtn'; b.id = 'btn-game'; dockLang();
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
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; } });
  return g;
}
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
const S = { char: null, q: 0, stage: 'pick', petals: 0, carrying: null, objects: [], targets: [], tags: [], gift: null, done: {} };
try { Object.assign(S.done, JSON.parse(localStorage.getItem('dgy-game-done') || '{}')); } catch (e) {}
const saveDone = () => { try { localStorage.setItem('dgy-game-done', JSON.stringify(S.done)); } catch (e) {} };

function clearWorld() { for (const o of S.objects) scene.remove(o); S.objects = []; S.targets = []; for (const t of S.tags) t.el.remove(); S.tags = []; beacon.visible = groundRing.visible = false; }
function addTag(text, obj, dy, goal) { const el = document.createElement('div'); el.className = 'g-tag ui' + (goal ? ' goal' : ''); el.textContent = txt(text); document.body.appendChild(el); const t = { el, obj, dy, goal, text }; S.tags.push(t); return t; }
function place(obj, v, faceTo) { obj.position.copy(v); if (faceTo) obj.rotation.y = Math.atan2(faceTo.x - v.x, faceTo.z - v.z); scene.add(obj); S.objects.push(obj); return obj; }

/* 根据当前阶段布置场景：本阶段要互动的东西 + 光柱 */
function stageWorld() {
  clearWorld(); if (!S.char) return;
  const Q = CHARS[S.char].quests[S.q]; if (!Q) return;
  const P = Q.pick, G = Q.give;
  // 收礼人/花冢一直在场，让玩家先认得去处
  const ga = anchor(G.place);
  if (G.kind === 'mound') { const v = ga.off(2.4); const m = place(makeItem('mound'), v); S.targets.push({ stage: 'give', obj: m, pos: v, r: 2.2, label: () => giveDo(G) }); addTag(() => T(G, 'who'), m, 1.0, S.stage === 'give'); }
  else { const v = new V3(ga.x, ga.y, ga.z); const f = place(makeFigure(G.color, G.who !== '李纨' ? true : true), v, new V3(ga.spawn[0], 0, ga.spawn[1])); S.targets.push({ stage: 'give', obj: f, pos: v, r: 2.4, label: () => giveDo(G) }); addTag(() => T(G, 'who'), f, 2.15, S.stage === 'give'); }
  if (S.stage === 'pick') {
    if (P.kind === 'petals') { ringPoints(P.place, P.n).forEach((v, i) => { if (i < S.petals) return; const o = place(makeItem('petal'), v); S.targets.push({ stage: 'pick', obj: o, pos: v, r: 1.8, label: () => L('拾起落花', 'Gather fallen petals'), petal: true, bob: 0 }); }); }
    else if (P.kind === 'npc') { const a = anchor(P.place); const v = P.place === G.place ? a.off(3) : new V3(a.x, a.y, a.z); const f = place(makeFigure(P.color, true), v, new V3(a.spawn[0], 0, a.spawn[1])); S.targets.push({ stage: 'pick', obj: f, pos: v, r: 2.4, label: () => pickDo(P) }); addTag(() => T(P, 'who'), f, 2.15, true); }
    else { const a = anchor(P.place); const v = P.place === G.place ? a.off(3) : a.off(2.2); v.y += 0.85; const o = place(makeItem(P.item), v); o.userData.baseY = v.y; S.targets.push({ stage: 'pick', obj: o, pos: v, r: 2.0, label: () => pickDo(P), bob: 1 }); addTag(() => T(P, 'label'), o, 0.55, true); }
  }
  renderQuest();
}
function currentGoal() { const t = S.targets.filter(t => t.stage === S.stage); if (!t.length) return null; const p = walk.pos; t.sort((a, b) => a.pos.distanceToSquared(p) - b.pos.distanceToSquared(p)); return t[0]; }

/* ---------------------------------------------------------------------
   界面渲染
   --------------------------------------------------------------------- */
function renderQuest() {
  if (!S.char) { questEl.hidden = true; return; }
  const C = CHARS[S.char], Q = C.quests[S.q];
  const dots = C.quests.map((_, i) => `<i class="${i < S.q || (i === S.q && S.stage === 'done') ? 'on' : ''}"></i>`).join('');
  if (!Q) { questEl.innerHTML = `<div class="who"><b>${esc(T(C, 'name'))}</b><span>${L('心事已了', 'Wishes fulfilled')}</span></div><p class="tip">${L('在园中随意走走，或按「入园」换一个人。', 'Wander the garden as you please, or press “Play” to choose someone else.')}</p><div class="dots">${dots}</div>`; questEl.hidden = !walk.on; return; }
  const tip = S.stage === 'pick' ? (Q.pick.kind === 'petals' ? `${T(Q.pick, 'tip')}${L('（', ' (')}${S.petals}/${Q.pick.n}${L('）', ')')}` : T(Q.pick, 'tip')) : T(Q.give, 'tip');
  questEl.innerHTML = `<div class="who"><b>${esc(T(C, 'name'))}</b><span>${L('心事', 'Wish')} ${S.q + 1}/${C.quests.length} · ${esc(T(Q, 'title'))}</span></div><p class="want">${esc(T(Q, 'want'))}</p><p class="tip">${esc(tip)}</p>${S.carrying ? `<div class="bag">${L('随身：', 'Carrying: ')}${esc(txt(S.carrying))}</div>` : ''}<div class="dots">${dots}</div>`;
  questEl.hidden = !walk.on;
  for (const t of S.tags) t.el.classList.toggle('goal', t.goal || (S.stage === 'give' && t.obj === (S.targets.find(x => x.stage === 'give') || {}).obj));
}
function charCard(k) { const C = CHARS[k]; const done = S.done[k] ? L(' · 已完成', ' · completed') : '';
  return `<button class="g-char" data-k="${k}"><span class="sw" style="background:${C.look.robe}"></span><b>${esc(T(C, 'name'))}</b><small>${esc(T(C, 'home'))}${done}</small><p>${esc(T(C, 'line'))}</p><ol>${C.quests.map(q => `<li>${esc(T(q, 'title'))}</li>`).join('')}</ol></button>`; }
function showStart(giftMode) {
  pauseGame(true);
  if (walk.on) exitWalk();
  if (giftMode && S.gift) {
    const g = S.gift, p = placeById(g.p) || placeById('qinfang');
    startEl.innerHTML = EN()
      ? `<div class="g-sheet"><h2>A Gift in the Garden</h2><p class="g-lead"><b>${esc(g.f || 'Someone')}</b> has left ${esc(g.t ? g.t : 'you')} a gift at <b>${esc(pname(p))}</b> in the Grand View Garden: ${esc(g.n || 'a brocade box')}. Walk there in the garden and you can open it.</p><div class="g-foot"><button class="g-btn" id="g-go-gift">Enter and find it</button><button class="g-link" id="g-skip">Not yet, just look around</button></div></div>`
      : `<div class="g-sheet"><h2>园中有礼</h2><p class="g-lead"><b>${esc(g.f || '有人')}</b>在大观园的<b>${esc(p.name)}</b>给${esc(g.t ? g.t : '你')}留了一份礼：${esc(g.n || '一只锦盒')}。进园走到那里，就能打开它。</p><div class="g-foot"><button class="g-btn" id="g-go-gift">入园寻礼</button><button class="g-link" id="g-skip">先不打开，随便看看</button></div></div>`;
    startEl.dataset.mode = 'gift';
    startEl.hidden = false;
    $('g-go-gift').onclick = () => { startEl.hidden = true; beginGift(); };
    $('g-skip').onclick = () => { startEl.hidden = true; pauseGame(false); };
    return;
  }
  startEl.dataset.mode = '';
  startEl.innerHTML = `<div class="g-sheet"><h2>${L('我们的大观园', 'Our Grand View Garden')}</h2>
   <p class="g-lead">${L('大观园本是贾府为元妃省亲造的一份礼。园中人也总以物寄情：一方旧帕，一枝红梅，几篓螃蟹。选一个人入园，替园中人把心意送到。', 'The Grand View Garden was itself a gift, built by the Jia family for the Imperial Consort’s visit home. Those who live in it speak their hearts through things, too: an old handkerchief, a sprig of red plum, a few baskets of crabs. Choose someone, enter the garden, and carry their feelings to where they belong.')}</p>
   <div class="g-chars">${Object.keys(CHARS).map(charCard).join('')}</div>
   <div class="g-foot"><button class="g-link" id="g-skip">${L('只是逛逛', 'Just wander')}</button><form class="g-recv" id="g-recv"><input id="g-code-in" placeholder="${L('有赠礼码？贴在这里', 'Have a gift code? Paste it here')}" aria-label="${L('赠礼码', 'Gift code')}"><button class="g-btn ghost" type="submit">${L('收礼', 'Receive')}</button></form></div></div>`;
  startEl.hidden = false;
  startEl.querySelectorAll('.g-char').forEach(b => b.onclick = () => { startEl.hidden = true; beginChar(b.dataset.k); });
  $('g-skip').onclick = () => { startEl.hidden = true; pauseGame(false); document.body.classList.remove('g-playing'); };
  $('g-recv').onsubmit = (e) => { e.preventDefault(); const g = decodeGift($('g-code-in').value.trim()); if (!g) { $('g-code-in').value = ''; $('g-code-in').placeholder = L('这个码打不开，再检查一下', 'That code won’t open. Please check it'); return; } S.gift = g; showStart(true); };
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
  startEl.hidden = true;
  S.char = k; S.q = 0; S.stage = 'pick'; S.petals = 0; S.carrying = null; S.giftMode = false;
  const C = CHARS[k]; dressHero(C.look); const a0 = C.quests[0].at; setWorld(a0[0], a0[1]);
  document.body.classList.add('g-playing'); pauseGame(false);
  stageWorld(); enterWalk(spawnAt(C.start)); renderQuest();
}
function beginGift() {
  S.char = null; S.giftMode = true; clearWorld(); document.body.classList.add('g-playing'); pauseGame(false);
  const g = S.gift, id = placeById(g.p) ? g.p : 'qinfang', a = anchor(id); const v = a.off(2.2);
  const o = place(makeItem('gift'), v); S.targets = [{ stage: 'gift', obj: o, pos: v, r: 2.2, label: () => L('打开' + (g.f ? g.f + '的' : '') + '礼', g.f ? `Open ${g.f}’s gift` : 'Open the gift') }]; S.stage = 'gift'; addTag(() => L('给你的礼', 'A gift for you'), o, 0.7, true);
  renderGiftQuest();
  enterWalk(spawnAt(id)); questEl.hidden = false;
}
function renderGiftQuest() {
  const g = S.gift, id = placeById(g.p) ? g.p : 'qinfang', pn = esc(pname(placeById(id)));
  questEl.innerHTML = `<div class="who"><b>${L('收礼', 'A Gift')}</b><span>${pn}</span></div><p class="tip">${EN() ? `${esc(g.f || 'Someone')} left the gift at ${pn}. Follow the beam of light.` : `${esc(g.f || '有人')}把礼放在了${pn}。跟着光柱走过去。`}</p>`;
}
function interact() {
  const t = S.near; if (!t || t.stage !== S.stage || !t.obj.parent) return; S.near = null;
  if (S.stage === 'gift') { openGift(); return; }
  const C = CHARS[S.char], Q = C.quests[S.q];
  if (S.stage === 'pick') {
    if (t.petal) { scene.remove(t.obj); S.targets = S.targets.filter(x => x !== t); S.petals++; { const n = S.petals; S.carrying = () => L(`落花 ${n} 捧`, `${n} handful${n > 1 ? 's' : ''} of petals`); } blip(660);
      if (S.petals >= Q.pick.n) { S.stage = 'give'; S.carrying = () => L('一囊落花', 'a bag of fallen petals'); flash(L('收了一囊落花', 'A bagful of fallen petals gathered')); }
      renderQuest(); return; }
    { const P = Q.pick; S.carrying = () => T(P, 'label'); } S.stage = 'give'; blip(660);
    flash(EN() ? (Q.pick.kind === 'npc' ? `${Q.pick.whoEn} gives you ${Q.pick.labelEn}` : `You take ${Q.pick.labelEn}`) : (Q.pick.kind === 'npc' ? `${Q.pick.who}给了你${Q.pick.label}` : `取了${Q.pick.label}`));
    stageWorld(); return;
  }
  if (S.stage === 'give') { S.stage = 'done'; S.carrying = null; blip(880); clearWorld(); reveal(Q); }
}
function reveal(Q) {
  const R = Q.reveal; setWorld(R.season, R.hour);
  openModal(() => `<div class="ey">${esc(T(R, 'ch'))}</div><h3>${esc(T(R, 'title'))}</h3>${R.poem.length ? `<p class="poem">${R.poem.map(esc).join('<br>')}</p>` : ''}${EN() && R.poemEn && R.poemEn.length ? `<p class="prose" style="text-align:center;font-style:italic">${R.poemEn.map(l => esc(l).replace(/ \/ /g, '<br>')).join('<br><br>')}</p>` : ''}<p class="prose">${esc(T(R, 'prose'))}</p><div class="ch">${EN() ? `See <i>Dream of the Red Chamber</i>, ${esc(R.chEn.split(' · ')[0])}` : `见《红楼梦》${esc(R.ch.split(' · ')[0])}`}</div><button class="g-btn" id="g-next">${L('继续', 'Continue')}</button>`,
    () => { S.q++; S.stage = 'pick'; S.petals = 0; const C = CHARS[S.char];
      if (S.q >= C.quests.length) { S.done[S.char] = 1; saveDone(); giftForm(); } else { const n = C.quests[S.q]; setWorld(n.at[0], n.at[1]); stageWorld(); flash(L('新的心事 · ', 'A new wish · ') + T(n, 'title')); } });
}

/* ---------------------------------------------------------------------
   赠一份礼：写给现实中的一个人，生成赠礼码
   --------------------------------------------------------------------- */
function encodeGift(g) { const s = btoa(unescape(encodeURIComponent(JSON.stringify(g)))); return 'DGY-' + s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function decodeGift(code) { try { let s = code.replace(/^.*#gift=/, '').replace(/^DGY-/, '').replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const g = JSON.parse(decodeURIComponent(escape(atob(s)))); return g && g.p ? g : null; } catch (e) { return null; } }
function giftForm() {
  const C = CHARS[S.char]; let keep = null, made = null;
  const showCode = (g, code) => { $('gf-out').innerHTML = `<div class="g-code" id="gf-code">${esc(code)}</div><p class="prose" style="margin-top:8px">${EN() ? `Send the code to them. They open the Grand View Garden, press “Play”, paste the code under “Receive”, and will be led to ${esc(pname(placeById(g.p)))} to find your gift.` : `把赠礼码发给对方。对方打开大观园，点「入园」，把码贴进「收礼」，就会被带到${esc(placeById(g.p).name)}，找到你的礼。`}</p>`; };
  const build = () => { // 切换语言重绘时保留已填写的内容
    if ($('gf-f')) { keep = {}; for (const k of 'ftnpm') keep[k] = $('gf-' + k).value; }
    const opts = PLACES.filter(p => p.pos).map(p => `<option value="${p.id}"${p.id === C.start ? ' selected' : ''}>${esc(pname(p))}</option>`).join('');
    return `<div class="ey">${esc(T(C, 'name'))} · ${L('心事已了', 'Wishes fulfilled')}</div><h3>${L('赠一份礼', 'Give a Gift')}</h3>
   <p class="prose">${L('大观园是元妃的礼，园中人又以物互赠。现在轮到你：把园子里的一处地方，连同一份礼和一句话，送给现实中的一个人。', 'The garden was a gift to the Imperial Consort, and those who lived in it gave gifts to one another. Now it is your turn: give a corner of the garden, with a gift and a few words, to someone in your own life.')}</p>
   <div class="g-form"><label for="gf-f">${L('你是', 'From')}</label><input id="gf-f" maxlength="12" placeholder="${L('署名', 'Your name')}">
   <label for="gf-t">${L('送给', 'To')}</label><input id="gf-t" maxlength="12" placeholder="${L('对方的名字', 'Their name')}">
   <label for="gf-n">${L('礼物', 'Gift')}</label><input id="gf-n" maxlength="24" placeholder="${L('想送的东西，如：一枝红梅', 'What to give, e.g. a sprig of red plum')}">
   <label for="gf-p">${L('放在', 'Leave it at')}</label><select id="gf-p">${opts}</select>
   <label for="gf-m">${L('留言', 'Message')}</label><textarea id="gf-m" maxlength="140" placeholder="${L('一句话', 'A few words')}"></textarea></div>
   <div id="gf-out"></div><button class="g-btn" id="gf-make">${L('生成赠礼码', 'Make a gift code')}</button> <button class="g-btn ghost" id="g-next">${L('以后再说', 'Maybe later')}</button>`; };
  const after = () => {
    if (keep) for (const k of 'ftnpm') $('gf-' + k).value = keep[k];
    if (made) { showCode(made.g, made.code); if (made.copied) $('gf-make').textContent = L('已复制', 'Copied'); }
    $('gf-make').onclick = () => {
      const g = { f: $('gf-f').value.trim(), t: $('gf-t').value.trim(), n: $('gf-n').value.trim(), p: $('gf-p').value, m: $('gf-m').value.trim() };
      const code = encodeGift(g); let link = ''; try { link = location.href.split('#')[0] + '#gift=' + code.slice(4); } catch (e) {}
      made = { g, code }; showCode(g, code);
      try { navigator.clipboard.writeText(code); $('gf-make').textContent = L('已复制', 'Copied'); made.copied = 1; } catch (e) {}
      void link;
    };
  };
  openModal(build, null, after);
}
function openGift() {
  const g = S.gift; clearWorld(); blip(990); S.stage = 'none';
  openModal(() => `<div class="ey">${esc(pname(placeById(g.p)) || '')}</div><h3>${esc(g.n || L('一份礼', 'A gift'))}</h3>${g.m ? `<p class="poem" style="font-size:22px">${esc(g.m)}</p>` : ''}<p class="prose" style="text-align:center">${EN() ? `${g.t ? esc(g.t) + ': ' : ''}${esc(g.f || 'Someone')} left this for you in the Grand View Garden.` : `${g.t ? esc(g.t) + '：' : ''}这是${esc(g.f || '有人')}在大观园里留给你的。`}</p><button class="g-btn" id="g-next">${L('收下', 'Accept')}</button>`,
    () => { S.giftMode = false; questEl.hidden = true; flash(L('也选一个人入园看看？', 'Why not choose someone and enter the garden too?')); setTimeout(() => { if (!walk.on) return; }, 0); });
}

/* ---------------------------------------------------------------------
   暂停 / 弹窗 / 小提示
   --------------------------------------------------------------------- */
function pauseGame(on) { window.__gamePause = on; if (on) { walk.keys = {}; walk.stick.x = walk.stick.y = 0; } }
let modalDone = null, modalPaint = null;
/* html 为返回 HTML 的函数，切换语言时可重绘；after 在每次绘制后绑定事件 */
function openModal(html, onDone, after) {
  pauseGame(true); walk.keys = {}; if (document.pointerLockElement) document.exitPointerLock();
  modalPaint = () => { scrollEl.innerHTML = txt(html); const n = $('g-next'); if (n) n.onclick = closeModal; if (after) after(); };
  modalPaint(); modalEl.hidden = false; modalDone = onDone; promptEl.hidden = true;
  const n = $('g-next'); if (n) setTimeout(() => n.focus(), 50);
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
  if (!modalEl.hidden) { e.stopImmediatePropagation(); if ((e.code === 'KeyE' || e.code === 'Enter' || e.code === 'Space') && $('g-next') && !$('gf-make')) { e.preventDefault(); closeModal(); } return; }
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
  const playing = (S.char || S.giftMode) && walk.on;
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
    const Q = S.char ? CHARS[S.char].quests[S.q] : null; const where = pname(S.giftMode ? placeById(S.gift.p) : placeById(S.stage === 'pick' ? Q.pick.place : Q.give.place));
    compassEl.hidden = d < 5; compassEl.querySelector('svg').style.transform = `rotate(${-rel}rad)`; compassEl.querySelector('b').textContent = where; compassEl.querySelector('span').textContent = Math.round(d / 0.75) + L(' 步', ' steps');
  } else { compassEl.hidden = true; beacon.visible = groundRing.visible = false; }
  // 最近的可交互目标
  let near = null; for (const t of S.targets) { if (t.stage !== S.stage) continue; const d = Math.hypot(t.pos.x - p.x, t.pos.z - p.z); if (d < t.r && Math.abs(t.pos.y - p.y) < 2.5) { near = t; break; } }
  S.near = modalEl.hidden ? near : null;
  if (S.near) { promptEl.innerHTML = isTouch ? `<span>${L('点这里', 'Tap here')}</span>${esc(txt(S.near.label))}` : `<kbd>E</kbd>${esc(txt(S.near.label))}`; promptEl.hidden = false; } else promptEl.hidden = true;
  // 头顶名签
  const W = innerWidth, H = innerHeight;
  for (const t of S.tags) { if (!t.obj.parent) { t.el.style.display = 'none'; continue; } _v.copy(t.obj.position); _v.y += t.dy; const dist = camera.position.distanceTo(_v); _v.project(camera);
    const vis = _v.z < 1 && dist < 60 && Math.abs(_v.x) < 1.1 && Math.abs(_v.y) < 1.1; t.el.style.display = vis ? '' : 'none';
    if (vis) { t.el.style.transform = `translate(${(_v.x * 0.5 + 0.5) * W}px,${(-_v.y * 0.5 + 0.5) * H}px) translate(-50%,-100%)`; t.el.style.opacity = dist > 35 ? 0.6 : 1; } }
}
requestAnimationFrame(tick);

/* 切换语言：重绘当前可见的界面与名签 */
addEventListener('dgy-lang', () => {
  dockLang();
  for (const t of S.tags) t.el.textContent = txt(t.text);
  if (S.char) renderQuest(); else if (S.giftMode && S.gift && S.stage === 'gift') renderGiftQuest();
  if (!startEl.hidden) showStart(startEl.dataset.mode === 'gift');
  if (!modalEl.hidden && modalPaint) modalPaint();
});

/* 调试接口（测试用） */
window.__game = { S, CHARS, beginChar, interact, anchor, stageWorld, encodeGift, decodeGift, showStart, closeModal, beginGift };

/* 开场：链接里带礼 → 收礼；否则显示选人 */
{ const g = decodeGift(location.hash || ''); if (g) { S.gift = g; showStart(true); } else showStart(); }
