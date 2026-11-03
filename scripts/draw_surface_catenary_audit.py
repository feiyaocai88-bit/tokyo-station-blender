"""Create a model-only numbered PNG plan and offline clickable SVG report.

Requires NumPy and Pillow. No photos, network requests or model changes.
"""
from pathlib import Path
import html, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'images/catenary_audit';OUT.mkdir(parents=True,exist_ok=True)
AUDIT=json.loads((ROOT/'validation/surface_catenary_audit.json').read_text(encoding='utf8'))
T=json.loads((ROOT/'scripts/targets.json').read_text(encoding='utf8'))
LABELS={
    'inherited_procedural_unverified':('旧版生成位置 · 未实景核准','#48627d'),
    'V14_photo_chainage_estimate_lateral_fitted':('V14 照片纵向估算 · 横向适配','#087f8c'),
    'model_end_adaptation':('V14 模型末端适配','#b26b00'),
    'curve_constraint_unverified':('V14 曲线约束增设 · 未核准','#8b49a5'),
}
W,H=1900,1500
im=Image.new('RGB',(W,H),'#f3f5f8');draw=ImageDraw.Draw(im)
font_path=os.environ.get('CATENARY_AUDIT_FONT')
if not font_path:
    font_path=next((str(p) for p in [Path('C:/Windows/Fonts/msyh.ttc'),Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')] if p.exists()),None)
if not font_path:
    raise RuntimeError('Set CATENARY_AUDIT_FONT to an installed Chinese TrueType/OpenType font.')
fonts={s:ImageFont.truetype(font_path,s) for s in [12,14,17,18,20,25,34]}
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="175 根支柱的模型坐标图"><rect width="100%" height="100%" fill="#f3f5f8"/>']

def text(x,y,s,size=18,color='#253449'):
    draw.text((x,y),s,font=fonts[size],fill=color)
    svg.append(f'<text x="{x:.1f}" y="{y+size:.1f}" font-size="{size}" fill="{color}">{html.escape(s)}</text>')

def line(points,color='#d9e0e7',width=1):
    draw.line(points,fill=color,width=width)
    svg.append('<polyline points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')

def polygon(points,color):
    draw.polygon(points,fill=color)
    svg.append('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in points)+f'" fill="{color}"/>')

def rect(a,b,c,d,color):
    draw.rectangle((a,b,c,d),fill=color)
    svg.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{color}"/>')

text(45,25,'东京站 · 地上接触网杆位检查',34)
text(45,76,'V15 模型坐标图｜175 根独立支柱｜本轮未移动杆位｜2026-11-03',20)
text(45,112,'站台中、北段仍为旧版生成位置；几何检查通过，不等于与实景逐根一致。',20,'#914b08')
for i,(key,(label,color)) in enumerate(LABELS.items()):
    x=45+i*465
    draw.ellipse((x,158,x+12,170),fill=color)
    svg.append(f'<circle cx="{x+6}" cy="164" r="6" fill="{color}"/>')
    text(x+20,150,label,17)
text(45,187,'← 北 / 模型 -X              南 / 模型 +X →     ·     各图上方为模型东侧；分区比例不同。浅灰为模型站台轮廓。',17,'#5e6b7a')

panels=[
    ('Chuo','中央线 1 / 2 番线：40 根',230,270,-220,125,9,47,['01','02']),
    ('conventional','在来线及交界：122 根',520,400,-220,250,32,126,[f'{i:02}' for i in range(3,11)]),
    ('Shinkansen','新干线露天区：13 根独立柱（顶棚悬吊支点另计）',940,400,-220,250,94,214,['20','21','22','23','14','15','16','17','18','19']),
]
for zone,title,top,height,xmin,xmax,ymin,ymax,tracks in panels:
    rect(35,top,1865,top+height,'#ffffff');text(55,top+12,title,25)
    left,right,pt,pb=85,1800,top+62,top+height-33
    def xy(x,y):return (left+(x-xmin)/(xmax-xmin)*(right-left),pb-(y-ymin)/(ymax-ymin)*(pb-pt))
    for x in range(int(np.ceil(xmin/25)*25),int(xmax)+1,25):
        a,b=xy(x,ymin),xy(x,ymax);line([a,b]);text(a[0]-14,pb+5,str(x),12,'#7b8795')
    for island,v in T['islands'].items():
        if v['west'] not in tracks:continue
        xx=np.linspace(*v['P'],100)
        yy1=np.interp(xx,T['X'],T['target'][v['west']])+v['edge']
        yy2=np.interp(xx,T['X'],T['target'][v['east']])-v['edge']
        polygon([xy(x,y) for x,y in zip(xx,yy1)]+[xy(x,y) for x,y in zip(xx[::-1],yy2[::-1])],'#e9edf0')
    for k in tracks:
        end=124 if zone=='Chuo' else (190 if k in ['20','21'] else 185 if k in ['22','23'] else 245)
        xx=np.linspace(xmin,min(xmax,end),400);yy=np.interp(xx,T['X'],T['target'][k])
        pts=[xy(x,y) for x,y in zip(xx,yy) if ymin<=y<=ymax]
        if len(pts)>1:
            line(pts,'#9ca9b5',2);text(left-27,pts[0][1]-8,k,14,'#637181')
    if zone=='Shinkansen':
        text(540,top+85,'大部分覆盖区使用屋架下悬吊支点，本图只标独立支柱。',18,'#647383')
    for m in AUDIT['masts']:
        if m['zone']!=zone:continue
        x,y=xy(m['x'],m['y']);color=LABELS[m['evidence']][1]
        svg.append(f'<g class="mast" data-id="{m["id"]}" tabindex="0" role="button" aria-label="查看 {m["id"]}">')
        draw.ellipse((x-5,y-5,x+5,y+5),fill=color,outline='white',width=1)
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="{color}" stroke="white" stroke-width="1.5"/>')
        text(x+7,y-13,m['id'],12,color)
        svg.append('</g>')
text(45,1370,'六项模型检查通过：柱体净距、设施干涉、屋面穿孔、设备间干涉及柱脚连接均已记录。',20)
text(45,1407,'147 根有底部承托面；28 根中央线边柱通过现有侧挂支架接入高架。所有杆位均未获得实测坐标认证。',18,'#5e6b7a')
text(45,1442,'编号与 CSV 一致。轨道/站台轮廓源自项目既有 GSI 配准数据；此图不是实景测绘图，未转载照片。',17,'#5e6b7a')
svg.append('</svg>');graphic='\n'.join(svg)
im.save(OUT/'plan.png');(OUT/'plan.svg').write_text(graphic,encoding='utf8')
payload=json.dumps(AUDIT['masts'],ensure_ascii=False).replace('<','\\u003c')
names=json.dumps({k:v[0] for k,v in LABELS.items()},ensure_ascii=False)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>东京站接触网杆位检查</title><style>
body{margin:0;background:#eef2f6;color:#253449;font:16px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1440px;margin:auto;padding:24px}h1{font-size:28px;margin:0 0 8px}.notice{background:#fff3df;border-left:4px solid #b26b00;padding:14px 18px}.tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}input{font:inherit;padding:8px 10px;border:1px solid #aab8c5;border-radius:6px;width:130px}button{font:inherit;background:#294f6d;color:white;border:0;border-radius:6px;padding:9px 14px;cursor:pointer}.detail{background:white;border:1px solid #d5dfe8;border-radius:8px;padding:14px;min-height:92px;position:sticky;top:0;z-index:2;box-shadow:0 3px 15px #294f6d14}#diagram{overflow:auto;background:white;margin-top:16px}svg{width:100%;min-width:950px;font-family:system-ui,"Microsoft YaHei",sans-serif}.mast{cursor:pointer}.mast:hover circle,.mast:focus circle,.mast.selected circle{stroke:#111;stroke-width:3}a{color:#126b97}footer{padding:20px 0;font-size:14px}dl{display:grid;grid-template-columns:150px 1fr;margin:0;gap:3px 12px}dt{color:#68798a}dd{margin:0}
</style><main><h1>地上站台的接触网杆位：检查记录</h1>
<p class="notice"><b>站台中、北段仍未按实景逐根校准。</b>已检查 175 根独立支柱的模型关系，本轮没有移动杆位或保存新模型。点击图中的支柱，查看坐标和证据来源。</p>
<div class="tools"><label for="mast-id">支柱编号</label><input id="mast-id" value="M001" maxlength="4"><button id="find">定位</button><button id="zoom">放大图</button><span>左侧为北，上方为模型东侧；各分区比例不同。</span></div>
<div class="detail" id="detail" aria-live="polite"></div><div id="diagram">GRAPHIC</div>
<footer>影像参考：<a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a> · <a href="https://commons.wikimedia.org/wiki/File:Tokyo_Station_overhead_2020-10-25.jpg">pelican 2020-10-25</a> · <a href="https://www.jreast.co.jp/estation/stations/1039.html">JR 东日本东京站图</a>。航空影像有视差及遮挡，官方站图没有杆位坐标。上述来源不能证明图中每个点与实景一致。图中未转载照片。<br>V14 的 10 根照片估算柱只具有纵向估计；另外 2 根为末端适配，1 根为曲线约束增设。162 根仍为旧版生成坐标。所有点均未获得实测坐标认证。</footer></main>
<script>const masts=PAYLOAD,names=NAMES;const detail=document.getElementById('detail');function show(id){const m=masts.find(x=>x.id===id);if(!m){detail.textContent='没有此编号；请输入 M001 至 M175。';return}document.querySelectorAll('.mast').forEach(e=>e.classList.toggle('selected',e.dataset.id===id));document.getElementById('mast-id').value=id;detail.replaceChildren();const h=document.createElement('b');h.textContent=m.id+' · 最近同层轨道 '+m.nearest_track+' 番线';detail.append(h);const dl=document.createElement('dl');const pairs=[['模型坐标','X '+m.x.toFixed(3)+' m；Y '+m.y.toFixed(3)+' m；柱底 Z '+m.base_z.toFixed(3)+' m'],['柱面最小间距',m.shaft_face_clearance_m.toFixed(3)+' m（模型目标 '+m.model_clearance_target_m.toFixed(2)+' m）'],['柱脚连接',m.base_attachment==='existing_side_brackets_intersect_viaduct'?'现有侧挂支架与高架网格相交':'柱脚下方有模型承托面'],['杆位依据',names[m.evidence]+'；非实测坐标']];for(const [a,b]of pairs){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=a;dd.textContent=b;dl.append(dt,dd)}detail.append(dl)}document.querySelectorAll('.mast').forEach(e=>{e.addEventListener('click',()=>show(e.dataset.id));e.addEventListener('keydown',ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();show(e.dataset.id)}})});document.getElementById('find').onclick=()=>show(document.getElementById('mast-id').value.trim().toUpperCase());document.getElementById('mast-id').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('find').click()});document.getElementById('zoom').onclick=()=>{const s=document.querySelector('svg');s.style.width=s.style.width==='1900px'?'100%':'1900px'};show('M001');</script></html>'''
page=page.replace('GRAPHIC',graphic).replace('PAYLOAD',payload).replace('NAMES',names)
(OUT/'index.html').write_text(page,encoding='utf8')
print('Created',OUT,'with',len(AUDIT['masts']),'clickable mast IDs')
