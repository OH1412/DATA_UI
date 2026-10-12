import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { BookOpen, CheckCircle2, CircleAlert, ClipboardCheck, Layers3, Network, X } from 'lucide-react';

type GuideSection={id:string;label:string;icon:typeof BookOpen;intro:string;items:{title:string;text:string;kind?:'good'|'warn'}[]};
const sections:GuideSection[]=[
 {id:'flow',label:'采集流程',icon:ClipboardCheck,intro:'先建立稳定、可复现的示教协议，再逐步扩大任务和环境的变化范围。',items:[
  {title:'先练习，再正式采集',text:'正式采集前先完整练习。连贯、有意识、前后统一的示教，比犹豫、试探或反复重来的轨迹更有价值。'},
  {title:'一次流畅完成一条 Episode',text:'正式录制从操作开始到任务结束连续完成，避免碰撞、试探、无意义悬停和反复尝试。操作开始立即录制，结束立即停止。'},
  {title:'固定任务协议',text:'保持任务目标、执行顺序、成功判据和结束姿态一致。需要改变策略时，先停止当前批次并记录新版本。'},
  {title:'质量优先，再优化速度',text:'先形成高质量、稳定、可复现的策略；确认质量达标后再缩短准备和操作时间，不能为了速度牺牲数据质量。'}]},
 {id:'record',label:'录制与同步',icon:Network,intro:'Whole-Body VLA 需要让视觉、语言、动作和本体状态在同一时间轴上对齐。',items:[
  {title:'相机和硬件保持固定',text:'正式采集期间不要移动机械臂、相机、夹爪或动捕传感器，也不要改变安装位置和角度。发生变化时应重新标定并开启新的采集批次。'},
  {title:'至少保留互补视角',text:'优先使用两路或更多互补视角，例如 front / top / wrist；主任务视角应持续看到机器人末端和被操作物体。示教者身体可出现在参考视角，但不应遮挡任务主体。'},
  {title:'统一时间戳与频率',text:'视频、全身关节、手部、末端位姿、夹爪状态和控制指令必须使用可对齐的时间戳。视频建议约 30 FPS；动作数据按设备能力使用更高频率并记录实际频率。'},
  {title:'采集前确认坐标系',text:'记录机器人基座、相机、动捕空间和物体坐标系的关系；重新布置场景或传感器后，不要沿用旧的外参。'}]},
 {id:'variation',label:'数据规模',icon:Layers3,intro:'先用小规模数据验证策略，再有计划地引入变量，避免一次改变太多因素。',items:[
  {title:'从可验证的小任务开始',text:'简单任务可先收集约 50–100 条高质量 Episode 作为基线。入门任务可以是将不同位置的物体放入收纳箱，并为每个位置保持均衡样本。数量不是硬指标，应以质量和覆盖度为准。'},
  {title:'一次只引入少量变量',text:'在基线策略稳定后，再逐步改变物体位置、外观、背景、光照、抓取方式或相机位姿。每次变化都要记录，避免短时间内引入过多变量。'},
  {title:'为泛化保留稳定锚点',text:'泛化不是让所有因素同时随机化。应保留任务语义、机器人本体和关键坐标的稳定锚点，再有计划地扩展环境与物体分布。'}]},
 {id:'schema',label:'标注与格式',icon:BookOpen,intro:'清晰的任务语义和一致的数据 schema，是让异质 Whole-Body 数据可联合训练的基础。',items:[
  {title:'任务描述要具体',text:'用简洁、可执行的语言描述目标，例如“拿起黄色方块并放入左侧收纳箱”。避免空白、task1、demo2、“握住”或“任务描述”等无法表达上下文的标签。'},
  {title:'统一模态和视角命名',text:'建议使用可解释的命名：images.front、images.top、images.wrist.left；动作、状态、语言和事件字段也要在不同数据集间保持一致。'},
  {title:'记录 Whole-Body 状态',text:'除末端动作外，尽量记录全身关节、根部位姿、双手、头部朝向、夹爪/手指状态、接触事件和控制模式，并明确单位、坐标系和关节顺序。'},
  {title:'每条 Episode 都要完整',text:'检查开始/结束时间、帧数、视频索引、动作与状态长度、任务文本和机器人配置是否齐全。删除或修剪序列后要同步更新索引和元数据。'}]},
 {id:'quality',label:'质量检查',icon:ClipboardCheck,intro:'把检查前移到采集现场，问题越早发现，返工成本越低。',items:[
  {title:'图像质量',text:'画面稳定、曝光和对焦一致、光照尽量中性；任务物体和机器人关键部位不出视野。建议至少达到设备稳定支持的 720p 级别，低带宽时优先保证清晰度和稳定性。'},
  {title:'动作质量',text:'轨迹连续、少碰撞、少停顿；双手和下肢动作与任务上下文一致。异常振动、遮挡或操作者不适应时先处理硬件，不要继续堆积数据。'},
  {title:'同步质量',text:'抽查视频、动作和状态是否在同一事件上对齐；检查丢帧、重复帧、时间戳回退、数据流断开和无效关节。'},
  {title:'批次质量',text:'每个批次保存设备配置、场景版本、操作者、任务版本、标定版本和异常说明，方便定位问题和复现实验。'}]},
 {id:'issues',label:'常见问题',icon:CircleAlert,intro:'以下问题会显著降低 Whole-Body VLA 的可学习性和跨设备迁移能力。',items:[
  {title:'任务标注模糊或不完整',text:'缺少目标、对象、位置或成功条件时，模型难以学习语言与动作的对应关系。补齐任务和子任务层级。',kind:'warn'},
  {title:'视角或特征含义不一致',text:'不要让同一个字段在不同数据集中一会儿代表第三人称相机、一会儿代表腕部相机；统一映射并在元数据中声明。',kind:'warn'},
  {title:'动作/状态维度不一致',text:'同一机器人或不同具身形态之间，关节顺序、动作维度、单位和坐标系必须显式记录；不能只依赖字段名猜测。',kind:'warn'},
  {title:'短序列与索引损坏',text:'只有 1 帧、极短序列、视频与 parquet 不匹配、删文件后未更新索引，都会破坏时序训练，应在入库前拦截。',kind:'warn'}]},
];

export function DataGuide(){const [open,setOpen]=useState(false);const [active,setActive]=useState('flow');const [host,setHost]=useState<Element|null>(null);useEffect(()=>setHost(document.querySelector('.workspace-nav')),[]);const section=sections.find(x=>x.id===active)||sections[0];const button=<button className="guide-nav-button" onClick={()=>setOpen(true)}><BookOpen size={15}/> 数据指南</button>;const modal=open&&<div className="guide-backdrop" onClick={()=>setOpen(false)}><section className="guide-modal guide-modal-wide" onClick={e=>e.stopPropagation()}><header className="guide-modal-head"><div><span className="eyebrow">LITCHI DATA SPACE / WHOLE-BODY VLA FIELD GUIDE</span><h2>人形机器人数据采集指南</h2><p>面向视觉—语言—动作模型的高质量真实世界数据采集规范。</p></div><button className="icon-button" onClick={()=>setOpen(false)} aria-label="关闭数据指南"><X size={18}/></button></header><div className="guide-body"><nav className="guide-sections">{sections.map(({id,label,icon:Icon})=><button className={active===id?'active':''} key={id} onClick={()=>setActive(id)}><Icon size={15}/>{label}</button>)}</nav><div className="guide-content"><div className="guide-section-intro"><span>0{sections.findIndex(x=>x.id===active)+1}</span><div><b>{section.label}</b><p>{section.intro}</p></div></div>{section.items.map((item,i)=><article className={`guide-item ${item.kind||''}`} key={item.title}><span>{String(i+1).padStart(2,'0')}</span><div><h3>{item.title}</h3><p>{item.text}</p></div>{item.kind==='warn'?<CircleAlert size={16}/>:<CheckCircle2 size={16}/>}</article>)}</div></div><footer className="guide-modal-foot"><span><CheckCircle2 size={15}/> 采集前检查：流程、硬件、标定、背景、同步、存储</span><button className="primary-button" onClick={()=>setOpen(false)}>我已了解</button></footer></section></div>;return <>{host?createPortal(button,host):null}{modal}</>}
