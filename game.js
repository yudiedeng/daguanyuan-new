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
#g-prompt{all:unset;position:fixed;left:50%;top:60%;transform:translate(-50%,-50%);padding:12px 28px 12px 14px;border-radius:999px;font-size:clamp(21px,2.9vw,31px);font-weight:600;letter-spacing:.1em;cursor:pointer;z-index:40;display:flex;align-items:center;gap:16px;background:rgba(18,16,14,.8);color:#fff4dc;border:1.5px solid rgba(255,214,140,.8);box-shadow:0 8px 30px rgba(0,0,0,.5),0 0 0 6px rgba(255,214,140,.16);backdrop-filter:blur(4px);animation:gprompt 1.7s ease-in-out infinite;text-shadow:0 1px 2px rgba(0,0,0,.6)}
#g-prompt[hidden]{display:none}
#g-prompt kbd{font:inherit;font-weight:800;min-width:1.75em;height:1.75em;display:inline-flex;align-items:center;justify-content:center;padding:0 .35em;border:none;border-radius:9px;background:#ffd98a;color:#2a1c0a;box-shadow:0 3px 0 #b88a3a;text-shadow:none}
#g-prompt span{display:inline-flex;align-items:center;height:1.75em;padding:0 .7em;border-radius:9px;background:#ffd98a;color:#2a1c0a;font-weight:800;box-shadow:0 3px 0 #b88a3a;text-shadow:none;font-size:.8em;letter-spacing:.04em}
@keyframes gprompt{0%,100%{box-shadow:0 8px 30px rgba(0,0,0,.5),0 0 0 6px rgba(255,214,140,.16)}50%{box-shadow:0 8px 30px rgba(0,0,0,.5),0 0 0 14px rgba(255,214,140,.05)}}
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
.g-opts{display:grid;gap:8px;margin:14px 0 2px}
.g-opt{all:unset;box-sizing:border-box;cursor:pointer;padding:10px 14px;border:1px solid var(--line);border-radius:2px;background:rgba(255,255,255,.4);font-size:15px;line-height:1.7;letter-spacing:.03em;text-align:left;color:var(--ink)}
.g-opt:hover,.g-opt:focus-visible{border-color:var(--cinnabar);background:rgba(255,255,255,.75)}
.g-opt i{font-style:normal;font-size:12px;color:var(--cinnabar);margin-right:8px}
#g-intro{position:fixed;inset:0;z-index:60;background:#07080a;color:#e9e3d3;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:opacity 1.6s ease;user-select:none}
#g-intro[hidden]{display:none}
#g-intro.out{opacity:0;pointer-events:none}
#g-intro .ln{font-family:var(--f-disp);font-size:clamp(27px,4.6vw,54px);letter-spacing:.12em;line-height:1.95;max-width:1120px;padding:0 28px;text-align:center;opacity:0;transform:translateY(8px);transition:opacity 1.3s ease,transform 1.3s ease}
#g-intro .ln.on{opacity:1;transform:none}
#g-intro .ln.ey{font-family:inherit;font-size:clamp(17px,2.2vw,24px);letter-spacing:.3em;color:#b39a6a}
#g-intro .ln.big{font-size:clamp(38px,6.6vw,76px);letter-spacing:.18em}
#g-intro .hint{position:absolute;left:0;right:0;bottom:calc(30px + env(safe-area-inset-bottom,0px));text-align:center;font-size:clamp(15px,1.8vw,20px);letter-spacing:.22em;color:#8d887b;animation:gpulse 2.4s ease-in-out infinite}
#g-intro .skip{all:unset;position:absolute;right:22px;top:calc(18px + env(safe-area-inset-top,0px));font-size:clamp(15px,1.8vw,20px);letter-spacing:.12em;color:#9a9486;cursor:pointer;border-bottom:1px solid #4a4740}
#g-intro .skip:hover,#g-intro .skip:focus-visible{color:#e9e3d3}
@keyframes gpulse{0%,100%{opacity:.35}50%{opacity:.9}}
#g-fade{position:fixed;inset:0;z-index:58;background:#07080a;opacity:0;pointer-events:none;transition:opacity 1.1s ease;display:flex;align-items:center;justify-content:center}
#g-fade.on{opacity:1;pointer-events:auto}
#g-blink{position:fixed;inset:0;z-index:44;background:#07080a;opacity:0;pointer-events:none;transition:opacity .25s ease}#g-blink.on{opacity:1}
#g-fade p{font-family:var(--f-disp);font-size:clamp(20px,3vw,28px);letter-spacing:.16em;color:#e9e3d3;max-width:720px;padding:0 28px;text-align:center;line-height:2}
#g-lids{position:fixed;inset:0;z-index:59;pointer-events:none}
#g-lids[hidden]{display:none}
#g-lids i{position:absolute;left:-15%;width:130%;height:56%;background:#07080a}
#g-lids i:first-child{top:0;border-radius:0 0 50% 50%/0 0 34% 34%;animation:glidT 3.6s cubic-bezier(.4,0,.2,1) forwards}
#g-lids i:last-child{bottom:0;border-radius:50% 50% 0 0/34% 34% 0 0;animation:glidB 3.6s cubic-bezier(.4,0,.2,1) forwards}
@keyframes glidT{0%{transform:translateY(0)}22%{transform:translateY(-22%)}34%{transform:translateY(-4%)}62%{transform:translateY(-58%)}74%{transform:translateY(-46%)}100%{transform:translateY(-110%)}}
@keyframes glidB{0%{transform:translateY(0)}22%{transform:translateY(22%)}34%{transform:translateY(4%)}62%{transform:translateY(58%)}74%{transform:translateY(46%)}100%{transform:translateY(110%)}}
@media (prefers-reduced-motion:reduce){#g-intro .ln{transition:opacity .6s}#g-lids i{animation-duration:1.2s}#g-intro .hint{animation:none}}
@media (max-width:760px){.g-chars{grid-template-columns:1fr}.g-sheet{padding:20px 18px}.g-sheet h2{font-size:34px}.g-char ol{display:none}#g-quest{top:auto;bottom:calc(170px + env(safe-area-inset-bottom,0px));width:auto;right:16px}#g-prompt{bottom:calc(150px + env(safe-area-inset-bottom,0px))}.g-scroll{padding:24px 20px}.g-scroll .poem{font-size:20px}}
@media (prefers-reduced-motion:reduce){#g-compass svg{transition:none}}
`;
document.head.insertAdjacentHTML('beforeend', `<style>${css}</style>`);
document.body.insertAdjacentHTML('beforeend', `
<div id="g-intro" hidden role="dialog" aria-modal="true" aria-live="polite"></div>
<div id="g-lids" hidden><i></i><i></i></div>
<div id="g-fade"><p></p></div>
<div id="g-blink"></div>
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
function makeFigure(color, female = true, sit = false) {
  const g = new THREE.Group(), robe = std(color, .85), dark = std(new THREE.Color(color).multiplyScalar(0.8).getStyle(), .85), skin = std('#efd3bb', .6), hair = std('#16130f', .5);
  const prof = [[0, 0], [0.31, 0], [0.29, 0.15], [0.25, 0.55], [0.2, 0.9], [0.18, 1.08]].map(p => new THREE.Vector2(p[0], p[1]));
  const sk = new THREE.Mesh(new THREE.LatheGeometry(prof, 18), robe); sk.position.y = 0.05; g.add(sk);
  const to = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.19, 0.42, 14), robe); to.position.y = 1.3; g.add(to);
  for (const s of [-1, 1]) { const a = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.12, 0.5, 10), dark); a.position.set(s * 0.2, 1.24, 0.04); a.rotation.set(-0.35, 0, s * 0.12); g.add(a); }
  const hd = new THREE.Mesh(new THREE.SphereGeometry(0.11, 18, 14), skin); hd.scale.y = 1.1; hd.position.y = 1.67; g.add(hd);
  const hr = new THREE.Mesh(new THREE.SphereGeometry(0.117, 18, 10, 0, Math.PI * 2, 0, Math.PI * 0.55), hair); hr.rotation.x = -0.35; hr.position.set(0, 1.69, -0.012); g.add(hr);
  if (female) { for (const s of [-1, 1]) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.055, 12, 8), hair); b.position.set(s * 0.08, 1.8, -0.04); g.add(b); } }
  else { const b = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 8), hair); b.position.set(0, 1.81, -0.03); g.add(b); }
  if (sit) {   // 坐姿：原点在座面上。裙摆压扁摊在座上，上身整体降到座面，双膝向前，小腿垂下
    const lap = g.children[0]; lap.scale.y = 0.3;
    for (let i = 1; i < g.children.length; i++) { const ch = g.children[i]; ch.position.y -= 0.93; }
    for (const ch of g.children) if (ch.geometry && ch.geometry.type === 'CylinderGeometry' && ch.rotation.z !== 0) ch.rotation.x = -0.85;
    const darkM = std(new THREE.Color(color).multiplyScalar(0.6).getStyle(), .85);
    for (const s of [-1, 1]) {
      const knee = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 0.44), lap.material); knee.position.set(s * 0.1, 0.17, 0.28); g.add(knee);
      const shin = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.045, 0.5, 8), darkM); shin.position.set(s * 0.1, -0.1, 0.5); g.add(shin);
      const foot = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.05, 0.18), darkM); foot.position.set(s * 0.1, -0.36, 0.56); g.add(foot);
    }
  }
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.scale.setScalar(walk.s);   // 与主角同比例
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
  if (S.story) { renderStory(); return; }
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
   <div class="g-foot"><span><button class="g-btn" id="g-liu">${L('刘姥姥进大观园', 'Granny Liu Visits the Garden')}</button> <button class="g-link" id="g-skip">${L('只是逛逛', 'Just wander')}</button></span><form class="g-recv" id="g-recv"><input id="g-code-in" placeholder="${L('有赠礼码？贴在这里', 'Have a gift code? Paste it here')}" aria-label="${L('赠礼码', 'Gift code')}"><button class="g-btn ghost" type="submit">${L('收礼', 'Receive')}</button></form></div></div>`;
  startEl.hidden = false;
  startEl.querySelectorAll('.g-char').forEach(b => b.onclick = () => { startEl.hidden = true; beginChar(b.dataset.k); });
  $('g-liu').onclick = () => { startEl.hidden = true; liuIntro(); };
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
  startEl.hidden = true; S.story = null; if (banEr) scene.remove(banEr); putFlowers(false);
  S.char = k; S.q = 0; S.stage = 'pick'; S.petals = 0; S.carrying = null; S.giftMode = false;
  const C = CHARS[k]; dressHero(C.look); const a0 = C.quests[0].at; setWorld(a0[0], a0[1]);
  document.body.classList.add('g-playing'); pauseGame(false);
  stageWorld(); walk.third = false; enterWalk(spawnAt(C.start)); renderQuest();
}
/* =====================================================================
   刘姥姥进大观园：开场引导（第三十九回末 · 第四十回开头）
   黑屏旁白 → 睁眼 → 正门外清早，板儿跟在身边 → 进门找丰儿 → 到大观楼下见李纨
   旁白、对白为转述；揭示里引号内为原文
   ===================================================================== */
const LIU = {
  name: '刘姥姥', nameEn: 'Granny Liu',
  look: { robe: '#56606c', robe2: '#47505b', sash: '#8b7a55', crown: false },
  spawn: [0, 131, 0], season: 2, hour: 7.2,
  intro: [
    ['第三十九回 · 第四十回', 'Chapters 39 · 40', 'ey'],
    ['你是刘姥姥，今年七十五岁，住在城外的庄子上。', 'You are Granny Liu, seventy-five years old, living on a farm outside the city.'],
    ['秋收过后，你带着外孙板儿，背了些新摘的枣子、倭瓜和野菜，进城来荣国府走动。', 'After the autumn harvest you brought your grandson Ban’er into the city to call on the Rongguo mansion, with fresh-picked dates, squashes and wild greens.'],
    ['老太太和你投缘，留你住下，说园子里也有果子，明儿叫你尝尝。', 'The old lady took to you, kept you for the night, and said there was fruit in the garden for you to try tomorrow.'],
    ['人人都说大观园好。你只在年下买的画儿上见过那样的地方，总想着画儿不过是假的，哪里有这个真地方呢。', 'Everyone says the Grand View Garden is wonderful. You have only seen such places in New Year prints, and always thought them make-believe — how could there be such a place?'],
    ['次日清早，天气清朗。', 'The next morning broke clear and bright.'],
    ['这是你头一回进大观园。', 'This is your first time in the Grand View Garden.', 'big']
  ],
  /* 每一步：npcs 第一位是要找的人（光柱指向她），其余站在旁边；pages 依次弹出：
     say = 对白 [谁, 谁En, 话, 话En]（谁为空即旁白）；ask = 选择回话；text = 第几回原文揭示。
     位置函数返回 [x, z]，qf() 是沁芳亭桥心。 */
  steps: [
    { tip: '进园门去。凤姐的丫头丰儿在门里等你。', tipEn: 'Go in through the gate. Xifeng’s maid Feng’er is waiting just inside.',
      label: '和丰儿说话', labelEn: 'Talk to Feng’er', where: '正门', whereEn: 'Main Gate', face: () => [0, 131],
      npcs: [{ who: '丰儿', whoEn: 'Feng’er', color: '#c08c86', at: () => [6, 110] }],
      pages: [{ say: [['丰儿', 'Feng’er', '姥姥起得早。我们奶奶叫我先领您和板儿进园子，找大奶奶去——大奶奶一早就在大观楼底下张罗呢。', 'Up early, Granny! My mistress told me to take you and Ban’er into the garden to find Madam Li Wan — she’s been busy under the Grand View Tower since dawn.'],
                      ['刘姥姥', 'Granny Liu', '好姑娘，劳动你了。', 'Bless you, my dear, for the trouble.']], btn: ['跟她走', 'Follow her'] }] },
    { tip: '跟着前面的丰儿走，过沁芳亭，到大观楼底下找大奶奶李纨。（走丢了就跟着光柱）', tipEn: 'Follow Feng’er ahead of you, past Drenched Blossoms Pavilion, to Li Wan under the Grand View Tower. (If you lose her, follow the beam of light.)',
      label: '见李纨', labelEn: 'Greet Li Wan', place: 'daguan',
      npcs: [{ who: '李纨', whoEn: 'Li Wan', color: '#8e8a80', anchor: 'daguan' }, { who: '丰儿', whoEn: 'Feng’er', color: '#c08c86', anchor: 'daguan', off: 2.2, guide: true }],
      pages: [{ text: { title: '史太君两宴大观园', titleEn: 'The Lady Dowager Feasts in the Garden', ch: '第四十回', chEn: 'Chapter 40',
        p: ['李纨一早起来，正看着老婆子丫头们扫那些落叶，擦抹桌椅，预备茶酒器皿。丰儿带了你和板儿进来，说：“大奶奶倒忙的很。”李纨笑道：“我说你昨儿去不成，只忙着要去。”你笑道：“老太太留下我，叫我也热闹一天去。”',
            '李纨叫人上去开了缀锦阁，把桌椅一张一张往下抬。你巴不得一声儿，拉了板儿登梯上去，只见乌压压的堆着些围屏、桌椅、大小花灯，虽不大认得，只见五彩炫耀，各有奇妙。你念了几声佛，便下来了。',
            '不多时，老太太已带了一群人进园来了。'],
        pEn: ['Li Wan had risen at dawn and was watching the women sweep up fallen leaves, wipe down tables and set out tea and wine things. Feng’er brought you and Ban’er in: “Madam is busy indeed.” Li Wan laughed: “I said you wouldn’t get away yesterday, you were in such a hurry to go.” You laughed: “The old lady kept me, so I could join in the fun for a day.”',
              'Li Wan had the Brocade Pavilion opened and the tables carried down one by one. You couldn’t wait — you pulled Ban’er up the ladder and found the place crammed with screens, tables, chairs and lanterns great and small; you hardly knew what any of it was, only that it dazzled in every colour. You called on the Buddha a few times and came back down.',
              'Before long, the old lady arrived in the garden with a whole crowd behind her.'] } }] },
    { tip: '老太太进园了。随大奶奶往回迎，到沁芳亭南头见老太太。', tipEn: 'The old lady has come into the garden. Go back with Li Wan to meet her at the south end of Drenched Blossoms Pavilion.',
      label: '迎老太太', labelEn: 'Greet the old lady', where: '沁芳亭', whereEn: 'Drenched Blossoms Pavilion', face: () => { const [x, z] = qf(); return [x, z - 20]; },
      npcs: [{ who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => { const [x, z] = qf(); return [x, z + 13]; } },
             { who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => { const [x, z] = qf(); return [x - 1.6, z + 14]; } },
             { who: '凤姐', whoEn: 'Wang Xifeng', color: '#b6463c', at: () => { const [x, z] = qf(); return [x + 1.8, z + 13.6]; } },
             { who: '碧月', whoEn: 'Biyue', color: '#c9b07a', at: () => { const [x, z] = qf(); return [x + 0.9, z + 11.4]; } }],
      pages: [{ say: [['', '', '碧月早捧过一个大荷叶式的翡翠盘子来，里面养着各色的折枝菊花。老太太便拣了一朵大红的簪于鬓上，回头看见了你，忙笑道：', 'Biyue had already brought up a great jade dish shaped like a lotus leaf, holding sprays of chrysanthemums of every colour. The old lady picked a big red one and pinned it at her temple, then turned, saw you, and laughed:'],
                      ['贾母', 'The Lady Dowager', '过来带花儿。', 'Come and wear some flowers.'],
                      ['', '', '一语未完，凤姐便拉过你，笑道：“让我打扮你。”说着，将一盘子花横三竖四的插了一头。老太太和众人笑的了不得。', 'Before she had finished, Xifeng pulled you over: “Let me dress you up!” — and stuck the whole dishful of flowers every which way all over your head. The old lady and everyone laughed fit to burst.']], btn: ['……', '…'], then: 'flowers' },
              { ask: { q: ['众人笑道：“你还不拔下来摔到她脸上呢，把你打扮的成了个老妖精了。”你怎么回？', 'Everyone laughed: “Pull them out and throw them in her face! She’s made you into an old witch!” What do you say?'],
                  opts: [{ t: ['我虽老了，年轻时也风流，爱个花儿粉儿的，今儿老风流才好。', 'I may be old, but I was a flirt in my day and loved my flowers and powder — today I’ll be an old flirt!'], best: 1 },
                         { t: ['哎哟，这么好的花儿，可别糟蹋了。', 'Oh my, such lovely flowers — mustn’t waste them.'] },
                         { t: ['（不说话，只摸着一头的花傻笑）', '(Say nothing; just pat the flowers on your head and grin.)'] }],
                  after: ['你索性笑道：“我虽老了，年轻时也风流，爱个花儿粉儿的，今儿老风流才好。”', 'Then you laughed outright: “I may be old, but I was a flirt in my day and loved my flowers and powder — today I’ll be an old flirt!”'],
                  ch: ['第四十回', 'Chapter 40'] } }] },
    { tip: '跟老太太到沁芳亭上去，在她身边坐下。', tipEn: 'Follow the old lady onto Drenched Blossoms Pavilion and sit beside her.',
      label: '在老太太身边坐下', labelEn: 'Sit beside the old lady', where: '沁芳亭', whereEn: 'Drenched Blossoms Pavilion', face: () => { const [x, z] = qf(); return [x, z + 20]; },
      npcs: [{ who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => { const [x, z] = qf(); return [x - 1.2, z - 0.6]; } },
             { who: '惜春', whoEn: 'Xichun', color: '#9fa6c8', at: () => { const [x, z] = qf(); return [x + 1.5, z - 1.4]; } },
             { who: '凤姐', whoEn: 'Wang Xifeng', color: '#b6463c', at: () => { const [x, z] = qf(); return [x + 1.6, z + 1.4]; } },
             { who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => { const [x, z] = qf(); return [x - 1.9, z + 1.3]; } },
             { who: '李纨', whoEn: 'Li Wan', color: '#8e8a80', at: () => { const [x, z] = qf(); return [x + 0.2, z + 3.4]; } }],
      pages: [{ say: [['', '', '说笑之间，已来至沁芳亭子上。丫鬟们抱了一个大锦褥子来，铺在栏杆榻板上。老太太倚柱坐下，命你也坐在旁边，因问你：', 'Laughing and chatting, they came up onto Drenched Blossoms Pavilion. Maids brought a great brocade mat and spread it on the railing bench. The old lady sat down against a pillar, had you sit beside her, and asked:'],
                      ['贾母', 'The Lady Dowager', '这园子好不好？', 'Well — is this garden good or not?']], btn: ['……', '…'] },
              { ask: { q: ['你怎么回？', 'What do you say?'],
                  opts: [{ t: ['我们乡下人到了年下，都上城来买画儿贴。想着那个画儿也不过是假的，那里有这个真地方呢。谁知我今儿进这园里一瞧，竟比那画儿还强十倍。', 'At New Year we country folk come to town to buy pictures to paste up. I always thought those pictures were make-believe — how could there be such a place? But now I’ve come into this garden, it beats the pictures ten times over!'], best: 1 },
                         { t: ['好是好，就是太大了，走得我腿都酸了。', 'Good it is — only so big my old legs ache from walking.'] },
                         { t: ['好！这么大一片地，要是种上庄稼，够我们庄上吃几年的。', 'Good! A plot this size, sown with grain, would feed our whole village for years.'] }],
                  after: ['众人都笑了。你念了一声佛，又道：“我们乡下人到了年下，都上城来买画儿贴……谁知我今儿进这园里一瞧，竟比那画儿还强十倍。”', 'Everyone laughed. You called on the Buddha and went on: “At New Year we country folk come to town to buy pictures… but now I’ve come into this garden, it beats the pictures ten times over!”'],
                  ch: ['第四十回', 'Chapter 40'] } },
              { text: { title: '比画儿还强十倍', titleEn: 'Ten Times Better than the Pictures', ch: '第四十回', chEn: 'Chapter 40',
                p: ['你又说：“怎么得有人也照着这个园子画一张，我带了家去，给他们见见，死了也得好处。”',
                    '老太太听说，便指着惜春笑道：“你瞧我这个小孙女儿，她就会画。等明儿叫她画一张如何？”你听了，喜的忙跑过来，拉着惜春说道：“我的姑娘！你这么大年纪儿，又这么个好模样，还有这个能干，别是个神仙托生的罢。”',
                    '老太太少歇一回，自然领着你都见识见识。先到了潇湘馆。'],
                pEn: ['And you said: “If only someone would paint this garden just as it is, so I could take it home to show them — I’d die content.”',
                      'Hearing this, the old lady pointed at Xichun and laughed: “See this little granddaughter of mine? She can paint. Shall we have her paint one for you?” You were so delighted you ran over, took Xichun’s hands and said: “My dear young lady! So young, so lovely, and so clever besides — you must be a fairy come down to earth!”',
                      'After a short rest the old lady naturally took you to see everything. First they came to the Bamboo Lodge.'] } }] },
    { tip: '跟老太太去潇湘馆。', tipEn: 'Follow the old lady to the Bamboo Lodge.', label: '跟着进院', labelEn: 'Follow them in', place: 'xiaoxiang', face: () => [-40, 92],
      npcs: [{ who: '琥珀', whoEn: 'Hupo', color: '#c7a76a', at: () => [-50.5, 92.5] },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [-53.6, 90.2] },
             { who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => [-53.2, 88.6] },
             { who: '凤姐', whoEn: 'Wang Xifeng', color: '#b6463c', at: () => [-54.4, 92.4] }],
      pages: [{ say: [['', '', '一进门，只见两边翠竹夹路，土地下苍苔布满，中间羊肠一条石子漫的路。你让出路来给老太太众人走，自己却走土地。', 'Inside the gate, green bamboo lined both sides of the way; the bare earth was carpeted with moss, with a narrow pebbled path winding down the middle. You stepped aside to leave the path to the old lady and the others, and walked on the earth yourself.'],
                      ['琥珀', 'Hupo', '姥姥，你上来走，仔细苍苔滑了。', 'Granny, come up onto the path — mind the moss, it’s slippery!']], btn: ['……', '…'] },
              { ask: { q: ['你怎么回？', 'What do you say?'],
                  opts: [{ t: ['不相干的，我们走熟了的，姑娘们只管走罢。可惜你们的那绣鞋，别沾脏了。', 'Never mind me — we’re used to it. You young ladies go on; it’d be a shame to dirty those embroidered shoes of yours.'], best: 1 },
                         { t: ['好，好，我这就上来。', 'Yes, yes, I’m coming up.'] },
                         { t: ['（不答话，只顾抬头看那竹子）', '(Say nothing; just gaze up at the bamboo.)'] }],
                  bestAfter: ['你只顾上头和人说话，不防底下——', 'You were so busy talking to the people above that you didn’t watch your feet —'],
                  after: ['你嘴上应着，眼睛却只顾往上看，不防底下——', 'You answered, but your eyes were on everything above you, and you didn’t watch your feet —'],
                  ch: ['第四十回', 'Chapter 40'] } },
              { fx: 'slip' },
              { say: [['', '', '果踩滑了，咕咚一跤跌倒。众人拍手都哈哈的笑起来。', 'Sure enough your foot slid, and down you went with a thud. Everyone clapped and roared with laughter.'],
                      ['贾母', 'The Lady Dowager', '小蹄子们，还不搀起来，只站着笑。', 'You little minxes! Don’t just stand there laughing — help her up!'],
                      ['', '', '说话时，你已爬了起来，自己也笑了：“才说嘴就打了嘴。”', 'By then you had scrambled up yourself, laughing too: “Serves me right for boasting!”'],
                      ['贾母', 'The Lady Dowager', '可扭了腰了不曾？叫丫头们捶一捶。', 'Did you wrench your back? Let the maids pound it for you.'],
                      ['刘姥姥', 'Granny Liu', '那里说的我这么娇嫩了。那一天不跌两下子，都要捶起来，还了得呢。', 'I’m not as delicate as all that. Not a day goes by I don’t take a tumble or two — if I had to be pounded every time, where would I be?']], btn: ['进屋去', 'Go inside'] }] },
    { tip: '进屋去。紫鹃早打起湘帘，老太太已在屋里坐下了。', tipEn: 'Go inside. Zijuan has raised the bamboo blind; the old lady is already seated.', label: '在屋里看看', labelEn: 'Look around the room', place: 'xiaoxiang',
      face: () => [-70, 86],
      npcs: [{ who: '林黛玉', whoEn: 'Lin Daiyu', color: '#b7c8b6', at: () => [-68.2, 89.6], floor: () => roomY('xiaoxiang_in') },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [-70.75, 89.95], floor: () => roomY('xiaoxiang_in'), sit: 0.5, seat: 'none', look: [-62, 90.4] },
             { who: '紫鹃', whoEn: 'Zijuan', color: '#9d8fb0', at: () => [-66.6, 91.7], floor: () => roomY('xiaoxiang_in') }],
      pages: [{ say: [['', '', '林黛玉亲自用小茶盘捧了一盏茶来奉与老太太。你因见窗下案上设着笔砚，又见书架上磊着满满的书——', 'Lin Daiyu herself brought the old lady a cup of tea on a little tray. You noticed brushes and inkstones laid out on the desk by the window, and bookshelves crammed full of books —']], btn: ['……', '…'] },
              { ask: { q: ['你心想，这是谁的屋子？', 'Whose room do you suppose this is?'],
                  opts: [{ t: ['这必定是那位哥儿的书房了。', 'This must be one of the young masters’ studies.'], best: 1 },
                         { t: ['这是老太太念经的地方吧？', 'Is this where the old lady says her prayers?'] },
                         { t: ['这么多书，是哪位先生教书的屋子？', 'So many books — is this some tutor’s schoolroom?'] }],
                  bestAfter: ['老太太笑指黛玉道：“这是我这外孙女儿的屋子。”', 'The old lady laughed and pointed at Daiyu: “This is my granddaughter’s room.”'],
                  after: ['众人都笑了。老太太笑指黛玉道：“这是我这外孙女儿的屋子。”', 'Everyone laughed. The old lady pointed at Daiyu: “This is my granddaughter’s room.”'],
                  ch: ['第四十回', 'Chapter 40'] } },
              { say: [['', '', '你留神打量了黛玉一番，方笑道：', 'You looked Daiyu carefully up and down, then laughed:'],
                      ['刘姥姥', 'Granny Liu', '这那像个小姐的绣房，竟比那上等的书房还好。', 'This is nothing like a young lady’s boudoir — it’s finer than the best of studies!']], btn: ['……', '…'] },
              { text: { title: '软烟罗', titleEn: 'Soft Mist Gauze', ch: '第四十回', chEn: 'Chapter 40',
                p: ['老太太见窗上的纱颜色旧了，说：“这个纱新糊上好看，过了后来就不翠了。这个院子里头又没有个桃杏树，这竹子已是绿的，再拿这绿纱糊上反不配。”',
                    '她说库里原有一种软烟罗，只有四样颜色：一样雨过天晴，一样秋香色，一样松绿的，一样就是银红的。做了帐子，糊了窗屉，远远的看着，就似烟雾一样，所以叫作软烟罗；那银红的又叫作霞影纱。“明儿就找出几匹来，拿银红的替她糊窗子。”',
                    '一径离了潇湘馆，远远望见池中一群人在那里撑船。老太太便说：早饭就摆到三姑娘那里去，我们从这里坐了船去。'],
                pEn: ['Seeing the window gauze had faded, the old lady said: “This gauze looks fine when it’s new, but it soon loses its green. There are no peach or apricot trees in this courtyard, and the bamboo is green already — green gauze on top of it doesn’t suit.”',
                      'There was a fabric in the storeroom, she said, called Soft Mist Gauze, in just four colours: rain-washed sky blue, autumn incense, pine green and silvery red. Made into bed curtains or pasted on window frames it looks from afar like mist — hence the name; the silvery red is also called Rosy Cloud Gauze. “Tomorrow find a few bolts and paste her windows with the silvery red.”',
                      'Leaving the Bamboo Lodge, they saw people poling boats on the pool. The old lady said: lay breakfast at Third Miss’s, and we’ll go over by boat.'] } }] },
    /* ---------------- 第四十回：秋爽斋早饭 ---------------- */
    { tip: '往秋爽斋去。早饭摆在晓翠堂，鸳鸯在院里等你。', tipEn: 'Go to the Autumn Freshness Studio. Breakfast is laid in the Hall of Morning Green; Yuanyang is waiting in the court.',
      label: '和鸳鸯说话', labelEn: 'Talk to Yuanyang', place: 'qiushuang', face: () => [-86, 34],
      npcs: [{ who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => [-83.4, 25.6] },
             { prop: 'table', at: () => [-86, 11.2], look: [-85, 11.2] },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [-86, 9.9], sit: 0.5, look: [-86, 11.2] },
             { who: '凤姐', whoEn: 'Wang Xifeng', color: '#b6463c', at: () => [-88.2, 12.9], look: [-86, 11.2] },
             { who: '史湘云', whoEn: 'Shi Xiangyun', color: '#c98a4e', at: () => [-84.6, 9.9], sit: 0.5, look: [-84.6, 11.2] },
             { who: '林黛玉', whoEn: 'Lin Daiyu', color: '#b7c8b6', at: () => [-87.4, 9.9], sit: 0.5, look: [-87.4, 11.2] },
             { who: '贾宝玉', whoEn: 'Jia Baoyu', color: '#a8342b', at: () => [-84.0, 11.2], male: 1, sit: 0.5, look: [-86, 11.2] }],
      pages: [{ say: [['', '', '早饭摆在秋爽斋晓翠堂上。鸳鸯拉你出来，悄悄的嘱咐了一席话，又说：', 'Breakfast was laid in the Hall of Morning Green. Yuanyang drew you aside, whispered a long string of instructions, and added:'],
                      ['鸳鸯', 'Yuanyang', '这是我们家的规矩，若错了我们就笑话呢。', 'That’s the custom in our house — if you get it wrong, we’ll laugh at you.'],
                      ['', '', '调停已毕，你入了座，拿起箸来，沉甸甸的不伏手——原是凤姐和鸳鸯商议定了，单拿一双老年四楞象牙镶金的筷子与你。', 'All arranged, you took your seat and picked up your chopsticks — heavy, and they wouldn’t sit right in your hand. Xifeng and Yuanyang had plotted to give you alone an old pair of square ivory chopsticks inlaid with gold.'],
                      ['刘姥姥', 'Granny Liu', '这叉爬子比俺那里铁锨还沉，那里犟的过他。', 'These prongs are heavier than a spade back home — how am I to manage them?']], btn: ['……', '…'] },
              { ask: { q: ['老太太说声“请”，你想起鸳鸯嘱咐的话，便站起身来——', 'The old lady said “Please, begin.” Remembering Yuanyang’s instructions, you stood up —'],
                  opts: [{ t: ['（高声说）老刘，老刘，食量大似牛，吃一个老母猪不抬头。', '(Loudly) Old Liu, Old Liu, eats like an ox — gobbles a whole sow without lifting her head!'], best: 1 },
                         { t: ['多谢老太太赏饭！', 'Thank you, old lady, for the meal!'] },
                         { t: ['（不说话，坐下低头先吃）', '(Say nothing; sit down and start eating.)'] }],
                  bestAfter: ['说完，却鼓着腮不语。众人先是发怔，后来一听，上上下下都哈哈的大笑起来。', 'Then you sat with cheeks puffed out, saying nothing. Everyone stared — then it sank in, and the whole room roared with laughter.'],
                  after: ['鸳鸯在旁边直使眼色。你想起来了，忙又站起身，高声说道：“老刘，老刘，食量大似牛，吃一个老母猪不抬头。”众人先是发怔，后来一听，上上下下都哈哈的大笑起来。', 'Yuanyang kept winking at you. You remembered, stood up and boomed: “Old Liu, Old Liu, eats like an ox — gobbles a whole sow without lifting her head!” Everyone stared — then the whole room roared with laughter.'],
                  ch: ['第四十回', 'Chapter 40'] } },
              { say: [['', '', '史湘云撑不住，一口饭都喷了出来；林黛玉笑岔了气，伏着桌子嗳哟；宝玉早滚到老太太怀里，老太太笑的搂着宝玉叫“心肝”。', 'Shi Xiangyun couldn’t hold it and sprayed out a mouthful of rice; Lin Daiyu laughed herself breathless and collapsed over the table groaning; Baoyu rolled into the old lady’s lap, and she hugged him, calling him “my heart”.']], btn: ['……', '…'] },
              { ask: { q: ['凤姐偏拣了一碗鸽子蛋放在你桌上。你拿起那双象牙筷子——', 'Xifeng set a bowl of pigeon eggs right in front of you. You lifted those ivory chopsticks —'],
                  opts: [{ t: ['这里的鸡儿也俊，下的这蛋也小巧，怪俊的。我且攮一个。', 'Even the hens here are dainty — look how small and pretty their eggs are! Let me spear one.'], best: 1 },
                         { t: ['这么小的鸡蛋，是怎么下的？', 'Such tiny hen’s eggs — how do they lay them?'] },
                         { t: ['（不说话，伸筷子就夹）', '(Say nothing; just go for one.)'] }],
                  bestAfter: ['满碗里闹了一阵，好容易撮起一个来，才伸着脖子要吃，偏又滑下来滚在地下。', 'You chased them round the bowl, at last pinched one up, craned your neck to eat it — and it slipped and rolled onto the floor.'],
                  after: ['众人笑个不住。你满碗里闹了一阵，好容易撮起一个来，才伸着脖子要吃，偏又滑下来滚在地下。', 'Everyone kept laughing. You chased them round the bowl, at last pinched one up, craned your neck — and it slipped and rolled onto the floor.'],
                  ch: ['第四十回', 'Chapter 40'] } },
              { text: { title: '老刘老刘，食量大似牛', titleEn: 'Old Liu, Old Liu, Eats Like an Ox', ch: '第四十回', chEn: 'Chapter 40',
                p: ['你叹道：“一两银子，也没听见响声儿就没了。”原来这鸽子蛋一两银子一个。',
                    '老太太便叫换了一双乌木三镶银的筷子来。你说：“去了金的，又是银的，到底不及俺们那个伏手。”凤姐儿道：“菜里若有毒，这银子下去了就试的出来。”你道：“这个菜里若有毒，俺们那菜都成了砒霜了。那怕毒死了也要吃尽了。”',
                    '饭后，忽一阵风过，隐隐听得鼓乐之声。老太太说，就叫梨香院的女孩子们在藕香榭的水亭子上演习，借着水音更好听。众人往荇叶渚上船去。'],
                pEn: ['You sighed: “A whole tael of silver, gone without so much as a sound.” Each pigeon egg cost a tael.',
                      'The old lady had your chopsticks changed for ebony ones mounted with silver. You said: “Gold gone, silver come — still not as handy as ours at home.” Xifeng said: “If there’s poison in a dish, the silver will show it.” You said: “If these dishes are poison, then ours at home are pure arsenic! I’d eat them all even if they killed me.”',
                      'After the meal a breeze brought the faint sound of drums and pipes. The old lady said to have the girls from Pear Fragrance Court practise on the water pavilion of the Lotus Fragrance Pavilion — the music sounds better over water. Everyone set off for the Water-Fringe Landing to take the boats.'] } }] },
    /* ---------------- 第四十回：荇叶渚上船，花溆萝港，到蘅芜苑 ---------------- */
    { tip: '到荇叶渚码头上船。驾娘已把两只棠木舫撑来了。', tipEn: 'Go to the Water-Fringe Landing and board the boat. The boatwomen have brought the two crab-apple-wood boats over.',
      label: '上船', labelEn: 'Board the boat', place: 'xingye', face: () => [-104, 21],
      npcs: [{ who: '驾娘', whoEn: 'Boatwoman', color: '#6f7d68', at: () => [-115.6, 23.4] },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [-112.4, 19.6] },
             { who: '贾宝玉', whoEn: 'Jia Baoyu', color: '#a8342b', at: () => [-110.8, 22.8], male: 1 },
             { who: '林黛玉', whoEn: 'Lin Daiyu', color: '#b7c8b6', at: () => [-111.2, 18.2] }],
      pages: [{ say: [['', '', '到了荇叶渚，那姑苏选来的几个驾娘早把两只棠木舫撑来。众人扶了老太太上去，你也跟着上了船。', 'At the Water-Fringe Landing the boatwomen chosen from Suzhou had already poled the two crab-apple-wood boats over. They helped the old lady aboard, and you climbed in after.'],
                      ['贾宝玉', 'Jia Baoyu', '这些破荷叶可恨，怎么还不叫人来拔去。', 'These ragged lotus leaves are hateful — why hasn’t anyone pulled them out?'],
                      ['林黛玉', 'Lin Daiyu', '我最不喜欢李义山的诗，只喜他这一句“留得残荷听雨声”。偏你们又不留着残荷了。', 'I don’t care for Li Shangyin’s poems at all, except this one line: “Keep the withered lotus to hear the rain.” And now you won’t even keep the withered lotus.'],
                      ['贾宝玉', 'Jia Baoyu', '果然好句，以后咱们就别叫人拔去了。', 'A fine line indeed. From now on we won’t have them pulled.']], btn: ['开船', 'Cast off'] },
              { fade: { msg: ['船过花溆的萝港之下，觉得阴森透骨，两滩上衰草残菱，更助秋情。', 'The boat passed under the Lily Harbour by the flowering shoals — a chill to the bone; withered grass and broken water-chestnuts on either bank deepened the autumn mood.'], to: 'hengwu', hold: 3200 } }] },
    { tip: '上岸了。进蘅芜苑，到宝钗屋里看看。', tipEn: 'You’re ashore. Go into Alpinia Park and look round Baochai’s room.',
      label: '进宝钗屋里', labelEn: 'Enter Baochai’s room', place: 'hengwu', ch: ['第四十回', 'Chapter 40'], face: () => [-70, -128],
      npcs: [{ who: '薛宝钗', whoEn: 'Xue Baochai', color: '#e5d9b6', at: () => [-67, -148.2], floor: () => roomY('hengwu_in') },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [-72.2, -147.6], floor: () => roomY('hengwu_in') }],
      pages: [{ say: [['', '', '进了蘅芜苑，只觉异香扑鼻。那些奇草仙藤愈冷愈苍翠，都结了实，似珊瑚豆子一般，累垂可爱。', 'Entering Alpinia Park, a strange fragrance met you. The rare grasses and fairy vines grew greener as the cold came on, all hung with fruit like coral beads, lovely in their clusters.'],
                      ['', '', '及进了房屋，雪洞一般，一色玩器全无，案上只有一个土定瓶中供着数枝菊花，并两部书，茶奁茶杯而已。床上只吊着青纱帐幔，衾褥也十分朴素。', 'Inside, the room was like a snow cave — not a single ornament; on the desk only a plain earthenware vase with a few sprays of chrysanthemum, two volumes of books, a tea caddy and cups. The bed had only blue gauze curtains, and the covers were very plain.'],
                      ['贾母', 'The Lady Dowager', '这孩子太老实了。你没有陈设，何妨和你姨娘要些。', 'This child is too modest. If you have no ornaments, why not ask your aunt for some?'],
                      ['贾母', 'The Lady Dowager', '使不得。虽然她省事，倘或来一个亲戚，看着不像；二则年轻的姑娘们，房里这样素净，也忌讳。我们这老婆子，越发该住马圈去了。', 'This won’t do. Thrifty as she is, if a relative came it wouldn’t look right; and besides, it’s unlucky for a young girl’s room to be so bare. By that measure we old women ought to be living in the stables!']], btn: ['……', '…'] },
              { text: { title: '蘅芜苑 · 雪洞一般', titleEn: 'Alpinia Park · Like a Snow Cave', ch: '第四十回', chEn: 'Chapter 40',
                p: ['老太太便命鸳鸯去取那石头盆景儿和那架纱桌屏，还有个墨烟冻石鼎，摆在这案上就够了；再把那水墨字画白绫帐子拿来，把这帐子也换了。',
                    '说着，坐了一回方出来，一径来至缀锦阁下。'],
                pEn: ['The old lady sent Yuanyang to fetch the stone miniature landscape, the gauze table screen and the smoky-ink soapstone tripod — those on the desk would be enough; and the white silk curtains painted in ink were to replace the bed curtains.',
                      'After sitting a while they came out and went straight to the foot of the Brocade Pavilion.'] } }] },
    /* ---------------- 第四十回：缀锦阁下，鸳鸯行牙牌令 ---------------- */
    { tip: '到大观楼东边的缀锦阁下入席。鸳鸯做令官，要行牙牌令了。', tipEn: 'Go to the foot of the Brocade Pavilion, east of the Grand View Tower, and take your seat. Yuanyang is master of the drinking game.',
      label: '入席', labelEn: 'Take your seat', where: '缀锦阁', whereEn: 'Brocade Pavilion', place: 'daguan', ch: ['第四十回', 'Chapter 40'], face: () => [24, -70],
      npcs: [{ who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => [26.4, -45.2] },
             { prop: 'table', at: () => [24, -47.6], look: [25, -47.6] },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [24, -48.5], sit: 0.5, look: [24, -47.6] },
             { who: '薛姨妈', whoEn: 'Aunt Xue', color: '#7d6a8a', at: () => [22.4, -47.6], sit: 0.5, look: [24, -47.6] },
             { who: '史湘云', whoEn: 'Shi Xiangyun', color: '#c98a4e', at: () => [25.7, -47.6], sit: 0.5, look: [24, -47.6] },
             { who: '薛宝钗', whoEn: 'Xue Baochai', color: '#e5d9b6', at: () => [23.1, -46.7], sit: 0.5, look: [23.1, -47.6] },
             { who: '林黛玉', whoEn: 'Lin Daiyu', color: '#b7c8b6', at: () => [24.9, -46.7], sit: 0.5, look: [24.9, -47.6] }],
      pages: [{ say: [['', '', '藕香榭那边，梨香院的女孩子们奏起乐来，乐声穿林度水而来，自然使人神怡心旷。众人在缀锦阁下吃酒，鸳鸯做了令官，行牙牌令：她说一句，各人照着牌对一句，要押韵。', 'Over at the Lotus Fragrance Pavilion the girls struck up their music, which came threading through the trees and across the water, lifting everyone’s spirits. They drank at the foot of the Brocade Pavilion with Yuanyang as master of the game: she calls out a domino, and each person answers with a rhyming line.'],
                      ['鸳鸯', 'Yuanyang', '轮到刘姥姥了。', 'Granny Liu’s turn now.'],
                      ['刘姥姥', 'Granny Liu', '我们庄家人闲了，也常会几个人弄这个，但不如说的这么好听。少不得我也试一试。', 'We country folk play this too when we’re idle, only we don’t say it so prettily. Well, I suppose I must try.']], btn: ['来吧', 'Go on'] },
              { ask: { q: ['鸳鸯道：“左边‘四四’是个人。”', 'Yuanyang: “On the left, double four — that’s a person.”'],
                  opts: [{ t: ['是个庄家人罢。', 'A farmer, I’d say.'], best: 1 }, { t: ['是个老婆子罢。', 'An old woman, I’d say.'] }, { t: ['是个大胖子罢。', 'A big fat fellow, I’d say.'] }],
                  bestAfter: ['众人哄堂笑了。老太太笑道：“说的好，就是这样说。”你也笑道：“我们庄家人，不过是现成的本色，众位别笑。”', 'Everyone burst out laughing. The old lady said: “Well said — that’s just the way.” You laughed too: “We farmers just say what’s in front of us — don’t laugh, all of you.”'],
                  after: ['众人都笑。你想了想，又道：“是个庄家人罢。”老太太笑道：“说的好，就是这样说。”', 'Everyone laughed. You thought again and said: “A farmer, I’d say.” The old lady laughed: “Well said — that’s just the way.”'],
                  ch: ['第四十回 · 牙牌令', 'Chapter 40 · Dominoes'] } },
              { ask: { q: ['鸳鸯道：“中间‘三四’绿配红。”', 'Yuanyang: “In the middle, three-four — green set off with red.”'],
                  opts: [{ t: ['大火烧了毛毛虫。', 'A big fire burned the caterpillar up.'], best: 1 }, { t: ['红萝卜配青葱。', 'Red radishes go with green onions.'] }, { t: ['绿叶子配红花儿。', 'Green leaves go with red flowers.'] }],
                  bestAfter: ['众人笑道：“这是有的，还说你的本色。”', 'Everyone laughed: “That’s real enough — your own true colours again.”'],
                  after: ['众人笑道：“这也使得。”你想了想，又道：“大火烧了毛毛虫。”众人越发笑了。', 'Everyone laughed: “That’ll do.” You thought again: “A big fire burned the caterpillar up.” They laughed all the more.'],
                  ch: ['第四十回 · 牙牌令', 'Chapter 40 · Dominoes'] } },
              { ask: { q: ['鸳鸯道：“右边‘幺四’真好看。”', 'Yuanyang: “On the right, one-four — lovely indeed.”'],
                  opts: [{ t: ['一个萝卜一头蒜。', 'One radish and a head of garlic.'], best: 1 }, { t: ['一朵花儿一根线。', 'One flower and one thread.'] }, { t: ['一碗米饭一碗汤。', 'A bowl of rice, a bowl of soup.'] }],
                  bestAfter: ['众人又笑了。', 'Everyone laughed again.'],
                  after: ['你自己摇摇头，又道：“一个萝卜一头蒜。”众人又笑了。', 'You shook your head and tried again: “One radish and a head of garlic.” Everyone laughed again.'],
                  ch: ['第四十回 · 牙牌令', 'Chapter 40 · Dominoes'] } },
              { ask: { q: ['鸳鸯笑道：“凑成便是一枝花。”', 'Yuanyang laughed: “All together they make a spray of flowers.”'],
                  opts: [{ t: ['（两只手比着）花儿落了结个大倭瓜。', '(Gesturing with both hands) When the flowers fall, out comes a great big squash!'], best: 1 }, { t: ['花儿插在我头上。', 'And the flowers are stuck on my head!'] }, { t: ['一枝花儿香又香。', 'A spray of flowers, sweet and sweet.'] }],
                  bestAfter: ['众人大笑起来。', 'Everyone roared with laughter.'],
                  after: ['众人笑起来。你两只手比着，又说道：“花儿落了结个大倭瓜。”众人大笑起来。', 'Everyone laughed. You gestured with both hands and went on: “When the flowers fall, out comes a great big squash!” Everyone roared.'],
                  ch: ['第四十回 · 牙牌令', 'Chapter 40 · Dominoes'] } }] },
    /* ---------------- 第四十一回：茄鲞 ---------------- */
    { tip: '凤姐叫你过去，要夹菜给你尝。', tipEn: 'Xifeng is calling you over to try a dish.', label: '尝凤姐夹的菜', labelEn: 'Taste Xifeng’s dish', where: '缀锦阁', whereEn: 'Brocade Pavilion', place: 'daguan',
      ch: ['第四十一回', 'Chapter 41'], face: () => [24, -70],
      npcs: [{ who: '凤姐', whoEn: 'Wang Xifeng', color: '#b6463c', at: () => [22.2, -45.4], look: [24, -47.6] },
             { prop: 'table', at: () => [24, -47.6], look: [25, -47.6] },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', at: () => [24, -48.5], sit: 0.5, look: [24, -47.6] },
             { who: '鸳鸯', whoEn: 'Yuanyang', color: '#a7c0b8', at: () => [26.4, -45.2], look: [24, -47.6] }],
      pages: [{ say: [['贾母', 'The Lady Dowager', '你把茄鲞搛些喂她。', 'Pick out some of the aubergine relish and feed her.'],
                      ['', '', '凤姐儿听说，依言搛些茄鲞送入你口中，笑道：“你们天天吃茄子，也尝尝我们的茄子弄的可口不可口。”', 'Xifeng did as she was told and popped some aubergine relish into your mouth, laughing: “You eat aubergine every day — try ours and see if it’s any good.”'],
                      ['刘姥姥', 'Granny Liu', '别哄我了，茄子跑出这味儿来了，我们也不用种粮食，只种茄子了。', 'Don’t tease me! If aubergine could taste like this, we’d stop growing grain and plant nothing but aubergines.'],
                      ['凤姐', 'Wang Xifeng', '这也不难。你把才下来的茄子把皮签了，只要净肉，切成碎钉子，用鸡油炸了，再用鸡脯子肉并香菌、新笋、蘑菇、五香腐干、各色干果子，俱切成钉子，用鸡汤煨干，将香油一收，外加糟油一拌，盛在瓷罐子里封严，要吃时拿出来，用炒的鸡瓜一拌就是。', 'Nothing to it. Take fresh aubergines, peel them, keep only the flesh and dice it; fry in chicken fat; then dice chicken breast, mushrooms, fresh bamboo shoots, button mushrooms, spiced dried tofu and all kinds of dried fruit and nuts, simmer them all dry in chicken stock, finish with sesame oil and a dash of wine-lees oil, seal it in a porcelain jar, and when you want some, toss it with fried diced chicken.']], btn: ['……', '…'] },
              { ask: { q: ['你听完，怎么说？', 'Having heard all that, what do you say?'],
                  opts: [{ t: ['我的佛祖！倒得十来只鸡来配他，怪道这个味儿！', 'Merciful Buddha! It takes a dozen chickens to go with it — no wonder it tastes like that!'], best: 1 }, { t: ['俺们庄上的茄子，可就白长了。', 'Then the aubergines on our farm grow for nothing.'] }, { t: ['（摇头吐舌，半日说不出话来）', '(Shake your head and stick out your tongue, speechless for a long while.)'] }],
                  bestAfter: ['你一面说，一面慢慢的吃完了酒，还只管细玩那杯。', 'Saying so, you slowly finished your wine, and kept turning the cup over to admire it.'],
                  after: ['半日，你摇头吐舌说道：“我的佛祖！倒得十来只鸡来配他，怪道这个味儿！”众人都笑了。', 'After a long while you shook your head, stuck out your tongue and said: “Merciful Buddha! It takes a dozen chickens to go with it — no wonder it tastes like that!” Everyone laughed.'],
                  ch: ['第四十一回', 'Chapter 41'] } },
              { text: { title: '茄鲞', titleEn: 'Aubergine Relish', ch: '第四十一回', chEn: 'Chapter 41',
                p: ['吃过酒，老太太带了众人往栊翠庵来。妙玉忙接了进去。'],
                pEn: ['After the wine the old lady led everyone to the Green Lattice Nunnery. Miaoyu hurried out to welcome them in.'] } }] },
    /* ---------------- 第四十一回：栊翠庵品茶 ---------------- */
    { tip: '跟老太太去栊翠庵。妙玉在庵里奉茶。', tipEn: 'Follow the old lady to the Green Lattice Nunnery. Miaoyu is serving tea.', label: '吃茶', labelEn: 'Have tea', place: 'longcui',
      ch: ['第四十一回', 'Chapter 41'],
      npcs: [{ who: '妙玉', whoEn: 'Miaoyu', color: '#d8d2c4', anchor: 'longcui' },
             { who: '贾母', whoEn: 'The Lady Dowager', color: '#6d5a48', anchor: 'longcui', off: 2.2, sit: 0.5 }],
      pages: [{ say: [['贾母', 'The Lady Dowager', '我们才都吃了酒肉，你这里头有菩萨，冲了罪过。我们这里坐坐，把你的好茶拿来，我们吃一杯就去了。', 'We’ve all just had wine and meat, and you have the Buddha here — we mustn’t offend. We’ll sit out here; bring your good tea, we’ll have a cup and go.'],
                      ['', '', '妙玉亲自捧了一个海棠花式雕漆填金云龙献寿的小茶盘，里面放一个成窑五彩小盖钟，捧与老太太。', 'Miaoyu herself brought a small carved-lacquer tray shaped like a crab-apple blossom, gilded with clouds and dragons, holding a little covered cup of Chenghua five-colour porcelain, and offered it to the old lady.'],
                      ['贾母', 'The Lady Dowager', '我不吃六安茶。', 'I don’t drink Lu’an tea.'],
                      ['妙玉', 'Miaoyu', '知道。这是老君眉。', 'I know. This is Old Master’s Eyebrow.'],
                      ['贾母', 'The Lady Dowager', '是什么水？', 'And the water?'],
                      ['妙玉', 'Miaoyu', '是旧年蠲的雨水。', 'Rainwater, saved from last year.'],
                      ['', '', '老太太吃了半盏，便笑着递与你说：“你尝尝这个茶。”你便一口吃尽——', 'The old lady drank half the cup and passed it to you with a smile: “Try this tea.” You drank it down in one gulp —']], btn: ['……', '…'] },
              { ask: { q: ['你怎么说？', 'What do you say?'],
                  opts: [{ t: ['好是好，就是淡些，再熬浓些更好了。', 'Good it is, only a bit weak — brew it stronger and it’d be better still.'], best: 1 }, { t: ['这是什么好茶？比俺们庄上的大碗茶香多了。', 'What fine tea! Much more fragrant than the big-bowl tea back home.'] }, { t: ['这么小一个盅子，还不够润嗓子的。', 'Such a tiny cup — not enough to wet my throat.'] }],
                  bestAfter: ['老太太众人都笑起来。', 'The old lady and everyone burst out laughing.'],
                  after: ['众人都笑。你咂咂嘴，又道：“好是好，就是淡些，再熬浓些更好了。”老太太众人越发笑起来。', 'Everyone laughed. You smacked your lips and added: “Good it is, only a bit weak — brew it stronger and it’d be better still.” The old lady and everyone laughed all the more.'],
                  ch: ['第四十一回', 'Chapter 41'] } },
              { text: { title: '栊翠庵茶品梅花雪', titleEn: 'Tea at Green Lattice Nunnery', ch: '第四十一回', chEn: 'Chapter 41',
                p: ['那成窑的茶杯，妙玉嫌你吃过，叫人不要收了，搁在外头去。宝玉悄悄讨了来，说给你拿去卖了，也可以度日。',
                    '出了栊翠庵，你吃多了酒和油腻，又喝了些茶，肚子里一阵乱响，忙要出恭。一个婆子领你去了，回来却找不着路——'],
                pEn: ['Because you had drunk from it, Miaoyu would not have the Chenghua cup taken back; she had it left outside. Baoyu quietly begged it from her, saying you could sell it and live on the money.',
                      'Leaving the nunnery, between the wine, the rich food and the tea, your stomach began to rumble and you hurried off to the privy. An old woman showed you the way — but on the way back you couldn’t find it —'] } }] },
    /* ---------------- 第四十一回：醉卧怡红院 ---------------- */
    { tip: '你迷了路，酒也上了头。跟着光柱走，看看是哪里。', tipEn: 'You’ve lost your way, and the wine has gone to your head. Follow the beam of light and see where you end up.',
      label: '进屋看看', labelEn: 'Go in and look', place: 'yihong', ch: ['第四十一回', 'Chapter 41'],
      npcs: [{ ghost: 1, at: () => [104, 137], floor: () => roomY('yihong_in') }],
      pages: [{ say: [['', '', '你东绕西绕，穿过一带竹篱，进了一个院子，又进了房门。只见迎面一个女孩儿，满面含笑迎了出来。你忙笑道：“姑娘们把我丢下了，叫我碰头碰到这里来。”说了，只见那女孩儿不答。你便赶来拉她的手，“咕咚”一声，便撞到板壁上——原来是一幅画儿。', 'You wandered this way and that, through a bamboo fence, into a courtyard and in at a door. A girl came smiling to meet you. “The young ladies left me behind,” you said, laughing, “and I’ve bumped my way here.” She didn’t answer. You went to take her hand — and thudded into the wall. It was a painting.'],
                      ['', '', '你又转了几转，见一个老婆子也从外面迎了进来，头上满满的插着花。你只当是亲家母，诧异道——', 'You turned and turned again, and saw an old woman coming in to meet you, her head stuck full of flowers. You took her for your kinswoman and said in surprise —']], btn: ['……', '…'] },
              { ask: { q: ['你对那“亲家母”说——', 'You say to your “kinswoman” —'],
                  opts: [{ t: ['你好没见世面，见这园里的花好，你就没死活戴了一头。', 'You’ve never seen anything, have you? You see the pretty flowers in this garden and stick a whole headful on, never mind if you live or die!'], best: 1 }, { t: ['亲家母，你也来逛园子了？', 'Kinswoman! You’ve come to see the garden too?'] }, { t: ['（伸手去拉她）', '(Reach out to take her hand.)'] }],
                  bestAfter: ['那老婆子只是笑，也不答言。你伸手一摸，再细一看，原来是一面嵌在板壁上的大穿衣镜，里头那个戴了一头花的，正是你自己。', 'The old woman only laughed and said nothing. You reached out, felt, looked closer — it was a great dressing mirror set into the wall, and the woman with the headful of flowers was you.'],
                  after: ['那老婆子也伸手来拉你，你一摸，冰凉的——原来是一面嵌在板壁上的大穿衣镜，里头那个戴了一头花的，正是你自己。', 'The old woman reached out too; you touched — ice-cold. It was a great dressing mirror set into the wall, and the woman with the headful of flowers was you.'],
                  ch: ['第四十一回', 'Chapter 41'] } },
              { fade: { msg: ['你东一摸西一摸，转进了一间屋子，只见一副最精致的床帐。此时又带了七八分醉，又走乏了，便一屁股坐在床上，身不由己，前仰后合的，朦胧着两眼，一歪身就睡熟在床上……鼾齁如雷。', 'Groping about, you found yourself in a room with the most exquisite bed and curtains. Seven or eight parts drunk and worn out with walking, you plumped down on the bed, swayed back and forth with eyes half shut, toppled over, and fell fast asleep… snoring like thunder.'], hold: 3600 } },
              { say: [['', '', '袭人找来，进了房门，只闻得酒屁臭气，满屋一瞧，只见你扎手舞脚的仰卧在床上。袭人这一惊不小，忙上来将你没死活的推醒。', 'Xiren came looking, stepped in, and was met by a reek of wine; there you were, sprawled on your back across the bed, arms and legs flung out. Thoroughly alarmed, she shook you awake for all she was worth.'],
                      ['袭人', 'Xiren', '不相干，有我呢。你随我出来。', 'Never mind — I’m here. Come out with me.'],
                      ['袭人', 'Xiren', '你就说醉倒在山子石上打了个盹儿。', 'Just say you got drunk and dozed off on the rockery.']], btn: ['跟她出去', 'Follow her out'] },
              { fade: { msg: ['当晚你又在老太太那里歇了一夜。次日清早，该回去了。', 'You spent one more night at the old lady’s. Early next morning, it was time to go home.'], to: 'gate', at: [0, 104, 0], hour: 7.4, hold: 2600 } }] },
    /* ---------------- 第四十二回：平儿打点东西，回乡 ---------------- */
    { tip: '第二天一早，你要回去了。到正门去找平儿，她替你打点好了东西。', tipEn: 'Next morning you’re going home. Go to the Main Gate and find Pinger — she has packed everything for you.',
      label: '和平儿说话', labelEn: 'Talk to Pinger', place: 'gate', ch: ['第四十二回', 'Chapter 42'], face: () => [0, 90],
      npcs: [{ who: '平儿', whoEn: 'Pinger', color: '#c9a3b6', at: () => [-5, 111.5] }],
      pages: [{ say: [['平儿', 'Pinger', '这是昨日你要的青纱一匹，奶奶另外送你一个实地子月白纱作里子。这是两个茧绸，作袄儿裙子都好。这包袱里是两匹绸子，年下做件衣裳穿。这是一盒子各样内造小饽饽儿，也有你吃过的，也有你没吃过的，拿去摆碟子请人，比买的强些。', 'Here’s the bolt of blue gauze you asked for yesterday, and my mistress adds a moon-white gauze for lining. These two are pongee — good for a jacket or a skirt. In this bundle, two bolts of silk to make clothes for New Year. Here’s a box of all sorts of palace pastries — some you’ve tasted, some you haven’t — set them out for guests, better than anything you could buy.'],
                      ['平儿', 'Pinger', '这两条口袋是你昨日装瓜果子来的，如今这一个里头装了两斗御田粳米，熬粥是难得的；这一条里头是园子里果子和各样干果子。这两包每包里头五十两，共是一百两，是太太给的，叫你拿去或者作个小本买卖，或者置几亩地，以后再别求亲靠友的。', 'These two sacks you brought your melons and fruit in yesterday: one now holds two pecks of rice from the imperial fields — rare for porridge; the other, fruit from the garden and all kinds of dried fruit. And these two packets of fifty taels each, a hundred in all, are from Her Ladyship — use them to set up a little trade or buy a few acres, so you need never depend on friends and relatives again.'],
                      ['', '', '你只管念佛，听平儿如此说，越发感激不尽。', 'You kept calling on the Buddha, and hearing all this, your gratitude knew no bounds.']], btn: ['……', '…'] },
              { text: { title: '刘姥姥回乡', titleEn: 'Granny Liu Goes Home', ch: '第四十二回', chEn: 'Chapter 42',
                p: ['你带着板儿，坐上车出了角门，回乡去了。',
                    '那园子，老太太已叫四姑娘惜春照样画一张。你回去说给庄上的人听：画儿上那样的地方，原来是真有的。'],
                pEn: ['You climbed into the cart with Ban’er, went out by the side gate, and headed home to the country.',
                      'As for the garden — the old lady has had Fourth Miss, Xichun, set about painting it just as it is. Back home you tell the village: the places in the pictures are real after all.'] } }] }
  ],
  tail: ['刘姥姥进大观园 · 完。可以在园子里随便走走，或点「入园」从头再来。', 'Granny Liu Visits the Garden · The End. Wander the garden as you like, or press “Play” to start again.']
};
/* 室内地面：取室内模型的位置（懒加载前用院落地面） */
function roomY(id) { const b = D.BLD.find(x => x.id === id); return b ? b.root.position.y + 0.48 : null; }
const qf = () => { const Q = D.QINFANG; return Q ? [Q.x, Q.z] : [0, 52]; };
const introEl = $('g-intro'), lidsEl = $('g-lids');
let banEr = null, flowerHat = null;
/* 站在桥上、台上的人：从上往下找最近的可站面 */
function standY(x, z) { return groundAt(x, z, Math.max(D.hq(x, z), 0) + 4.5)[0]; }
function npcAt(n) {
  if (n.at) { const [x, z] = n.at(); const fy = n.floor && n.floor(); return new V3(x, fy ?? standY(x, z), z); }
  const a = anchor(n.anchor); return n.off ? a.off(n.off) : new V3(a.x, a.y, a.z);
}
function storyWorld() {
  clearWorld(); guide = null; const st = LIU.steps[S.q]; if (!st) { renderStory(); return; }
  const fa = st.face ? st.face() : null;
  st.npcs.forEach((n, i) => {
    let v = npcAt(n); let face;
    if (n.look) face = new V3(n.look[0], 0, n.look[1]); else if (fa) face = new V3(fa[0], 0, fa[1]); else if (n.anchor) { const a = anchor(n.anchor); face = new V3(a.spawn[0], 0, a.spawn[1]); } else face = null;
    if (n.prop) { place(makeProp(n.prop), v, face); return; }
    const seatH = n.sit ? (typeof n.sit === 'number' ? n.sit : 0.5) : 0;
    if (n.sit && n.seat !== 'none') place(makeProp(n.seat || 'chair'), v.clone(), face);   // 座下垫一把椅子（室内已有家具的用 seat:'none'）
    if (n.sit) v = v.clone().setY(v.y + seatH);
    const dest = v.clone(); let leadFrom = null;
    if (n.guide && S.lastNpc && S.lastNpc.who === n.who) { leadFrom = S.lastNpc.pos; v = new V3(leadFrom[0], standY(leadFrom[0], leadFrom[1]), leadFrom[1]); }
    const f = place(n.ghost ? new THREE.Group() : makeFigure(n.color, !n.male, !!n.sit), v, face);
    if (leadFrom && !startGuide(f, leadFrom[0], leadFrom[1], dest.x, dest.z, true)) f.position.copy(dest);
    if (n.ghost) { if (i === 0) S.targets.push({ stage: 'story', obj: f, pos: v, r: 2.2, label: () => T(st, 'label'), where: () => st.place ? pname(placeById(st.place)) : T(st, 'where') }); return; }
    if (i === 0) S.targets.push({ stage: 'story', obj: f, pos: v, r: 2.6, label: () => T(st, 'label'), where: () => st.place ? pname(placeById(st.place)) : T(st, 'where') });
    addTag(() => T(n, 'who'), f, 2.15 * walk.s, i === 0);
  });
  renderStory();
}
function renderStory() {
  const st = LIU.steps[S.q], dots = LIU.steps.map((_, i) => `<i class="${i < S.q ? 'on' : ''}"></i>`).join('');
  questEl.innerHTML = st
    ? `<div class="who"><b>${esc(T(LIU, 'name'))}</b><span>${esc(L(...(st.ch || ['第四十回', 'Chapter 40'])))} · ${S.q + 1}/${LIU.steps.length}</span></div><p class="tip">${esc(T(st, 'tip'))}</p><div class="bag">${L('身边：板儿', 'With you: Ban’er')}${flowerHat && flowerHat.parent ? L(' · 一头菊花', ' · a head full of chrysanthemums') : ''}</div><div class="dots">${dots}</div>`
    : `<div class="who"><b>${esc(T(LIU, 'name'))}</b><span>${L('未完待续', 'To be continued')}</span></div><p class="tip">${esc(L(...LIU.tail))}</p><div class="dots">${dots}</div>`;
  questEl.hidden = !walk.on;
}
/* 凤姐给插的一头菊花 */
function putFlowers(on) {
  if (!on) { if (flowerHat && flowerHat.parent) flowerHat.parent.remove(flowerHat); return; }
  if (!flowerHat) { flowerHat = new THREE.Group(); const cols = ['#c8322e', '#e3b23c', '#f2efe6', '#d96fa0', '#e88a2a', '#b8a0d8'];
    for (let k = 0; k < 16; k++) { const a = k * 2.399, r = 0.05 + (k % 4) * 0.025, up = 0.06 + ((k * 7) % 5) * 0.012;
      const fl = new THREE.Mesh(new THREE.SphereGeometry(0.03 + (k % 3) * 0.008, 8, 6), new THREE.MeshStandardMaterial({ color: cols[k % cols.length], roughness: 0.7 }));
      fl.scale.y = 0.6; fl.position.set(Math.cos(a) * r, up, Math.sin(a) * r - 0.01); flowerHat.add(fl); } }
  hero.head.add(flowerHat);
}
const say1 = ([w, wE, l, lE]) => w ? `<p class="prose"><b>${esc(L(w, wE))}</b>${L('：', ': ')}${esc(L(l, lE))}</p>` : `<p class="prose" style="color:var(--ink-2)">${esc(L(l, lE))}</p>`;
function runPages(pages, k, done) {
  const pg = pages[k]; if (!pg) { done(); return; }
  const go = () => runPages(pages, k + 1, done);
  if (pg.say) { openModal(() => `<div class="ey">${esc(T(LIU, 'name'))} · ${esc(L(...(LIU.steps[S.q]?.ch || ['第四十回', 'Chapter 40'])))}</div>${pg.say.map(say1).join('')}<button class="g-btn" id="g-next">${esc(L(...(pg.btn || ['继续', 'Continue'])))}</button>`,
      () => { if (pg.then === 'flowers') { putFlowers(true); renderStory(); } go(); }); return; }
  if (pg.ask) { const A = pg.ask;
    openModal(() => `<div class="ey">${esc(L(...A.ch))}</div><p class="prose">${esc(L(...A.q))}</p><div class="g-opts g-say">${A.opts.map((o, i) => `<button class="g-opt" data-i="${i}"><i>${i + 1}</i>${esc(L(...o.t))}</button>`).join('')}</div>`, null,
      () => { scrollEl.querySelectorAll('.g-opt').forEach(b => b.onclick = () => { const o = A.opts[+b.dataset.i]; blip(o.best ? 880 : 520);
        openModal(() => `<div class="ey">${esc(L(...A.ch))}</div>${o.best ? `<p class="prose"><b>${L('你', 'You')}</b>${L('：', ': ')}${esc(L(...o.t))}</p><p class="prose" style="color:var(--ink-2)">${esc(A.bestAfter ? L(...A.bestAfter) : L('众人都笑了。', 'Everyone laughed.'))}</p>` : `<p class="prose"><b>${L('你', 'You')}</b>${L('：', ': ')}${esc(L(...o.t))}</p><p class="prose" style="color:var(--ink-2)">${esc(L(...A.after))}</p>`}<button class="g-btn" id="g-next">${L('继续', 'Continue')}</button>`, go); }); });
    return; }
  if (pg.fx === 'slip') { slipAnim(go); return; }
  if (pg.fade) { fadeDo(pg.fade, go); return; }
  if (pg.text) { const R = pg.text;
    openModal(() => `<div class="ey">${esc(T(R, 'ch'))}</div><h3>${esc(T(R, 'title'))}</h3>${(EN() ? R.pEn : R.p).map(t => `<p class="prose">${esc(t)}</p>`).join('')}<div class="ch">${EN() ? `See <i>Dream of the Red Chamber</i>, ${esc(R.chEn)}` : `见《红楼梦》${esc(R.ch)}`}</div><button class="g-btn" id="g-next">${L('继续', 'Continue')}</button>`, go); return; }
  go();
}
function storyInteract(t) {
  const st = LIU.steps[S.q]; blip(660);
  { const n0 = st.npcs && st.npcs[0]; S.lastNpc = n0 && n0.who && n0.at ? { who: n0.who, pos: n0.at() } : null; }
  runPages(st.pages, 0, () => { S.q++; S.done.liu = Math.max(S.done.liu || 0, S.q); saveDone();
    if (S.q >= LIU.steps.length) { finishStory(); return; }
    storyWorld(); flash(T(LIU.steps[S.q], 'tip')); });
}
const liuDone = () => (S.done.liu || 0) >= LIU.steps.length;
/* 走完刘姥姥：自由探索；原来的人物心事、赠礼都从这里接进来 */
function endStory() { S.story = null; S.stage = 'pick'; clearWorld(); if (banEr) scene.remove(banEr); putFlowers(false); questEl.hidden = true; }
function finishStory() {
  clearWorld(); blip(990);
  openModal(() => `<div class="ey">${L('第三十九回 至 第四十二回', 'Chapters 39–42')}</div><h3>${L('刘姥姥进大观园 · 完', 'Granny Liu Visits the Garden · The End')}</h3>
    <p class="prose">${L('园子现在是你的了。可以随便走走，进各处院落、屋里看看；也可以选一个园中人，替她把心事办了；或者把园子里的一处地方，连同一份礼和一句话，送给现实中的一个人。', 'The garden is yours now. Wander anywhere, step into the courtyards and rooms; or choose someone who lives here and help with their wishes; or give a spot in the garden, with a gift and a message, to someone in real life.')}</p>
    <div class="g-opts"><button class="g-opt" id="g-end-walk"><i>1</i>${L('在园子里随便走走', 'Wander the garden')}</button><button class="g-opt" id="g-end-chars"><i>2</i>${L('选一个人入园，办她的心事', 'Choose someone and help with their wishes')}</button><button class="g-opt" id="g-end-gift"><i>3</i>${L('赠一份礼', 'Give a gift')}</button></div>`, null,
    () => { $('g-end-walk').onclick = () => { closeModal(); endStory(); flash(L('自由探索 · 点「入园」可以选人物、收礼赠礼', 'Free exploration · press “Play” to choose someone or give a gift')); };
            $('g-end-chars').onclick = () => { closeModal(); endStory(); showStart(); };
            $('g-end-gift').onclick = () => { endStory(); giftForm(); }; });
}
/* 黑屏转场：字幕一句，必要时换个地方（坐船到对岸） */
const fadeEl = $('g-fade');
function fadeDo(F, done) {
  pauseGame(true); fadeEl.querySelector('p').textContent = L(...F.msg); fadeEl.classList.add('on');
  setTimeout(() => { if (F.to) { const sp = placeById(F.to).spawn, [x, z, yaw] = F.at || sp, g = groundAt(x, z, 99)[0];
      walk.pos.set(x, g, z); walk.feet = g; walk.vel.set(0, 0, 0); walk.vy = 0; walk.yaw = walk.charYaw = yaw;
      if (banEr) banEr.position.set(x + 1, groundAt(x + 1, z + 1, g + 1)[0], z + 1); }
    if (F.hour != null) setWorld(null, F.hour); },
    1200);
  setTimeout(() => { fadeEl.classList.remove('on'); }, 1200 + (F.hold || 2600));
  setTimeout(() => { pauseGame(false); done(); }, 2400 + (F.hold || 2600));
}
/* 宴席上的小摆设 */
function makeProp(kind) {
  const g = new THREE.Group(), wood = new THREE.MeshStandardMaterial({ color: '#5a3422', roughness: 0.6 });
  if (kind === 'table') { const top = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.07, 0.95), wood); top.position.y = 0.78; g.add(top);
    for (const sx of [-0.82, 0.82]) for (const sz of [-0.4, 0.4]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.76, 0.07), wood); l.position.set(sx, 0.38, sz); g.add(l); }
    const cols = ['#f2efe6', '#c8322e', '#e3b23c', '#7aa0b8'];
    for (let k = 0; k < 7; k++) { const d = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.08, 0.05, 14), new THREE.MeshStandardMaterial({ color: cols[k % 4], roughness: 0.4 })); d.position.set(-0.66 + k * 0.22, 0.84, (k % 2 ? 0.18 : -0.16)); g.add(d); } }
  if (kind === 'chair' || kind === 'stool') {   // 座面高 0.46；椅的椅背在 -z（人脸朝 +z）
    const seat = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.05, kind === 'chair' ? 0.48 : 0.5), wood); seat.position.y = 0.44; g.add(seat);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.42, 0.05), wood); l.position.set(sx * 0.24, 0.21, sz * 0.2); g.add(l); }
    if (kind === 'chair') {
      const back = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.52, 0.045), wood); back.position.set(0, 0.74, -0.22); g.add(back);
      for (const sx of [-1, 1]) { const arm = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.04, 0.44), wood); arm.position.set(sx * 0.27, 0.66, -0.02); g.add(arm); }
    }
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; }); return g;
}
/* 苍苔上滑一跤：人往前扑倒，停一会儿，再爬起来 */
function slipAnim(done) {
  pauseGame(true); const g = hero.g, t0 = performance.now(); g.rotation.order = 'YXZ'; blip(150); flash(L('咕咚！', 'Thud!'));
  const step = () => { const t = (performance.now() - t0) / 1000;
    g.rotation.x = t < 0.32 ? -1.3 * (t / 0.32) ** 2 : t < 1.25 ? -1.3 : t < 2.0 ? -1.3 * (1 - (t - 1.25) / 0.75) : 0;
    if (t < 2.05) requestAnimationFrame(step); else { g.rotation.x = 0; pauseGame(false); done(); } };
  requestAnimationFrame(step);
}

/* 带路的人：从上一步站的地方出发，沿走得通的路在前面走；玩家落得太远就站住等 */
let guide = null;
function findPath(ax, az, bx, bz, maxNodes = 400000) {
  const cell = 0.6, X0 = -156, Z0 = -186, NX = Math.ceil(312 / cell), NZ = Math.ceil(322 / cell), memo = new Map();
  const toI = (x, z) => [Math.round((x - X0) / cell), Math.round((z - Z0) / cell)];
  const hOf = (i, j) => { const k = i * NZ + j; let v = memo.get(k); if (v !== undefined) return v; const x = X0 + i * cell, z = Z0 + j * cell; let g = okAt(x, z);
    if (g != null) for (const [dx, dz] of [[0.3, 0], [-0.3, 0], [0, 0.3], [0, -0.3]]) if (okAt(x + dx, z + dz) == null) { g = null; break; }
    memo.set(k, g); return g; };
  /* 草坪（不在石子路、桥、台阶、室内）走起来贵 6 倍，路线就会沿着路走 */
  const lawnM = new Map(), lawn = (i, j) => { const k = i * NZ + j; let v = lawnM.get(k); if (v === undefined) { const x = X0 + i * cell, z = Z0 + j * cell, gr = groundAt(x, z, 99); v = gr[1] && !(window.__dgy.nearPath && window.__dgy.nearPath(x, z, 1.7)); lawnM.set(k, v); } return v; };
  const snap = (x, z) => { const [i0, j0] = toI(x, z); for (let r = 0; r < 8; r++) for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) { if (Math.max(Math.abs(a), Math.abs(b)) !== r) continue; if (hOf(i0 + a, j0 + b) != null) return [i0 + a, j0 + b]; } return null; };
  const s = snap(ax, az), t = snap(bx, bz); if (!s || !t) return null;
  const heap = [], push = (f, k) => { heap.push([f, k]); let c = heap.length - 1; while (c > 0) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
  const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let c = 0; for (;;) { let l = 2 * c + 1, r = l + 1, m = c; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
  const G = new Map(), from = new Map(), key = (i, j) => i * NZ + j, h = (i, j) => Math.hypot(i - t[0], j - t[1]);
  const sk = key(s[0], s[1]); G.set(sk, 0); push(h(s[0], s[1]), sk); let found = false, n = 0;
  while (heap.length && n++ < maxNodes) { const [, k] = pop(); const i = (k / NZ) | 0, j = k % NZ; if (i === t[0] && j === t[1]) { found = true; break; } const cur = hOf(i, j), g0 = G.get(k);
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { if (!a && !b) continue; const ni = i + a, nj = j + b; if (ni < 0 || nj < 0 || ni >= NX || nj >= NZ) continue; const nh = hOf(ni, nj); if (nh == null || Math.abs(nh - cur) > 0.4) continue;
      if (a && b && (hOf(i + a, j) == null || hOf(i, j + b) == null)) continue; const nk = key(ni, nj), ng = g0 + Math.hypot(a, b) * (lawn(ni, nj) ? 6 : 1); if (ng < (G.get(nk) ?? 1e9)) { G.set(nk, ng); from.set(nk, k); push(ng + h(ni, nj), nk); } } }
  if (!found) return null;
  const pts = []; for (let k = key(t[0], t[1]); k !== undefined; k = from.get(k)) { pts.push([X0 + ((k / NZ) | 0) * cell, Z0 + (k % NZ) * cell]); if (k === sk) break; } pts.reverse(); pts.push([bx, bz]);
  const los = (p, q) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]), m = Math.max(2, Math.ceil(L / 0.4)); let y = null; for (let u = 0; u <= m; u++) { const x = p[0] + (q[0] - p[0]) * u / m, z = p[1] + (q[1] - p[1]) * u / m, g = okAt(x, z); if (g == null || (y != null && Math.abs(g - y) > 0.4)) return false; y = g;
    if (u && u < m && Math.min(Math.hypot(x - p[0], z - p[1]), Math.hypot(x - q[0], z - q[1])) > 2.5 && lawn(...toI(x, z))) return false; } return true; };
  const out = [pts[0]]; let i = 0; while (i < pts.length - 1) { let j = pts.length - 1; while (j > i + 1 && !los(pts[i], pts[j])) j--; out.push(pts[j]); i = j; } return out;
}
function startGuide(fig, ax, az, bx, bz, faceTo) {
  const path = findPath(ax, az, bx, bz); guide = path && path.length > 1 ? { fig, path, i: 1, faceTo } : null; return !!guide;
}
function followGuide(dt) {
  const G = guide; if (!G || !G.fig.parent) return; const f = G.fig, p = walk.pos, x = f.position.x, z = f.position.z;
  if (G.i >= G.path.length) { if (G.faceTo) f.rotation.y = Math.atan2(p.x - x, p.z - z); return; }
  if (Math.hypot(p.x - x, p.z - z) > 9 && G.moved) { f.position.y = groundAt(x, z, f.position.y + 0.6)[0]; return; }   // 等你跟上
  const [tx, tz] = G.path[G.i], dx = tx - x, dz = tz - z, d = Math.hypot(dx, dz), step = Math.min(d, 2.6 * walk.s * dt);
  if (d < 0.05) { G.i++; return; }
  f.position.x += dx / d * step; f.position.z += dz / d * step; G.moved = true; f.rotation.y = Math.atan2(dx, dz);
  f.position.y = groundAt(f.position.x, f.position.z, f.position.y + 0.6)[0] + Math.abs(Math.sin(performance.now() / 170)) * 0.03;
}
/* 板儿跟在身后半步 */
function followBanEr(dt) {
  if (!banEr || !banEr.parent) return; const p = walk.pos, yaw = walk.charYaw ?? walk.yaw, f = new V3(-Math.sin(yaw), 0, -Math.cos(yaw));
  const tx = p.x - f.x * 1.3 + f.z * 0.9, tz = p.z - f.z * 1.3 - f.x * 0.9; const dx = tx - banEr.position.x, dz = tz - banEr.position.z, d = Math.hypot(dx, dz);
  if (d > 12) { banEr.position.set(tx, groundAt(tx, tz, p.y + 1)[0], tz); return; }
  if (d > 0.25) { const k = Math.min(1, dt * (d > 3 ? 3.5 : 2.2)); banEr.position.x += dx * k; banEr.position.z += dz * k; banEr.rotation.y = Math.atan2(dx, dz); }
  banEr.position.y = groundAt(banEr.position.x, banEr.position.z, p.y + 1)[0];
}
function liuIntro() {
  pauseGame(true); startEl.hidden = true; clearWorld();
  S.char = null; S.giftMode = false; S.story = 'liu'; S.stage = 'story'; S.q = 0; S.carrying = null; putFlowers(false);
  dressHero(LIU.look); setWorld(LIU.season, LIU.hour); document.body.classList.add('g-playing');
  let i = -1, busy = null;
  const paint = () => { const [zh, en, cls] = LIU.intro[i]; introEl.innerHTML = `<p class="ln ${cls || ''}">${esc(L(zh, en))}</p><button class="skip" id="g-intro-skip">${L('跳过', 'Skip')}</button><div class="hint">${isTouch ? L('点一下继续', 'Tap to continue') : L('点击或按空格继续', 'Click or press Space to continue')}</div>`;
    requestAnimationFrame(() => requestAnimationFrame(() => introEl.querySelector('.ln')?.classList.add('on'))); $('g-intro-skip').onclick = (e) => { e.stopPropagation(); wake(); }; };
  /* 淡出中再点：不等，直接换下一句 */
  const next = () => { if (busy) { clearTimeout(busy); busy = null; i++; paint(); return; } if (i >= LIU.intro.length - 1) { wake(); return; }
    const old = introEl.querySelector('.ln'); if (old) { old.classList.remove('on'); busy = setTimeout(() => { busy = null; i++; paint(); }, 700); } else { i++; paint(); } };
  const onKey = (e) => { if (introEl.hidden) return; if (e.code === 'Space' || e.code === 'Enter' || e.code === 'ArrowRight') { e.preventDefault(); e.stopImmediatePropagation(); next(); } else if (e.code === 'Escape') { e.stopImmediatePropagation(); wake(); } };
  /* 睁眼：眼皮张开两次，画面由模糊转清 */
  const wake = () => { if (introEl.hidden || introEl.classList.contains('out')) return; removeEventListener('keydown', onKey, true);
    if (walk.on) exitWalk(); walk.third = false; enterWalk(LIU.spawn); pauseGame(true);
    if (!banEr) { banEr = makeFigure('#7a8a5a', false); banEr.scale.setScalar(0.62 * walk.s); }
    banEr.position.set(1.0, groundAt(1.0, 132.4, 2)[0], 132.4); banEr.rotation.y = Math.PI; scene.add(banEr);
    storyWorld();
    const cv = D.renderer.domElement; cv.style.transition = 'none'; cv.style.filter = 'blur(12px) brightness(.55)';
    lidsEl.hidden = false; lidsEl.innerHTML = '<i></i><i></i>';
    introEl.classList.add('out'); setTimeout(() => { introEl.hidden = true; introEl.classList.remove('out'); }, 1700);
    requestAnimationFrame(() => { cv.style.transition = 'filter 3.4s ease-out'; cv.style.filter = ''; });
    setTimeout(() => { lidsEl.hidden = true; cv.style.transition = ''; pauseGame(false); renderStory();
      flash(isTouch ? L('左下角摇杆走路 · 跟着光柱走', 'Use the stick to walk · follow the beam of light') : L('WASD 走路 · 鼠标转头 · 跟着光柱走', 'WASD to walk · mouse to look · follow the beam of light')); }, 3700);
  };
  introEl.hidden = false; introEl.classList.remove('out'); introEl.onclick = next; addEventListener('keydown', onKey, true); next();
}
function beginGift() {
  S.char = null; S.story = null; if (banEr) scene.remove(banEr); S.giftMode = true; clearWorld(); document.body.classList.add('g-playing'); pauseGame(false);
  const g = S.gift, id = placeById(g.p) ? g.p : 'qinfang', a = anchor(id); const v = a.off(2.2);
  const o = place(makeItem('gift'), v); S.targets = [{ stage: 'gift', obj: o, pos: v, r: 2.2, label: () => L('打开' + (g.f ? g.f + '的' : '') + '礼', g.f ? `Open ${g.f}’s gift` : 'Open the gift') }]; S.stage = 'gift'; addTag(() => L('给你的礼', 'A gift for you'), o, 0.7, true);
  renderGiftQuest();
  walk.third = false; enterWalk(spawnAt(id)); questEl.hidden = false;
}
function renderGiftQuest() {
  const g = S.gift, id = placeById(g.p) ? g.p : 'qinfang', pn = esc(pname(placeById(id)));
  questEl.innerHTML = `<div class="who"><b>${L('收礼', 'A Gift')}</b><span>${pn}</span></div><p class="tip">${EN() ? `${esc(g.f || 'Someone')} left the gift at ${pn}. Follow the beam of light.` : `${esc(g.f || '有人')}把礼放在了${pn}。跟着光柱走过去。`}</p>`;
}
function interact() {
  if (!S.near && nearDoor) { goThroughDoor(); return; }
  const t = S.near; if (!t || t.stage !== S.stage || !t.obj.parent) return; S.near = null;
  if (S.stage === 'gift') { openGift(); return; }
  if (S.story) { storyInteract(t); return; }
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
  const C = CHARS[S.char] || { name: LIU.name, nameEn: LIU.nameEn, start: 'gate' }; let keep = null, made = null;
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
  if (!modalEl.hidden) { e.stopImmediatePropagation();
    { const m = /^Digit([1-9])$/.exec(e.code), o = m && scrollEl.querySelectorAll('.g-opt')[+m[1] - 1]; if (o) { e.preventDefault(); o.click(); return; } } if ((e.code === 'KeyE' || e.code === 'Enter' || e.code === 'Space') && $('g-next') && !$('gf-make')) { e.preventDefault(); closeModal(); } return; }
  if (!startEl.hidden) { e.stopImmediatePropagation(); return; }
  if (e.code === 'KeyE' && walk.on && (S.near || nearDoor)) { e.preventDefault(); interact(); }
}, true);
promptEl.addEventListener('click', interact);

/* ---------------------------------------------------------------------
   每帧：指引、提示、标签、道具浮动
   --------------------------------------------------------------------- */

/* ---------------------------------------------------------------------
   门：走近任何一座建筑的门，提示「进门 / 出门」，按 E（手机点提示）穿过去
   --------------------------------------------------------------------- */
const GATES = [   // [建筑根节点 id, 局部 x, 局部 z, 中文名, 英文名]（局部坐标跟着建筑走）
  ['hengwu', 0, 13.75, '蘅芜苑 · 院门', 'Alpinia Park · gate'],
  ['yihong', -20.05, 11.05, '怡红院 · 院门', 'Happy Red Court · gate'],
  ['daoxiang', -4, -0.8, '稻香村 · 柴门', 'Paddy-Sweet Cottage · door'],
  ['daoxiang', 14.4, -14, '稻香村 · 院门', 'Paddy-Sweet Cottage · gate'],
  ['longcui', 0, 7.7, '栊翠庵 · 山门', 'Green Lattice Nunnery · gate'],
  ['tubi', 0, 1.2, '凸碧山庄', 'Convex Emerald Hall'],
  ['aojing', 0, -3.2, '凹晶馆', 'Concave Crystal Lodge'],
  ['luxue', 0, -5, '芦雪广', 'Reed Snow Cottage'],
  ['qiushuang', 0, 12.6, '秋爽斋 · 院门', 'Autumn Freshness Studio · gate']];
let DOORS = [], doorKey = '', nearDoor = null, doorBusy = false;
function buildDoors() {
  const key = D.BLD.length + ':' + D.INTER.length; if (key === doorKey) return; doorKey = key;
  DOORS = [{ x: 0, z: 120, n: '大观园 · 正门', ne: 'Grand View Garden · Main Gate' }];
  for (const [id, lx, lz, n, ne] of GATES) { const b = D.BLD.find(b => b.id === id); if (!b) continue; const v = b.root.localToWorld(new V3(lx, 0, lz)); DOORS.push({ x: v.x, z: v.z, n, ne }); }
  for (const it of D.INTER) it.rooms.forEach((r, i) => {   // 室内房间：门在南面（局部 +z）边中点；r[6]==='e' 表示门在东面
    const east = r[6] === 'e', ex = Array.isArray(r[6]); const v = it.root.localToWorld(ex ? new V3(r[6][0], r[4], r[6][1]) : new V3(east ? r[2] : (r[0] + r[2]) / 2, r[4], east ? (r[1] + r[3]) / 2 : r[3]));
    DOORS.push({ x: v.x, z: v.z, room: { it, r }, n: (it.names && it.names[i]) || it.name, ne: (it.namesEn && it.namesEn[i]) || it.en || it.name }); });
}
const insideRoom = (rm, p) => { const v = rm.it.root.worldToLocal(p.clone()), r = rm.r; return v.x > r[0] && v.x < r[2] && v.z > r[1] && v.z < r[3] && v.y > r[4] - 0.6 && v.y < r[5] + 0.6; };
function doorUpdate() {
  buildDoors(); let best = null, bd = 1e9; const p = walk.pos;
  if (walk.on && modalEl.hidden && startEl.hidden && !doorBusy && !window.__gamePause) {
    const fx = -Math.sin(walk.yaw), fz = -Math.cos(walk.yaw);
    for (const d of DOORS) { const dx = d.x - p.x, dz = d.z - p.z, dd = Math.hypot(dx, dz); if (dd > 3.0 || dd < 0.1) continue; if ((dx * fx + dz * fz) / dd < 0.2) continue; if (dd < bd) { bd = dd; best = d; } }
  }
  nearDoor = best;
  if (!best) { promptEl.hidden = true; return; }
  const ins = best.room ? insideRoom(best.room, p) : null;
  best.label = (ins === true ? L('出门', 'Go out') : ins === false ? L('进门', 'Go in') : L('过门', 'Pass through')) + ' · ' + L(best.n, best.ne);
  promptEl.innerHTML = (isTouch ? `<span>${L('点这里', 'Tap here')}</span>` : '<kbd>E</kbd>') + esc(best.label); promptEl.hidden = false;
}
function goThroughDoor() {
  const d = nearDoor; if (!d || doorBusy) return; doorBusy = true; blip(540);
  const p = walk.pos; let dx = d.x - p.x, dz = d.z - p.z; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
  let dest = null; for (const dist of [2.3, 1.8, 1.3]) { const x = d.x + dx * dist, z = d.z + dz * dist; if (okAt(x, z) != null) { dest = [x, z]; break; } }
  if (!dest) dest = [d.x + dx * 1.3, d.z + dz * 1.3];
  const blink = $('g-blink'); blink.classList.add('on'); pauseGame(true);
  setTimeout(() => { const gy = groundAt(dest[0], dest[1], p.y + 0.6)[0]; walk.pos.set(dest[0], gy, dest[1]); walk.feet = gy; walk.vel.set(0, 0, 0); walk.vy = 0; walk.grounded = true; walk.yaw = walk.charYaw = Math.atan2(-dx, -dz); flash(d.label); blink.classList.remove('on'); }, 260);
  setTimeout(() => { pauseGame(false); doorBusy = false; }, 640);
}

/* ---------------------------------------------------------------------
   花瓣引路：从脚下往目标沿着走得通的路飘一串花瓣；目标近了就散去
   --------------------------------------------------------------------- */
const PET_N = 64;
/* 桃花瓣：窄柄、圆肩、顶端一个小缺口，微微内卷；贴一张由柄部淡黄白渐到瓣缘粉红、带细脉的贴图 */
function petalGeo() {
  const W = 0.055, H = 0.085, sh = new THREE.Shape();
  sh.moveTo(0, 0); sh.bezierCurveTo(W * 0.35, H * 0.08, W, H * 0.45, W * 0.92, H * 0.78);
  sh.bezierCurveTo(W * 0.85, H * 0.97, W * 0.35, H * 1.02, 0, H * 0.9);   // 顶端缺口
  sh.bezierCurveTo(-W * 0.35, H * 1.02, -W * 0.85, H * 0.97, -W * 0.92, H * 0.78);
  sh.bezierCurveTo(-W, H * 0.45, -W * 0.35, H * 0.08, 0, 0);
  const geo = new THREE.ShapeGeometry(sh, 10), P = geo.attributes.position, uv = geo.attributes.uv;
  for (let i = 0; i < P.count; i++) { const x = P.getX(i), y = P.getY(i); P.setZ(i, (x / W) ** 2 * 0.018 - (y / H) * 0.012); uv.setXY(i, x / (2 * W) + 0.5, y / H); }
  geo.translate(0, -H * 0.45, 0); geo.computeVertexNormals(); return geo;
}
function petalTex() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 64; const x = c.getContext('2d');
  const gr = x.createRadialGradient(32, 64, 2, 32, 40, 62); gr.addColorStop(0, '#fff6dc'); gr.addColorStop(0.35, '#fff0f3'); gr.addColorStop(1, '#f7a9be');
  x.fillStyle = gr; x.fillRect(0, 0, 64, 64); x.strokeStyle = 'rgba(220,120,150,.28)'; x.lineWidth = 0.8;
  for (let i = -3; i <= 3; i++) { x.beginPath(); x.moveTo(32, 64); x.quadraticCurveTo(32 + i * 5, 34, 32 + i * 8.5, 4); x.stroke(); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const petals = new THREE.InstancedMesh(petalGeo(), new THREE.MeshBasicMaterial({ map: petalTex(), color: '#ffffff', side: THREE.DoubleSide, transparent: true, opacity: 0.96, depthWrite: false }), PET_N);
petals.frustumCulled = false; petals.visible = false; petals.renderOrder = 6; scene.add(petals);
{ const tint = ['#ffffff', '#ffe8ee', '#ffd6e0', '#fff4f6', '#ffdfe6']; for (let i = 0; i < PET_N; i++) petals.setColorAt(i, new THREE.Color(tint[i % tint.length])); }
const petalSeed = Array.from({ length: PET_N }, (_, i) => ({ lat: (Math.random() - 0.5) * 1.3, ph: Math.random() * 6.283, h: 0.2 + Math.random() * 0.9, sp: 0.8 + Math.random() * 0.5, o: i / PET_N }));
const _pd = new THREE.Object3D(); let PP = null, ppT = -1e9;
function buildPP(gx, gz, p, now) {
  let path = findPath(p.x, p.z, gx, gz, 80000); if (!path || path.length < 2) path = [[p.x, p.z], [gx, gz]];
  const cum = [0]; for (let i = 1; i < path.length; i++) cum.push(cum[i - 1] + Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]));
  PP = { gx, gz, path, cum, len: cum[cum.length - 1] }; ppT = now;
}
function ppNearest(p) {   // 玩家在路线上的最近位置（弧长）与偏离距离
  let best = 1e9, bs = 0; const P = PP.path;
  for (let i = 1; i < P.length; i++) { const ax = P[i - 1][0], az = P[i - 1][1], bx = P[i][0], bz = P[i][1], dx = bx - ax, dz = bz - az, L2 = dx * dx + dz * dz || 1;
    const t = Math.max(0, Math.min(1, ((p.x - ax) * dx + (p.z - az) * dz) / L2)), x = ax + dx * t, z = az + dz * t, d = Math.hypot(p.x - x, p.z - z); if (d < best) { best = d; bs = PP.cum[i - 1] + Math.sqrt(L2) * t; } }
  return [bs, best];
}
function ppAt(s) {
  const P = PP.path, C = PP.cum; s = Math.max(0, Math.min(PP.len, s)); let i = 1; while (i < P.length - 1 && C[i] < s) i++;
  const L = (C[i] - C[i - 1]) || 1, t = (s - C[i - 1]) / L; return [P[i - 1][0] + (P[i][0] - P[i - 1][0]) * t, P[i - 1][1] + (P[i][1] - P[i - 1][1]) * t, (P[i][0] - P[i - 1][0]) / L, (P[i][1] - P[i - 1][1]) / L];
}
function updatePetals(goal, p, now) {
  if (!goal || !walk.on) { petals.visible = false; return; }
  const gx = goal.pos.x, gz = goal.pos.z; if (Math.hypot(gx - p.x, gz - p.z) < 4) { petals.visible = false; return; }
  if (now - ppT > 1500 && (!PP || Math.hypot(PP.gx - gx, PP.gz - gz) > 2 || ppNearest(p)[1] > 3.5)) buildPP(gx, gz, p, now);
  if (!PP) { petals.visible = false; return; }
  const [s0] = ppNearest(p), WIN = Math.min(18, PP.len - s0 - 1.5); if (WIN < 2) { petals.visible = false; return; }
  petals.visible = true;
  for (let i = 0; i < PET_N; i++) { const q = petalSeed[i], t = (q.o + now * 0.00016 * q.sp) % 1, s = s0 + 1.4 + t * WIN, [x0, z0, dx, dz] = ppAt(s);
    const spread = q.lat * (0.3 + 0.7 * t), x = x0 - dz * spread + Math.sin(now * 0.002 + q.ph) * 0.18, z = z0 + dx * spread + Math.cos(now * 0.0017 + q.ph) * 0.18;
    const y = groundAt(x, z, p.y + 1.2)[0] + (0.15 + q.h * 0.55) * walk.s + Math.sin(now * 0.0032 + q.ph) * 0.1;
    const k = Math.min(1, t * 8) * (1 - Math.max(0, (t - 0.82) / 0.18));   // 近处淡入、远处散去
    _pd.position.set(x, y, z); _pd.rotation.set(0.8 + Math.sin(now * 0.004 + q.ph) * 0.9, now * 0.0025 * q.sp + q.ph, now * 0.0018 + q.ph); _pd.scale.setScalar(Math.max(0.001, k) * (0.9 + q.h * 0.35)); _pd.updateMatrix(); petals.setMatrixAt(i, _pd.matrix); }
  petals.instanceMatrix.needsUpdate = true; if (petals.instanceColor) petals.instanceColor.needsUpdate = true;
}

const _v = new V3(); let last = performance.now();
function tick(now) {
  requestAnimationFrame(tick); const dt = Math.min(0.05, (now - last) / 1000); last = now; beaconMat.uniforms.t.value = now / 1000;
  const playing = (S.char || S.giftMode || S.story) && walk.on; if (S.story) { followBanEr(dt); followGuide(dt); }
  questEl.hidden = !(playing || (S.giftMode && walk.on));
  if (!playing) { compassEl.hidden = true; petals.visible = false; doorUpdate(); beacon.visible = groundRing.visible = false; for (const t of S.tags) t.el.style.display = 'none'; return; }
  for (const t of S.targets) if (t.bob) t.obj.position.y = t.obj.userData.baseY + Math.sin(now / 500) * 0.06, t.obj.rotation.y += dt * 0.6;
  const goal = currentGoal(); const p = walk.pos;
  if (goal) {
    const d = Math.hypot(goal.pos.x - p.x, goal.pos.z - p.z);
    beacon.visible = d > 7; beacon.position.set(goal.pos.x, goal.pos.y, goal.pos.z); beaconMat.uniforms.a.value = Math.min(1, (d - 7) / 12);
    groundRing.visible = d < 18; groundRing.position.set(goal.pos.x, goal.pos.y + 0.04, goal.pos.z); ringMat.opacity = 0.35 + Math.sin(now / 300) * 0.2;
    // 指南：相对镜头朝向的方位
    const ang = Math.atan2(goal.pos.x - p.x, goal.pos.z - p.z); const camYaw = Math.atan2(-(Math.sin(walk.yaw)), -(Math.cos(walk.yaw)));
    let rel = ang - camYaw; rel = Math.atan2(Math.sin(rel), Math.cos(rel));
    const Q = S.char ? CHARS[S.char].quests[S.q] : null; const where = goal.where ? goal.where() : pname(S.giftMode ? placeById(S.gift.p) : placeById(S.stage === 'pick' ? Q.pick.place : Q.give.place));
    compassEl.hidden = d < 5; compassEl.querySelector('svg').style.transform = `rotate(${-rel}rad)`; compassEl.querySelector('b').textContent = where; compassEl.querySelector('span').textContent = Math.round(d / 0.75) + L(' 步', ' steps');
  } else { compassEl.hidden = true; beacon.visible = groundRing.visible = false; }
  updatePetals(goal, p, now);
  // 最近的可交互目标
  let near = null; for (const t of S.targets) { if (t.stage !== S.stage) continue; const d = Math.hypot(t.pos.x - p.x, t.pos.z - p.z); if (d < t.r && Math.abs(t.pos.y - p.y) < 2.5) { near = t; break; } }
  S.near = modalEl.hidden ? near : null;
  if (S.near) { promptEl.innerHTML = isTouch ? `<span>${L('点这里', 'Tap here')}</span>${esc(txt(S.near.label))}` : `<kbd>E</kbd>${esc(txt(S.near.label))}`; promptEl.hidden = false; nearDoor = null; } else doorUpdate();
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
  if (S.char || S.story) renderQuest(); else if (S.giftMode && S.gift && S.stage === 'gift') renderGiftQuest();
  if (!startEl.hidden) showStart(startEl.dataset.mode === 'gift');
  if (!modalEl.hidden && modalPaint) modalPaint();
});

/* 调试接口（测试用） */
window.__game = { get guide() { return guide; }, followGuide, findPath, okAt, S, CHARS, LIU, liuIntro, storyWorld, beginChar, interact, anchor, stageWorld, encodeGift, decodeGift, showStart, closeModal, beginGift };

/* 开场：链接里带礼 → 收礼；否则显示选人 */
{ const g = decodeGift(location.hash || ''); if (g) { S.gift = g; showStart(true); } else if (liuDone()) showStart(); else liuIntro(); }
