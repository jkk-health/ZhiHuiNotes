"""Generate editable drawio and StarUML models from the final delivery scope."""
from pathlib import Path
import json, uuid, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'diagrams';OUT.mkdir(parents=True,exist_ok=True)
def uid():return uuid.uuid4().hex
def ref(o):return {'$ref':o['_id'] if isinstance(o,dict) else o}
def obj(t,parent=None,**kw):return {'_type':t,'_id':uid(),**({'_parent':ref(parent)} if parent else {}),**kw}
class Draw:
 def __init__(self,name,w=1400,h=1000):
  self.file=ET.Element('mxfile',host='app.diagrams.net',version='24.7.17');d=ET.SubElement(self.file,'diagram',id=uid(),name=name)
  self.graph=ET.SubElement(d,'mxGraphModel',dx=str(w),dy=str(h),grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),math='0',shadow='0');self.root=ET.SubElement(self.graph,'root');ET.SubElement(self.root,'mxCell',id='0');ET.SubElement(self.root,'mxCell',id='1',parent='0')
 def box(self,text,x,y,w,h,style='rounded=1;whiteSpace=wrap;html=0;fillColor=#E9F4EF;strokeColor=#32785E;fontFamily=Microsoft YaHei;fontSize=15;'):
  i=uid();c=ET.SubElement(self.root,'mxCell',id=i,value=text,style=style,vertex='1',parent='1');ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'});return i
 def edge(self,a,b,label='',style='edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;fontFamily=Microsoft YaHei;fontSize=13;'):
  c=ET.SubElement(self.root,'mxCell',id=uid(),value=label,style=style,edge='1',parent='1',source=a,target=b);ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
 def save(self,n):ET.indent(self.file);ET.ElementTree(self.file).write(OUT/n,encoding='utf-8',xml_declaration=True)
fields={
 'User':['id: Integer [PK]','username: String(50) [unique]','pwd_hash: String(128)','salt: String(32)','created_at: DateTime'],
 'Notebook':['id: Integer [PK]','user_id: Integer [FK user.id]','name: String(100)','sort: Integer'],
 'Note':['id: Integer [PK]','user_id: Integer [FK user.id]','notebook_id: Integer? [FK notebook.id]','title: String(200)','content_html: Text','content_md: Text','is_top: Boolean','is_deleted: Boolean','is_public: Boolean [reserved]','created_at, updated_at: DateTime'],
 'Tag':['id: Integer [PK]','user_id: Integer [FK user.id]','name: String(50)','unique(user_id, name)'],
 'NoteTag':['note_id: Integer [PK, FK note.id]','tag_id: Integer [PK, FK tag.id]'],
 'Todo':['id: Integer [PK]','user_id: Integer [FK user.id]','note_id: Integer? [FK note.id]','title: String(200)','due_date: Date?','done: Boolean','created_at: DateTime'],
 'Mindmap':['id: Integer [PK]','user_id: Integer [FK user.id]','note_id: Integer? [FK note.id]','title: String(200)','map_json: Text [JSON]','updated_at: DateTime'],
 'Bill':['id: Integer [PK]','user_id: Integer [FK user.id]','type: String(2) [收/支]','category: String(50)','amount: Numeric(10,2)','bill_date: Date','remark: String(200)','created_at: DateTime']}
relations=[('User','Notebook','1 : N'),('User','Note','1 : N'),('User','Tag','1 : N'),('User','Todo','1 : N'),('User','Mindmap','1 : N'),('User','Bill','1 : N'),('Notebook','Note','0..1 : N'),('Note','NoteTag','1 : N'),('Tag','NoteTag','1 : N'),('Note','Todo','0..1 : N'),('Note','Mindmap','0..1 : N')]
d=Draw('用例图',1400,1000);actor=d.box('用户',80,440,100,140,'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=0;fontFamily=Microsoft YaHei;fontSize=18;');d.box('智汇笔记 Web 系统（所有业务需登录）',240,30,1080,900,'rounded=0;fillColor=none;strokeColor=#A8BBB1;verticalAlign=top;html=0;fontSize=20;')
uses=['注册 / 登录 / 退出','笔记编辑、搜索、分组与标签','置顶、回收站与恢复','待办增删改、完成与截止日期','笔记 ↔ 待办跳转','笔记生成导图、节点编辑与保存','AI 摘要预览与复制','AI 候选标签勾选采用','收支增删改与月度统计','离线访问与 AI 自动降级']
for i,s in enumerate(uses):
 a=d.box(s,300+(i%2)*470,110+(i//2)*150,400,85,'ellipse;whiteSpace=wrap;html=0;fillColor=#E9F4EF;strokeColor=#32785E;fontSize=17;fontFamily=Microsoft YaHei;');d.edge(actor,a,style='endArrow=none;html=0;strokeColor=#56796A;')
d.save('01-用例图.drawio')
d=Draw('核心八表 E-R 图',1600,1280);positions={'User':(600,30),'Notebook':(70,320),'Note':(600,320),'Tag':(1120,320),'NoteTag':(1120,680),'Todo':(70,810),'Mindmap':(600,810),'Bill':(1120,1020)};boxes={}
for n,fs in fields.items():
 x,y=positions[n];boxes[n]=d.box(n+'\n────────────\n'+'\n'.join(fs),x,y,360,80+len(fs)*24,'rounded=0;whiteSpace=wrap;html=0;align=left;verticalAlign=top;spacing=14;fillColor=#F5FAF7;strokeColor=#32785E;fontFamily=Microsoft YaHei;fontSize=14;')
for a,b,t in relations:d.edge(boxes[a],boxes[b],t,'edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=ERmany;startArrow=ERone;fontSize=13;')
d.save('02-核心八表ER图.drawio')
d=Draw('核心业务与 AI 降级流程',1400,1100)
texts=[('登录 / 刷新恢复会话',430,20,360,70),('编辑笔记（标题、正文、图片、标签）',430,130,360,80),('存在未保存修改？',450,270,320,100),('保存 / 放弃 / 取消',30,290,330,80),('保存并统一清理 HTML → 纯文本副本',430,420,360,80),('生成导图',30,570,310,70),('创建关联待办',430,570,360,70),('AI 摘要 / 标签（前 10000 字）',950,570,360,70),('API 可用且 8 秒内有效？',970,690,320,110),('本地句子抽取 / 词表标签',700,850,300,80),('返回 API 结果',1080,850,260,80),('预览 → 复制摘要 / 合并勾选标签',900,990,420,70),('编辑导图 → 保存 → 刷新恢复',20,730,340,80),('待办完成 → 返回来源笔记',430,730,360,80)]
bs=[]
for i,(s,x,y,w,h) in enumerate(texts):bs.append(d.box(s,x,y,w,h,'rhombus;whiteSpace=wrap;html=0;fillColor=#FFF2DA;strokeColor=#D2A544;fontFamily=Microsoft YaHei;fontSize=15;' if i in [2,8] else 'rounded=1;whiteSpace=wrap;html=0;fillColor=#E9F4EF;strokeColor=#32785E;fontFamily=Microsoft YaHei;fontSize=15;'))
for a,b,t in [(0,1,''),(1,2,''),(2,3,'是'),(3,4,'保存'),(2,4,'否'),(4,5,''),(4,6,''),(4,7,''),(5,12,''),(6,13,''),(7,8,''),(8,9,'否 / 错误 / 无 Key'),(8,10,'是'),(9,11,''),(10,11,'')]:d.edge(bs[a],bs[b],t)
d.save('03-业务流程图.drawio')
# Native StarUML semantic models and view objects, following official MDJ schema.
p=obj('Project',name='智汇笔记');model=obj('UMLModel',p,name='课程交付模型',ownedElements=[]);p['ownedElements']=[model]
diagram=obj('UMLClassDiagram',model,name='核心数据类图',defaultDiagram=True,ownedViews=[]);model['ownedElements'].append(diagram)
classes={};views={}
def baseview(t,parent,model=None,**k):return obj(t,parent,**({'model':ref(model)} if model else {}),visible=True,enabled=True,lineColor='#32785E',fillColor='#F5FAF7',fontColor='#182E25',font='Microsoft YaHei;13;0',showShadow=False,**k)
for i,(name,fs) in enumerate(fields.items()):
 c=obj('UMLClass',model,name=name,visibility='public',attributes=[]);classes[name]=c;model['ownedElements'].append(c)
 for f in fs:
  parts=f.split(':',1);c['attributes'].append(obj('UMLAttribute',c,name=parts[0],type=parts[1].strip() if len(parts)>1 else 'constraint',visibility='public'))
 x=40+(i%4)*370;y=60+(i//4)*460
 v=baseview('UMLClassView',diagram,c,left=x,top=y,width=340,height=400,autoResize=False,showType=True,showVisibility=True,suppressOperations=True,subViews=[]);views[name]=v
 comp=baseview('UMLNameCompartmentView',v,c,left=x,top=y,width=340,height=40,subViews=[])
 label=baseview('LabelView',comp,c,left=x+8,top=y+8,width=324,height=26,text=name,font='Microsoft YaHei;15;1') if False else obj('LabelView',comp,model=ref(c),visible=True,font='Microsoft YaHei;15;1',left=x+8,top=y+8,width=324,height=26,text=name)
 comp['subViews']=[label];comp['nameLabel']=ref(label);v['subViews'].append(comp);v['nameCompartment']=ref(comp)
 attr=baseview('UMLAttributeCompartmentView',v,c,left=x,top=y+44,width=340,height=340,subViews=[])
 for j,a in enumerate(c['attributes']):attr['subViews'].append(baseview('UMLAttributeView',attr,a,left=x+8,top=y+48+j*27,width=324,height=26,text=a['name']+': '+a['type']))
 v['subViews'].append(attr);v['attributeCompartment']=ref(attr);diagram['ownedViews'].append(v)
for a,b,label in relations:
 dep=obj('UMLDependency',model,name=label,source=ref(classes[a]),target=ref(classes[b]));model['ownedElements'].append(dep)
 av,bv=views[a],views[b];diagram['ownedViews'].append(baseview('UMLDependencyView',diagram,dep,tail=ref(av),head=ref(bv),lineStyle=1,points=f"{av['left']+170}:{av['top']+400};{bv['left']+170}:{bv['top']}",subViews=[]))
def sequence(name,participants,messages):
 inter=obj('UMLInteraction',model,name=name,participants=[],messages=[],ownedElements=[]);model['ownedElements'].append(inter)
 diag=obj('UMLSequenceDiagram',inter,name=name,ownedViews=[]);inter['ownedElements'].append(diag)
 lines=[];lineviews=[]
 for i,n in enumerate(participants):
  ll=obj('UMLLifeline',inter,name=n,visibility='public',isMultiInstance=False);inter['participants'].append(ll);lines.append(ll)
  x=40+i*270;v=baseview('UMLSeqLifelineView',diag,ll,left=x,top=40,width=230,height=740,autoResize=False,showType=False,subViews=[])
  comp=baseview('UMLNameCompartmentView',v,ll,left=x,top=40,width=230,height=55,subViews=[]);lab=obj('LabelView',comp,model=ref(ll),visible=True,text=n,font='Microsoft YaHei;13;0',left=x+8,top=52,width=214,height=32);comp['nameLabel']=ref(lab);comp['subViews']=[lab]
  part=baseview('UMLLinePartView',v,ll,left=x+115,top=96,width=1,height=680);v['subViews']=[comp,part];v['nameCompartment']=ref(comp);v['linePart']=ref(part);diag['ownedViews'].append(v);lineviews.append(part)
 for j,(a,b,text) in enumerate(messages):
  msg=obj('UMLMessage',inter,name=text,source=ref(lines[a]),target=ref(lines[b]),messageSort='synchCall',visibility='public');inter['messages'].append(msg)
  y=140+j*65;xa=lineviews[a]['left'];xb=lineviews[b]['left'];v=baseview('UMLSeqMessageView',diag,msg,tail=ref(lineviews[a]),head=ref(lineviews[b]),lineStyle=0,points=f'{xa}:{y};{xb}:{y}',subViews=[])
  label=baseview('EdgeLabelView',v,msg,text=str(j+1)+': '+text,left=min(xa,xb)+5,top=y-28,width=abs(xb-xa)-10,height=26,hostEdge=ref(v),edgePosition=1,distance=15,alpha=1.5708);v['nameLabel']=ref(label);v['subViews']=[label];diag['ownedViews'].append(v)
sequence('笔记转导图时序图',['用户','Vue 笔记页','Flask 转换服务','SQLite'],[(0,1,'点击一键转导图'),(1,2,'有修改先 PUT 保存正文'),(2,3,'提交清理后正文'),(1,2,'POST notes/{id}/to-mindmap'),(2,3,'读取当前用户笔记'),(3,2,'返回已保存 HTML / 旧 Markdown'),(2,3,'解析 h1/h2/h3 并 INSERT 新导图'),(2,1,'返回 map_json 与 id'),(1,0,'跳转编辑导图，独立保存')])
sequence('AI 降级时序图',['Vue 预览界面','Flask AI 服务','DeepSeek API','本地规则引擎'],[(0,1,'POST summary / tags + note_id'),(1,3,'无 Key：立即生成本地结果'),(1,2,'有 Key：仅发送纯文本，最多 10000 字'),(2,1,'有效响应，或超时 / 错误 / 非法结果'),(1,3,'异常时降级；总等待不超过 8 秒'),(3,1,'确定性摘要 / 最多五个候选标签'),(1,0,'返回 engine、reason、truncated'),(0,1,'用户勾选标签后 PUT notes/{id}'),(1,0,'原标签合并去重；摘要不改写笔记')])
(OUT/'04-类图与时序图.mdj').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
ids=set();refs=[]
def validate(x):
 if isinstance(x,dict):
  if '_id' in x:
   assert x['_id'] not in ids;ids.add(x['_id'])
  if '$ref' in x:refs.append(x['$ref'])
  for v in x.values():validate(v)
 elif isinstance(x,list):
  for v in x:validate(v)
validate(p);assert set(refs)<=ids
(OUT/'README.md').write_text('''# 可编辑建模源文件

01：用户用例图；02：与 SQLAlchemy 模型对应的八表 E-R 图；03：业务与 AI 降级流程。
前三份 `.drawio` 为未压缩 XML，可直接在 diagrams.net 中打开和修改。
04 为 StarUML JSON 工程，包含核心数据类图和两张时序图。NoteTag 表作为数据关系类表示，实际代码采用 db.Table；类间依赖标注对应外键基数。

已校验 XML、JSON、唯一 ID 和全部内部引用。当前环境未安装 StarUML，尚未完成在 StarUML 桌面版中打开后的人工排版验收；请组员在目标版本中打开复核。模型依据最终代码而非模板示例。

格式参考：[StarUML 官方示例](https://github.com/staruml/staruml-xmi/blob/master/unittest-files/XMI21-test-model.mdj)。
''',encoding='utf-8')
print('3 drawio diagrams, 3 StarUML diagrams;',len(ids),'unique objects,',len(refs),'valid references')
