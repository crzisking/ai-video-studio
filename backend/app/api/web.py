# -*- coding: utf-8 -*-
"""后端直出前端（零构建、无 Node）。单页应用，原生 JS，打同源 API。"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home():
    return HTML


HTML = r"""
<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 短视频生成平台</title>
<style>
  :root{--bg:#0f1216;--card:#1a1f27;--line:#2a323d;--fg:#e8ecf1;--mut:#8a95a3;--acc:#4f8cff;--ok:#37c871;--err:#ff5d5d;}
  *{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}
  a{color:var(--acc);text-decoration:none;cursor:pointer;}
  .wrap{max-width:920px;margin:0 auto;padding:28px 20px 60px;}
  h1{font-size:22px;margin:0 0 4px;} .sub{color:var(--mut);font-size:13px;margin-bottom:20px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:14px;}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:12px;} @media(max-width:600px){.row{grid-template-columns:1fr;}}
  label{display:block;margin-bottom:12px;} .lbl{font-size:13px;color:var(--mut);margin-bottom:6px;}
  input,textarea,select{width:100%;background:#10141a;border:1px solid var(--line);color:var(--fg);border-radius:9px;padding:10px 12px;font:inherit;}
  textarea{min-height:70px;resize:vertical;}
  .btn{background:var(--acc);color:#fff;border:0;border-radius:10px;padding:11px 18px;font-size:15px;font-weight:600;cursor:pointer;} .btn:disabled{opacity:.5;cursor:not-allowed;} .btn.sec{background:#2a323d;}
  .pill{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut);margin-right:6px;}
  .pill.on{border-color:var(--acc);color:var(--acc);}
  .ok{color:var(--ok);} .err{color:var(--err);white-space:pre-wrap;} .muted{color:var(--mut);font-size:12px;}
  .proj{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border:1px solid var(--line);border-radius:10px;margin-bottom:10px;}
  .spin{display:inline-block;width:13px;height:13px;border:2px solid var(--mut);border-top-color:var(--acc);border-radius:50%;animation:s .8s linear infinite;vertical-align:-1px;margin-right:6px;}@keyframes s{to{transform:rotate(360deg);}}
  img.preview,video.preview{max-width:320px;border-radius:10px;margin-top:8px;display:block;}
</style></head><body><div class="wrap" id="app"></div>
<script>
const $=s=>document.querySelector(s);
async function req(path,opts={}){
  const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts});
  const t=await r.text(); let j=null; try{j=t?JSON.parse(t):null;}catch{throw new Error('HTTP '+r.status+': '+t.slice(0,200));}
  if(!r.ok) throw new Error((j&&(j.detail||j.error))||('HTTP '+r.status)); return j;
}
const API={
  health:()=>req('/health'), providers:()=>req('/providers'),
  list:()=>req('/projects'), create:b=>req('/projects',{method:'POST',body:JSON.stringify(b)}),
  get:id=>req('/projects/'+id), del:id=>req('/projects/'+id,{method:'DELETE'}),
  testImage:b=>req('/providers/test-image',{method:'POST',body:JSON.stringify(b)}),
  testVideo:b=>req('/providers/test-video',{method:'POST',body:JSON.stringify(b)}),
  job:id=>req('/jobs/'+id),
  genSb:(id,b)=>req('/projects/'+id+'/storyboard:generate',{method:'POST',body:JSON.stringify(b)}),
  getShots:id=>req('/projects/'+id+'/shots'),
  saveShots:(id,b)=>req('/projects/'+id+'/shots',{method:'PUT',body:JSON.stringify(b)}),
  listAssets:id=>req('/projects/'+id+'/assets'),
  delAsset:(id,aid)=>req('/projects/'+id+'/assets/'+aid,{method:'DELETE'}),
  genImages:(id,b)=>req('/projects/'+id+'/images:generate',{method:'POST',body:JSON.stringify(b)}),
  regenImage:(id,sid,b)=>req('/projects/'+id+'/shots/'+sid+'/regen-image',{method:'POST',body:JSON.stringify(b)}),
  genAudio:(id,b)=>req('/projects/'+id+'/audio:generate',{method:'POST',body:JSON.stringify(b)}),
  genVideo:(id,b)=>req('/projects/'+id+'/video:generate',{method:'POST',body:JSON.stringify(b)}),
  render:id=>req('/projects/'+id+'/render',{method:'POST',body:'{}'}),
  listPersonas:id=>req('/projects/'+id+'/personas'),
  delPersona:(id,pid)=>req('/projects/'+id+'/personas/'+pid,{method:'DELETE'}),
  listCast:id=>req('/projects/'+id+'/cast'),
  delCast:(id,mid)=>req('/projects/'+id+'/cast/'+mid,{method:'DELETE'}),
};
async function uploadCast(pid, name, mediaFile, voiceFile){
  const fd=new FormData(); fd.append('name',name||''); fd.append('media',mediaFile);
  if(voiceFile) fd.append('voice',voiceFile);
  const r=await fetch('/projects/'+pid+'/cast',{method:'POST',body:fd});
  const t=await r.text(); let j=null; try{j=JSON.parse(t);}catch{throw new Error('HTTP '+r.status);}
  if(!r.ok) throw new Error((j&&j.detail)||('HTTP '+r.status)); return j;
}
let CAST=[];
async function createPersona(pid, name, voice, file){
  const fd=new FormData(); fd.append('name',name); fd.append('voice',voice); fd.append('portrait',file);
  const r=await fetch('/projects/'+pid+'/personas',{method:'POST',body:fd});
  const t=await r.text(); let j=null; try{j=JSON.parse(t);}catch{throw new Error('HTTP '+r.status);}
  if(!r.ok) throw new Error((j&&j.detail)||('HTTP '+r.status)); return j;
}
const VOICES=[['longxiaochun_v2','知性积极女'],['longxiaoxia_v2','沉稳权威女'],['loongbella_v2','精准干练女'],['longcheng_v2','智慧青年男'],['longshu_v2','沉稳青年男'],['longxiaocheng_v2','磁性低音男']];
function voiceOpts(sel){ return VOICES.map(v=>'<option value="'+v[0]+'"'+(v[0]===sel?' selected':'')+'>'+v[1]+'</option>').join(''); }
let PERSONAS=[];
// 上传参考素材（multipart）
async function uploadAssets(pid, files){
  const fd=new FormData(); [...files].forEach(f=>fd.append('files',f));
  const r=await fetch('/projects/'+pid+'/assets',{method:'POST',body:fd});
  const t=await r.text(); let j=null; try{j=JSON.parse(t);}catch{throw new Error('HTTP '+r.status);}
  if(!r.ok) throw new Error((j&&j.detail)||('HTTP '+r.status)); return j;
}
// 轮询 job
async function pollJob(jid, onTick){
  for(let i=0;i<240;i++){ const j=await API.job(jid); if(onTick)onTick(j);
    if(j.status==='succeeded'||j.status==='failed') return j;
    await new Promise(r=>setTimeout(r,3000)); }
}
// 读当前阶段 creds（用 localStorage，stage①填过）
function curCreds(){ const isAli=P.provider==='aliyun';
  return {api_key:localStorage.getItem(P.provider+'_key')||'', workspace_id:isAli?(localStorage.getItem('aliyun_ws')||''):''}; }
function needKey(){ if(!curCreds().api_key){ alert('请先在「①需求&素材」填写 API Key（会本机记住）'); return true; } return false; }
// 凭据：读/存 localStorage
function loadCreds(prov){ return {api_key:localStorage.getItem(prov+'_key')||'', workspace_id:localStorage.getItem('aliyun_ws')||''}; }
function saveCreds(prov,ak,ws){ localStorage.setItem(prov+'_key',ak||''); if(ws!=null)localStorage.setItem('aliyun_ws',ws||''); }
function esc(s){return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// 简易路由：#/ 列表  #/p/<id> 详情
window.addEventListener('hashchange',route); window.addEventListener('load',route);
function route(){ const h=location.hash; if(h.startsWith('#/p/')) viewProject(+h.slice(4)); else viewList(); }

async function viewList(){
  let online='检测中...'; try{await API.health(); online='<span class="ok">已连接</span>';}catch{online='<span class="err">后端未连接</span>';}
  $('#app').innerHTML=`
    <h1>AI 短视频生成平台 <span class="muted">· 短剧 / 企业宣传片</span></h1>
    <div class="sub">后端：${online}</div>
    <div class="card">
      <div class="lbl">新建项目</div>
      <div class="row">
        <label><div class="lbl">项目名</div><input id="nm" placeholder="如：XX公司宣传片"></label>
        <label><div class="lbl">产品线</div><select id="tp"><option value="promo">企业宣传</option><option value="drama">短剧</option></select></label>
      </div>
      <div class="row">
        <label><div class="lbl">AI 厂商</div><select id="pv"><option value="aliyun">阿里百炼（wan2.7）</option><option value="volcano">火山方舟（Seedance）</option></select></label>
        <label><div class="lbl">视频引擎</div><select id="eng"><option value="r2v">参考生视频 r2v（多主体一致·推荐）</option><option value="i2v">首尾帧 i2v</option></select></label>
      </div>
      <label><div class="lbl">需求简述</div><input id="bf"></label>
      <button class="btn" id="mk">创建项目</button>
    </div>
    <div class="card"><div class="lbl">项目列表</div><div id="plist" class="muted">加载中...</div></div>`;
  $('#mk').onclick=async()=>{ const nm=$('#nm').value.trim(); if(!nm)return alert('请填项目名');
    try{ await API.create({name:nm,type:$('#tp').value,provider:$('#pv').value,video_engine:$('#eng').value,brief:$('#bf').value}); loadList(); $('#nm').value='';$('#bf').value=''; }catch(e){alert(e.message);} };
  loadList();
}
async function loadList(){
  try{ const ps=await API.list();
    $('#plist').innerHTML = ps.length? ps.map(p=>`<div class="proj">
      <div><a href="#/p/${p.id}"><b>${esc(p.name)}</b></a>
      <span class="pill">${p.type==='drama'?'短剧':'企业宣传'}</span><span class="pill">${p.provider}</span><span class="pill">${p.status}</span></div>
      <button class="btn sec" onclick="delProj(${p.id})">删除</button></div>`).join('') : '<div class="muted">还没有项目</div>';
  }catch(e){ $('#plist').innerHTML='<span class="err">'+e.message+'</span>'; }
}
async function delProj(id){ if(!confirm('删除此项目？'))return; await API.del(id); loadList(); }

const STAGES=[['req','①需求&素材'],['script','②剧本&分镜'],['image','③分镜图'],['audio','④配音'],['video','⑤视频'],['post','⑥后期合成']];
const STATUS2STAGE={created:'req',scripting:'script',imaging:'image',audio:'audio',rendering:'video',done:'post'};
let P=null, curStage='req';

async function viewProject(id){
  try{P=await API.get(id);}catch(e){$('#app').innerHTML='<div class="sub"><a href="#/">← 返回</a></div><div class="card err">'+e.message+'</div>';return;}
  curStage=STATUS2STAGE[P.status]||'req';
  $('#app').innerHTML=`
    <div class="sub"><a href="#/">← 返回项目列表</a></div>
    <h1>${esc(P.name)} <span class="pill">${P.type==='drama'?'短剧':'企业宣传'}</span><span class="pill">${P.provider}</span></h1>
    <div class="card" id="pills"></div>
    <div id="stage"></div>`;
  renderPills(); setStage(curStage);
}
function renderPills(){
  $('#pills').innerHTML=STAGES.map(([k,l])=>`<span class="pill ${k===curStage?'on':''}" onclick="setStage('${k}')" style="cursor:pointer">${l}</span>`).join('');
}
function setStage(k){ curStage=k; renderPills();
  if(k==='req') stageReq(); else if(k==='script') stageScript();
  else if(k==='image') stageImage(); else if(k==='audio') stageAudio();
  else if(k==='video') stageVideo(); else if(k==='post') stagePost();
}
async function renderRefList(){
  let assets=[]; try{assets=await API.listAssets(P.id);}catch{}
  const box=$('#refs'); if(!box)return;
  box.innerHTML=assets.map(a=>`<div style="position:relative;width:74px;height:74px">
    <img src="/uploads/${a.path.split(/[\\\\/]/).pop()}" onerror="this.style.opacity=.3" style="width:74px;height:74px;object-fit:cover;border-radius:8px;border:1px solid var(--line)">
    <span onclick="rmRef(${a.id})" style="position:absolute;top:-7px;right:-7px;width:18px;height:18px;border-radius:50%;background:var(--err);color:#fff;font-size:13px;line-height:18px;text-align:center;cursor:pointer">×</span>
  </div>`).join('') || '<span class="muted">暂无参考素材</span>';
}
async function rmRef(aid){ await API.delAsset(P.id, aid); renderRefList(); }

// i2v：参考素材（出图用）
function renderRefPanel(){
  $('#srcbox').innerHTML=`<div class="lbl">参考素材（角色/场景/风格，图片或视频；出图会参考）</div>
    <button class="btn sec" id="addref" style="padding:8px 14px;font-size:14px">+ 添加参考图/视频</button>
    <input type="file" id="reffiles" accept="image/*,video/*" multiple style="display:none">
    <div id="refs" style="display:flex;gap:10px;flex-wrap:wrap;margin:10px 0"></div>`;
  renderRefList();
  $('#addref').onclick=()=>$('#reffiles').click();
  $('#reffiles').onchange=async e=>{ const fs=[...e.target.files]; e.target.value='';
    $('#genout').innerHTML='<span class="spin"></span>上传参考素材...';
    try{ await uploadAssets(P.id, fs); $('#genout').textContent=''; renderRefList(); }
    catch(err){ $('#genout').innerHTML='<span class="err">'+err.message+'</span>'; } };
}

// r2v：参考主体库（图/视频 + 音色，≤5）
async function renderCastPanel(){
  try{CAST=await API.listCast(P.id);}catch{CAST=[];}
  $('#srcbox').innerHTML=`<div class="lbl">参考主体库（最多5个；图片/视频主体，每个可挂音色音频。导演会用「图1/视频1」指代）</div>
    <div id="castlist" style="display:flex;gap:12px;flex-wrap:wrap;margin:8px 0"></div>
    <div class="row">
      <label style="margin:0"><div class="lbl">主体名(可选)</div><input id="cname" placeholder="如：女主角/产品/场景"></label>
      <label style="margin:0"><div class="lbl">主体素材(图/视频)</div><input type="file" id="cmedia" accept="image/*,video/*"></label>
    </div>
    <label><div class="lbl">音色音频(可选, mp3/wav, 1-10s)</div><input type="file" id="cvoice" accept=".mp3,.wav,audio/*"></label>
    <button class="btn sec" id="caddbtn">+ 添加主体</button>
    <div id="cmsg" class="muted" style="margin-top:6px"></div>`;
  drawCast();
  $('#caddbtn').onclick=async()=>{ const f=$('#cmedia').files[0]; if(!f)return alert('选一个图片或视频');
    $('#cmsg').innerHTML='<span class="spin"></span>上传中...';
    try{ await uploadCast(P.id,$('#cname').value.trim(),f,$('#cvoice').files[0]||null);
      CAST=await API.listCast(P.id); $('#cname').value='';$('#cmedia').value='';$('#cvoice').value=''; $('#cmsg').textContent=''; drawCast();
    }catch(e){ $('#cmsg').innerHTML='<span class="err">'+e.message+'</span>'; } };
}
function drawCast(){
  const box=$('#castlist'); if(!box)return;
  box.innerHTML=CAST.map(m=>`<div style="text-align:center;width:96px">
    ${m.media_kind==='video'?`<video src="${m.media_url}" style="width:90px;height:90px;object-fit:cover;border-radius:10px;border:1px solid var(--line)"></video>`:`<img src="${m.media_url}" style="width:90px;height:90px;object-fit:cover;border-radius:10px;border:1px solid var(--line)">`}
    <div style="font-size:12px"><b>${m.label}</b> ${esc(m.name||'')}</div>
    <div style="font-size:11px" class="muted">${m.voice_url?'🔊有音色':'无音色'}</div>
    <a style="font-size:12px" onclick="rmCast(${m.id})">删除</a></div>`).join('')||'<span class="muted">还没有参考主体，先加一个</span>';
}
async function rmCast(id){ if(!confirm('删除此主体？'))return; await API.delCast(P.id,id); CAST=await API.listCast(P.id); drawCast(); }

// ① 需求 & 素材 → 生成分镜
function stageReq(){
  const isAli=P.provider==='aliyun'; const cr=loadCreds(P.provider);
  $('#stage').innerHTML=`<div class="card">
    <div class="lbl">① 需求 & 素材 — 填写需求，生成分镜脚本</div>
    <div class="row">
      <label><div class="lbl">API Key（${P.provider}）</div><input type="password" id="ak" value="${esc(cr.api_key)}" placeholder="${isAli?'sk-xxx':'Ark Key'}"></label>
      ${isAli?`<label><div class="lbl">WorkspaceId</div><input id="ws" value="${esc(cr.workspace_id)}" placeholder="业务空间ID"></label>`:''}
    </div>
    <label><div class="lbl">需求描述</div><textarea id="bf" style="min-height:90px">${esc(P.brief)}</textarea></label>
    <div class="row">
      <label><div class="lbl">镜头数</div><input type="number" id="ns" value="5" min="1" max="20"></label>
      <label><div class="lbl">默认每镜时长(秒)</div><input type="number" id="du" value="5" min="2" max="12"></label>
    </div>
    <label><div class="lbl">宽高比</div><select id="rt"><option>16:9</option><option>9:16</option><option>1:1</option></select></label>
    <div id="srcbox"></div>
    <button class="btn" id="gen" style="margin-top:8px">生成分镜</button>
    <div id="genout" class="muted" style="margin-top:12px"></div>
  </div>`;
  if((P.video_engine||'r2v')==='r2v') renderCastPanel(); else renderRefPanel();
  $('#gen').onclick=async()=>{
    const ak=$('#ak').value.trim(); if(!ak)return alert('请填 API Key');
    const ws=isAli?$('#ws').value.trim():''; saveCreds(P.provider,ak,ws);
    const body={creds:{api_key:ak,workspace_id:ws},brief:$('#bf').value.trim(),
      num_shots:+$('#ns').value,duration:+$('#du').value,ratio:$('#rt').value};
    $('#gen').disabled=true; $('#genout').innerHTML='<span class="spin"></span>导演拆分镜中...';
    try{ const r=await API.genSb(P.id,body);
      for(let i=0;i<120;i++){ const j=await API.job(r.job_id);
        if(j.status==='succeeded'){ $('#genout').innerHTML='<span class="ok">完成：'+esc(j.result.title)+'（'+j.result.count+'镜）</span>'; P=await API.get(P.id); setStage('script'); return; }
        if(j.status==='failed'){ $('#genout').innerHTML='<span class="err">失败：'+esc(j.error)+'</span>'; break; }
        await new Promise(x=>setTimeout(x,2500)); }
    }catch(e){ $('#genout').innerHTML='<span class="err">'+e.message+'</span>'; }
    $('#gen').disabled=false;
  };
}

// ② 剧本 & 分镜 — 可编辑分镜表
async function stageScript(){
  $('#stage').innerHTML='<div class="card muted">加载分镜...</div>';
  let data; try{data=await API.getShots(P.id);}catch(e){$('#stage').innerHTML='<div class="card err">'+e.message+'</div>';return;}
  try{PERSONAS=await API.listPersonas(P.id);}catch{PERSONAS=[];}
  const shots=data.shots;
  const r2v=(P.video_engine||'r2v')==='r2v';
  const pc=r2v?'':personaCard();
  if(!shots.length){ $('#stage').innerHTML=pc+'<div class="card muted">还没有分镜。点上方「①需求&素材」去生成。</div>'; if(!r2v)bindPersona(); return; }
  $('#stage').innerHTML=pc+`<div class="card">
    <div class="lbl">② 剧本 & 分镜 — 共 ${shots.length} 镜，可逐条编辑（风格：${esc(data.project.style||'')}）。每镜可选「普通/数字人」。</div>
    <div id="shots"></div>
    <div style="display:flex;gap:10px;margin-top:8px">
      <button class="btn sec" id="add">+ 加一镜</button>
      <button class="btn sec" id="regen">↻ 重新生成</button>
      <button class="btn" id="save">保存分镜</button>
    </div>
    <div id="sv" class="muted" style="margin-top:10px"></div>
  </div>`;
  if(!r2v) bindPersona();
  renderShots(shots);
  $('#add').onclick=()=>{ const arr=collect(); arr.push({scene:'',first_frame_prompt:'',last_frame_prompt:'',motion_prompt:'',dialogue:'',duration:5,kind:'i2v',persona_id:null}); renderShots(arr); };
  $('#regen').onclick=()=>setStage('req');
  $('#save').onclick=async()=>{
    const arr=collect().map((s,i)=>({...s,idx:i+1}));
    $('#save').disabled=true; $('#sv').textContent='保存中...';
    try{ await API.saveShots(P.id,{shots:arr,style:data.project.style}); $('#sv').innerHTML='<span class="ok">已保存</span>'; }
    catch(e){ $('#sv').innerHTML='<span class="err">'+e.message+'</span>'; }
    $('#save').disabled=false;
  };
}
function personaSelect(sel){
  return '<option value="">—选择形象—</option>'+PERSONAS.map(p=>'<option value="'+p.id+'"'+(p.id==sel?' selected':'')+'>'+esc(p.name)+'</option>').join('');
}
function renderShots(shots){
  const r2v=(P.video_engine||'r2v')==='r2v';
  $('#shots').innerHTML=shots.map((s,i)=>{
    if(r2v){
      return `<div class="shotcard" data-i="${i}" style="border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between"><b>第 ${i+1} 段</b><a onclick="rmShot(${i})">删除</a></div>
        <div class="lbl" style="margin-top:6px">场景说明</div><input class="f-scene" value="${esc(s.scene)}">
        <div class="lbl">镜头提示词（用「图1/视频1」指代主体，含动作与对白，直接喂给模型）</div><textarea class="f-mp" style="min-height:70px">${esc(s.motion_prompt)}</textarea>
        <div class="lbl">对白文本（展示用，可留空）</div><textarea class="f-dlg">${esc(s.dialogue)}</textarea>
        <div class="lbl">时长(秒)</div><input type="number" class="f-du" value="${s.duration||5}" min="2" max="15" style="width:100px">
      </div>`;
    }
    const isAv=s.kind==='avatar';
    return `<div class="shotcard" data-i="${i}" style="border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:10px">
    <div style="display:flex;justify-content:space-between"><b>第 ${i+1} 镜</b><a onclick="rmShot(${i})">删除</a></div>
    <div class="lbl" style="margin-top:6px">场景说明</div><input class="f-scene" value="${esc(s.scene)}">
    <div class="row" style="margin-top:8px">
      <label style="margin:0"><div class="lbl">生成方式</div>
        <select class="f-kind" onchange="onKind(${i},this.value)"><option value="i2v"${!isAv?' selected':''}>普通(首尾帧)</option><option value="avatar"${isAv?' selected':''}>数字人</option></select></label>
      <label style="margin:0"><div class="lbl">数字人形象${PERSONAS.length?'':'（先在上方建形象）'}</div>
        <select class="f-persona" ${isAv?'':'disabled'}>${personaSelect(s.persona_id)}</select></label>
    </div>
    <div class="i2v-fields" style="${isAv?'display:none':''}">
      <div class="lbl">首帧出图提示词</div><textarea class="f-ffp">${esc(s.first_frame_prompt)}</textarea>
      <div class="lbl">尾帧出图提示词</div><textarea class="f-lfp">${esc(s.last_frame_prompt)}</textarea>
      <div class="lbl">运镜/动作</div><textarea class="f-mp">${esc(s.motion_prompt)}</textarea>
    </div>
    <div class="lbl">台词/旁白${isAv?'（数字人将朗读这段）':''}</div><textarea class="f-dlg">${esc(s.dialogue)}</textarea>
    <div class="lbl">时长(秒)</div><input type="number" class="f-du" value="${s.duration||5}" min="2" max="12" style="width:100px">
  </div>`;}).join('');
}
function onKind(i,val){ const arr=collect(); arr[i].kind=val; renderShots(arr); }
function collect(){
  return [...document.querySelectorAll('.shotcard')].map(el=>({
    scene:el.querySelector('.f-scene').value,
    first_frame_prompt:el.querySelector('.f-ffp')?el.querySelector('.f-ffp').value:'',
    last_frame_prompt:el.querySelector('.f-lfp')?el.querySelector('.f-lfp').value:'',
    motion_prompt:el.querySelector('.f-mp')?el.querySelector('.f-mp').value:'',
    dialogue:el.querySelector('.f-dlg').value, duration:+el.querySelector('.f-du').value||5,
    kind:el.querySelector('.f-kind')?el.querySelector('.f-kind').value:'i2v',
    persona_id:(el.querySelector('.f-persona')&&el.querySelector('.f-persona').value)?+el.querySelector('.f-persona').value:null }));
}
function rmShot(i){ const arr=collect(); arr.splice(i,1); renderShots(arr); }

// 数字人形象库
function personaCard(){
  return `<div class="card">
    <div class="lbl">数字人形象库（肖像 + 音色，可在分镜里选用）</div>
    <div id="plist" style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px"></div>
    <div class="row">
      <label style="margin:0"><div class="lbl">形象名</div><input id="pname" placeholder="如：主持人A"></label>
      <label style="margin:0"><div class="lbl">音色</div><select id="pvoice">${voiceOpts('longxiaochun_v2')}</select></label>
    </div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:8px">
      <input type="file" id="pfile" accept="image/*"><button class="btn sec" id="paddbtn">+ 新建形象</button>
    </div>
    <div id="pmsg" class="muted" style="margin-top:6px"></div></div>`;
}
function bindPersona(){
  drawPersonas();
  const btn=$('#paddbtn'); if(!btn)return;
  btn.onclick=async()=>{ const n=$('#pname').value.trim(); const f=$('#pfile').files[0];
    if(!n)return alert('填形象名'); if(!f)return alert('选肖像图');
    $('#pmsg').innerHTML='<span class="spin"></span>创建中...';
    try{ await createPersona(P.id,n,$('#pvoice').value,f); PERSONAS=await API.listPersonas(P.id);
      $('#pname').value=''; $('#pfile').value=''; $('#pmsg').textContent=''; drawPersonas();
      // 刷新分镜里的形象下拉
      const cur=collect(); if(cur.length) renderShots(cur);
    }catch(e){ $('#pmsg').innerHTML='<span class="err">'+e.message+'</span>'; } };
}
function drawPersonas(){
  const box=$('#plist'); if(!box)return;
  box.innerHTML=PERSONAS.map(p=>`<div style="text-align:center;width:90px">
    <img src="${p.portrait_url}" style="width:80px;height:80px;object-fit:cover;border-radius:10px;border:1px solid var(--line)">
    <div style="font-size:12px">${esc(p.name)}</div>
    <a style="font-size:12px" onclick="rmPersona(${p.id})">删除</a></div>`).join('')||'<span class="muted">暂无形象</span>';
}
async function rmPersona(id){ if(!confirm('删除此形象？'))return; await API.delPersona(P.id,id); PERSONAS=await API.listPersonas(P.id); drawPersonas(); const cur=collect&&document.querySelector('.shotcard')?collect():null; if(cur)renderShots(cur); }

// ③ 分镜图
async function stageImage(){
  if((P.video_engine||'r2v')==='r2v'){ $('#stage').innerHTML='<div class="card muted">当前是「参考生视频 r2v」引擎，<b>无需出分镜图</b>——参考主体在「①」的主体库里。请直接到「⑤视频」生成。</div>'; return; }
  $('#stage').innerHTML='<div class="card muted">加载...</div>';
  const data=await API.getShots(P.id); const shots=data.shots;
  if(!shots.length){ $('#stage').innerHTML='<div class="card muted">请先在「②剧本&分镜」生成分镜。</div>'; return; }
  $('#stage').innerHTML=`<div class="card">
    <div class="lbl">③ 分镜图 — 逐镜出首帧+尾帧（参考素材会带入；相邻镜首尾衔接）</div>
    <label><div class="lbl">宽高比</div><select id="rt"><option>16:9</option><option>9:16</option><option>1:1</option></select></label>
    <div style="display:flex;gap:10px"><button class="btn" id="genimg">生成所有分镜图</button></div>
    <div id="imgout" class="muted" style="margin-top:10px"></div>
    <div id="grid" style="margin-top:12px"></div></div>`;
  drawImgGrid(shots);
  $('#genimg').onclick=async()=>{ if(needKey())return;
    $('#genimg').disabled=true; $('#imgout').innerHTML='<span class="spin"></span>出图中（每镜首+尾，约各十几秒）...';
    try{ const r=await API.genImages(P.id,{creds:curCreds(),ratio:$('#rt').value});
      const tick=async()=>{ const d=await API.getShots(P.id); drawImgGrid(d.shots); };
      const iv=setInterval(tick,3000);
      const j=await pollJob(r.job_id); clearInterval(iv); await tick();
      $('#imgout').innerHTML=j.status==='succeeded'?'<span class="ok">完成</span>':'<span class="err">'+esc(j.error)+'</span>';
    }catch(e){ $('#imgout').innerHTML='<span class="err">'+e.message+'</span>'; } $('#genimg').disabled=false; };
}
function drawImgGrid(shots){
  $('#grid').innerHTML=shots.map(s=>`<div style="border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:10px">
    <div style="display:flex;justify-content:space-between"><b>第${s.idx}镜</b><a onclick="regen(${s.id})">重出此镜</a></div>
    <div class="muted" style="font-size:12px;margin:4px 0">${esc(s.scene)}</div>
    <div style="display:flex;gap:8px">
      ${s.first_url?`<figure style="flex:1;margin:0"><img src="${s.first_url}" style="width:100%;border-radius:8px"><figcaption class="muted" style="font-size:11px;text-align:center">首帧</figcaption></figure>`:'<div class="muted">首帧未生成</div>'}
      ${s.last_url?`<figure style="flex:1;margin:0"><img src="${s.last_url}" style="width:100%;border-radius:8px"><figcaption class="muted" style="font-size:11px;text-align:center">尾帧</figcaption></figure>`:''}
    </div></div>`).join('');
}
async function regen(sid){ if(needKey())return;
  $('#imgout').innerHTML='<span class="spin"></span>重出第'+sid+'镜...';
  try{ const r=await API.regenImage(P.id,sid,{creds:curCreds(),ratio:($('#rt')?$('#rt').value:'16:9'),which:'both'});
    await pollJob(r.job_id); const d=await API.getShots(P.id); drawImgGrid(d.shots); $('#imgout').textContent='';
  }catch(e){ $('#imgout').innerHTML='<span class="err">'+e.message+'</span>'; } }

// ④ 配音
async function stageAudio(){
  const data=await API.getShots(P.id); const shots=data.shots;
  const isAli=P.provider==='aliyun';
  $('#stage').innerHTML=`<div class="card">
    <div class="lbl">④ 配音 — 给有台词的分镜合成语音（同一音色跨镜一致）</div>
    ${isAli?`<label><div class="lbl">音色</div><select id="vo">
      <option value="longxiaochun_v2">知性积极女</option><option value="longxiaoxia_v2">沉稳权威女</option>
      <option value="loongbella_v2">精准干练女</option><option value="longcheng_v2">智慧青年男</option>
      <option value="longshu_v2">沉稳青年男</option><option value="longxiaocheng_v2">磁性低音男</option></select></label>
      <button class="btn" id="gena">生成配音</button>`
    :`<div class="muted">火山线无独立TTS；声音在「⑤视频」由 Seedance 原生生成。</div>`}
    <div id="aout" class="muted" style="margin-top:10px"></div><div id="agrid" style="margin-top:10px"></div></div>`;
  drawAudio(shots);
  if(isAli) $('#gena').onclick=async()=>{ if(needKey())return;
    $('#gena').disabled=true; $('#aout').innerHTML='<span class="spin"></span>配音中...';
    try{ const r=await API.genAudio(P.id,{creds:curCreds(),voice:$('#vo').value});
      const j=await pollJob(r.job_id); const d=await API.getShots(P.id); drawAudio(d.shots);
      $('#aout').innerHTML=j.status==='succeeded'?'<span class="ok">完成</span>':'<span class="err">'+esc(j.error)+'</span>';
    }catch(e){ $('#aout').innerHTML='<span class="err">'+e.message+'</span>'; } $('#gena').disabled=false; };
}
function drawAudio(shots){
  $('#agrid').innerHTML=shots.filter(s=>(s.dialogue||'').trim()).map(s=>`<div style="border:1px solid var(--line);border-radius:8px;padding:10px;margin-bottom:8px">
    <b>第${s.idx}镜</b> <span class="muted">${esc(s.dialogue)}</span>
    ${s.audio_url?`<audio controls src="${s.audio_url}" style="width:100%;margin-top:6px"></audio>`:'<div class="muted">未配音</div>'}</div>`).join('')||'<span class="muted">没有带台词的分镜</span>';
}

// ⑤ 视频
async function stageVideo(){
  const data=await API.getShots(P.id); const shots=data.shots;
  const r2v=(P.video_engine||'r2v')==='r2v';
  let cast=[]; if(r2v){ try{cast=await API.listCast(P.id);}catch{} }
  $('#stage').innerHTML=`<div class="card">
    <div class="lbl">⑤ 视频 — ${r2v?'逐段由参考主体(图1/视频1)生成，角色/音色一致':'逐镜由首尾帧生成（阿里：有配音则音画同步；火山：原生配音）'}</div>
    ${r2v?`<div class="muted" style="margin-bottom:8px">参考主体：${cast.length?cast.map(m=>m.label+(m.name?('='+esc(m.name)):'')).join('、'):'<span class="err">无，请先回①主体库上传</span>'}</div>`:''}
    <div class="row">
      <label><div class="lbl">宽高比</div><select id="rt"><option>16:9</option><option>9:16</option><option>1:1</option></select></label>
      <label><div class="lbl">分辨率</div><select id="re"><option>720P</option><option>1080P</option></select></label>
    </div>
    <button class="btn" id="genv">生成所有分镜视频</button>
    <div id="vout" class="muted" style="margin-top:10px"></div><div id="vgrid" style="margin-top:12px"></div></div>`;
  drawVideo(shots);
  $('#genv').onclick=async()=>{ if(needKey())return;
    if(r2v){ if(!cast.length){ alert('请先在「①需求&素材」的参考主体库上传至少1个主体'); return; } }
    else if(!shots.some(s=>s.first_url)){ alert('请先在③生成分镜图'); return; }
    $('#genv').disabled=true; $('#vout').innerHTML='<span class="spin"></span>生成视频中（每段1-5分钟，请耐心）...';
    try{ const r=await API.genVideo(P.id,{creds:curCreds(),ratio:$('#rt').value,resolution:$('#re').value});
      const iv=setInterval(async()=>{const d=await API.getShots(P.id);drawVideo(d.shots);},5000);
      const j=await pollJob(r.job_id); clearInterval(iv); const d=await API.getShots(P.id); drawVideo(d.shots);
      $('#vout').innerHTML=j.status==='succeeded'?'<span class="ok">完成</span>':'<span class="err">'+esc(j.error)+'</span>';
    }catch(e){ $('#vout').innerHTML='<span class="err">'+e.message+'</span>'; } $('#genv').disabled=false; };
}
function drawVideo(shots){
  $('#vgrid').innerHTML=shots.map(s=>`<div style="border:1px solid var(--line);border-radius:8px;padding:10px;margin-bottom:8px">
    <b>第${s.idx}镜</b>
    ${s.video_url?`<video controls src="${s.video_url}" style="width:100%;max-width:360px;border-radius:8px;display:block;margin-top:6px"></video>`:'<span class="muted"> 未生成</span>'}</div>`).join('');
}

// ⑥ 后期合成
async function stagePost(){
  const data=await API.getShots(P.id); const shots=data.shots;
  const ready=shots.filter(s=>s.video_url).length;
  $('#stage').innerHTML=`<div class="card">
    <div class="lbl">⑥ 后期合成 — 把分镜视频按顺序拼成成片（ffmpeg）</div>
    <div class="muted">已就绪分镜视频：${ready}/${shots.length}（需先在⑤生成）。需本机安装 ffmpeg。</div>
    <button class="btn" id="ren" style="margin-top:10px">合成成片</button>
    <div id="rout" style="margin-top:12px"></div></div>`;
  $('#ren').onclick=async()=>{
    $('#ren').disabled=true; $('#rout').innerHTML='<span class="spin"></span>合成中...';
    try{ const r=await API.render(P.id); const j=await pollJob(r.job_id);
      if(j.status==='succeeded'){ const u=j.result.final_url;
        $('#rout').innerHTML='<div class="ok">✅ 成片完成</div><video controls src="'+u+'" style="width:100%;max-width:480px;border-radius:10px;margin-top:8px;display:block"></video><div style="margin-top:8px"><a href="'+u+'" download>⬇ 下载成片</a></div>';
      } else $('#rout').innerHTML='<span class="err">'+esc(j.error)+'</span>';
    }catch(e){ $('#rout').innerHTML='<span class="err">'+e.message+'</span>'; } $('#ren').disabled=false; };
}
</script></body></html>
"""
