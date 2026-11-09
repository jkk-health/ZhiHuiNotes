"""User-visible module behavior, isolation, validation and cross-module retention."""
import copy
import time
from decimal import Decimal
import pytest
import requests
from app.services import ai_service


def note(client, html='<h1>Python 学习</h1><h3>Flask 接口</h3><h2>数据库</h2><p>使用 SQLite 保存学习笔记。</p>'):
    response = client.post('/api/notes', json={'title': '项目笔记', 'content_html': html, 'content_md':'错误副本', 'tags':['原标签']})
    assert response.status_code == 201
    return response.get_json()


def tree():
    return {'format':'node_tree', 'data':{'id':'root','topic':'根节点','children':[{'id':'one','topic':'<img src=x onerror=alert(1)>'}]}}


@pytest.mark.parametrize('resource', ['todos', 'mindmaps', 'bills'])
def test_modules_require_login(client, resource):
    assert client.get('/api/'+resource).status_code == 401
    assert client.post('/api/'+resource, json={}).status_code == 401
    for method in ('get','put','delete'):
        assert getattr(client,method)('/api/'+resource+'/1').status_code == 401


@pytest.mark.parametrize('resource', ['todos','mindmaps','bills','ai/summary','ai/tags'])
@pytest.mark.parametrize('body', [None, [], 'invalid'])
def test_json_object_validation(user_client,resource,body):
    assert user_client.post('/api/'+resource,json=body).status_code == 400


def test_rich_text_canonical_and_sanitized(user_client):
    value=note(user_client, '<h1>主题</h1><p><span class="ql-size-large" style="color:red;position:fixed">检索内容</span><img src="x" onerror="alert(1)"><script>恶意内容</script></p>')
    assert '错误副本' not in value['content_md']
    assert '检索内容' in value['content_md']
    assert 'onerror' not in value['content_html'] and '<script' not in value['content_html']
    assert 'position' not in value['content_html'] and 'ql-size-large' in value['content_html']
    assert '恶意内容' not in value['content_md']
    assert len(user_client.get('/api/notes?q=检索内容').get_json()) == 1
    result=user_client.put('/api/notes/'+str(value['id']),json={'content_html':'<p>新的正文</p>'}).get_json()
    assert result['content_md'] == '新的正文'
    assert user_client.get('/api/notes?q=检索内容').get_json() == []


def test_legacy_markdown_to_map_and_ai(user_client):
    value=user_client.post('/api/notes',json={'title':'旧笔记','content_md':'# 一级\n### 跳级\n\nPython 学习'}).get_json()
    generated=user_client.post(f"/api/notes/{value['id']}/to-mindmap",json={}).get_json()
    assert generated['map_json']['data']['children'][0]['children'][0]['topic'] == '跳级'
    assert user_client.post('/api/ai/summary',json={'note_id':value['id']}).get_json()['engine'] == 'local'


@pytest.mark.parametrize('bad', [[], 12, True])
def test_invalid_note_body(user_client,bad):
    assert user_client.post('/api/notes',json={'title':'测试','content_html':bad}).status_code == 400


def test_embedded_images(user_client):
    image='data:image/png;base64,iVBORw0KGgo='
    assert image in note(user_client,f'<p>图片</p><img src="{image}">')['content_html']
    value=note(user_client,'<img src="data:image/svg+xml;base64,PHN2Zz4=">')
    assert 'svg+xml' not in value['content_html']
    assert user_client.post('/api/notes',json={'title':'超限','content_html':'<img src="data:image/png;base64,' + 'AAAA'*700000 + '">'}).status_code == 400


def test_todo_crud_filters_and_retention(user_client):
    source=note(user_client)
    created=user_client.post('/api/todos',json={'title':'完成作业','note_id':source['id'],'due_date':'2026-10-11'}).get_json()
    path='/api/todos/'+str(created['id'])
    assert created['source_note']['title'] == source['title']
    assert len(user_client.get(f"/api/todos?note_id={source['id']}&done=0").get_json()) == 1
    assert user_client.put(path,json={'done':True}).get_json()['done'] is True
    assert user_client.get('/api/todos?done=0').get_json() == []
    user_client.delete('/api/notes/'+str(source['id']))
    assert user_client.get(path).get_json()['source_note']['is_deleted'] is True
    assert user_client.put(path,json={'note_id':source['id'],'title':'仍可编辑'}).status_code == 200
    user_client.post(f"/api/notes/{source['id']}/restore",json={})
    assert user_client.get(path).get_json()['source_note']['is_deleted'] is False
    assert user_client.put(path,json={'note_id':None,'due_date':None}).get_json()['source_note'] is None
    assert user_client.delete(path).status_code == 200
    assert user_client.get(path).status_code == 404


@pytest.mark.parametrize('data',[{'title':''},{'title':12},{'title':'a','done':'false'},{'title':'a','due_date':'2026-02-30'},{'title':'a','note_id':True},{'title':'a','note_id':-1}])
def test_todo_validation(user_client,data):
    assert user_client.post('/api/todos',json=data).status_code == 400


@pytest.mark.parametrize('query',['done=false','note_id=x','note_id=-1'])
def test_todo_filter_validation(user_client,query):
    assert user_client.get('/api/todos?'+query).status_code == 400


def test_mindmap_generation_update_preview_retention(user_client):
    source=note(user_client)
    path=f"/api/notes/{source['id']}/to-mindmap"
    first=user_client.post(path,json={}).get_json()
    root=first['map_json']['data']
    assert root['topic'] == source['title']
    assert [child['topic'] for child in root['children']] == ['Python 学习']
    assert [child['topic'] for child in root['children'][0]['children']] == ['Flask 接口','数据库']
    second=user_client.post(path,json={}).get_json()
    assert first['id'] != second['id']
    preview=user_client.post(path+'?preview=1',json={}).get_json()
    assert 'map_json' in preview and len(user_client.get('/api/mindmaps').get_json()) == 2
    map_path='/api/mindmaps/'+str(first['id'])
    updated=user_client.put(map_path,json={'map_json':tree(),'title':'编辑后的导图'}).get_json()
    assert updated['map_json']['data']['children'][0]['topic'].startswith('<img')
    assert user_client.get('/api/notes/'+str(source['id'])).get_json()['title'] == source['title']
    user_client.delete('/api/notes/'+str(source['id']))
    assert user_client.get(map_path).get_json()['source_note']['is_deleted'] is True
    assert user_client.delete(map_path).status_code == 200


@pytest.mark.parametrize('value',[None,{},'{}',{'format':'node_tree','data':[]},{'format':'node_tree','data':{'id':'r','topic':'根','children':[{'id':'r','topic':'重复'}]}},{'format':'node_tree','data':{'id':'r','topic':'根','children':{}}}])
def test_invalid_maps(user_client,value):
    assert user_client.post('/api/mindmaps',json={'title':'导图','map_json':value}).status_code == 400


def test_single_root_and_hundred_nodes(user_client):
    source=note(user_client,'<p>没有标题的正文</p>')
    result=user_client.post(f"/api/notes/{source['id']}/to-mindmap",json={}).get_json()
    assert result['map_json']['data']['children'] == []
    value=tree();value['data']['children']=[{'id':str(i),'topic':'节点'+str(i)} for i in range(100)]
    saved=user_client.post('/api/mindmaps',json={'title':'百节点','map_json':value}).get_json()
    assert len(user_client.get('/api/mindmaps/'+str(saved['id'])).get_json()['map_json']['data']['children']) == 100


def bill(client,amount='0.10',day='2026-10-11',type_='支',category='餐饮'):
    return client.post('/api/bills',json={'type':type_,'amount':amount,'bill_date':day,'category':category})


def test_bill_decimal_monthly_update_delete(user_client):
    first=bill(user_client).get_json()
    bill(user_client,'0.20')
    bill(user_client,'1.00',type_='收')
    bill(user_client,'88.88',day='2026-09-30')
    totals=user_client.get('/api/bills/monthly?month=2026-10').get_json()
    assert Decimal(str(totals['expense'])) == Decimal('0.30')
    assert totals['balance'] == .7 and len(totals['daily']) == 31
    assert totals['daily'][0]['expense'] == 0
    assert totals['categories'] == [{'name':'餐饮','value':.3}]
    path='/api/bills/'+str(first['id'])
    assert user_client.put(path,json={'amount':'2.10','bill_date':'2026-09-29'}).status_code == 200
    assert user_client.get('/api/bills/monthly?month=2026-10').get_json()['expense'] == .2
    assert user_client.delete(path).status_code == 200
    empty=user_client.get('/api/bills/monthly?month=2024-02').get_json()
    assert empty['income'] == empty['expense'] == empty['balance'] == 0
    assert len(empty['daily']) == 29 and empty['categories'] == []


@pytest.mark.parametrize('amount',['0','-1','1.001','NaN','Infinity','100000000',True,[],None,'abc'])
def test_bill_invalid_amount(user_client,amount):
    assert bill(user_client,amount).status_code == 400


@pytest.mark.parametrize('month',['','2026-13','2026-1','x'])
def test_bill_invalid_month(user_client,month):
    assert user_client.get('/api/bills/monthly?month='+month).status_code == 400


@pytest.mark.parametrize('resource',['todos','mindmaps','bills'])
def test_new_module_isolation(user_client,client,resource):
    source=note(user_client)
    if resource == 'todos': created=user_client.post('/api/todos',json={'title':'任务','note_id':source['id']}).get_json()
    elif resource == 'mindmaps': created=user_client.post(f"/api/notes/{source['id']}/to-mindmap",json={}).get_json()
    else: created=bill(user_client).get_json()
    client.post('/api/auth/register',json={'username':'other','password':'abc123456'})
    path='/api/'+resource+'/'+str(created['id'])
    for method in ('get','put','delete'):
        assert getattr(client,method)(path,json={}).status_code == 404
    assert client.get('/api/'+resource).get_json() == []
    assert client.post('/api/todos',json={'title':'越权','note_id':source['id']}).status_code == 404
    assert client.post('/api/mindmaps',json={'title':'越权','note_id':source['id'],'map_json':tree()}).status_code == 404
    assert client.post('/api/ai/summary',json={'note_id':source['id']}).status_code == 404
    assert client.post(f"/api/notes/{source['id']}/to-mindmap",json={}).status_code == 404


def test_ai_local_no_mutations(user_client):
    value=note(user_client)
    before=user_client.get('/api/notes/'+str(value['id'])).get_json()
    summary=user_client.post('/api/ai/summary',json={'note_id':value['id']}).get_json()
    tags=user_client.post('/api/ai/tags',json={'note_id':value['id']}).get_json()
    assert summary['engine'] == tags['engine'] == 'local'
    assert summary['reason'] == 'no_key' and summary['summary']
    assert 'Python' in tags['tags'] and len(tags['tags']) <= 5
    assert user_client.get('/api/notes/'+str(value['id'])).get_json() == before


def test_ai_empty_and_truncation(user_client):
    empty=note(user_client,'<p><br></p>')
    assert user_client.post('/api/ai/tags',json={'note_id':empty['id']}).status_code == 400
    long=note(user_client,'<p>'+'学习。'*4000+'</p>')
    assert user_client.post('/api/ai/summary',json={'note_id':long['id']}).get_json()['input_truncated'] is True


@pytest.mark.parametrize('kind,result',[('summary','真实摘要'),('tags',['Python','学习'])])
def test_ai_valid_remote(app,user_client,monkeypatch,kind,result):
    app.config['DEEPSEEK_API_KEY']='fake-test-key'
    value=note(user_client)
    class Response:
        def raise_for_status(self): pass
        def json(self):
            import json
            return {'choices':[{'message':{'content':json.dumps({kind:result},ensure_ascii=False)}}]}
    seen=[]
    def post(*args,**kwargs): seen.append(kwargs);return Response()
    monkeypatch.setattr(ai_service.requests,'post',post)
    answer=user_client.post('/api/ai/'+kind,json={'note_id':value['id']}).get_json()
    assert answer['engine'] == 'api' and answer[kind] == result
    assert '<h1>' not in seen[0]['json']['messages'][1]['content']


@pytest.mark.parametrize('failure,reason',[(requests.Timeout(),'timeout'),(requests.ConnectionError(),'api_error'),(requests.HTTPError(),'api_error'),(ValueError(),'invalid_response')])
def test_ai_remote_failure(app,user_client,monkeypatch,failure,reason):
    app.config['DEEPSEEK_API_KEY']='fake-test-key'
    value=note(user_client)
    def fail(*args): raise failure
    monkeypatch.setattr(ai_service,'remote_result',fail)
    answer=user_client.post('/api/ai/summary',json={'note_id':value['id']}).get_json()
    assert answer['engine'] == 'local' and answer['reason'] == reason


def test_ai_hard_wait_budget(app,user_client,monkeypatch):
    app.config.update(DEEPSEEK_API_KEY='fake-test-key',AI_TIMEOUT_SECONDS=.02)
    value=note(user_client)
    def slow(*args): time.sleep(.1);return '迟到结果'
    monkeypatch.setattr(ai_service,'remote_result',slow)
    start=time.monotonic()
    answer=user_client.post('/api/ai/summary',json={'note_id':value['id']}).get_json()
    assert time.monotonic()-start < .09
    assert answer['engine'] == 'local' and answer['reason'] == 'timeout'
