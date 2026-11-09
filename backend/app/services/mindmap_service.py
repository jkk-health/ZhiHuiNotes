import json
from app.services.api_utils import ApiError, text
from app.services.content_service import note_html, parse_html


def generate(note):
    root = {'id': 'root', 'topic': note.title, 'children': []}
    stack = [(0, root)]
    headings = parse_html(note_html(note)).headings
    for i, (level, title) in enumerate(headings):
        while stack[-1][0] >= level:
            stack.pop()
        node = {'id': f'n{i + 1}', 'topic': title[:200], 'children': []}
        stack[-1][1]['children'].append(node)
        stack.append((level, node))
    return {'meta': {'name': note.title, 'version': '1'}, 'format': 'node_tree', 'data': root}


def validate_map(value):
    if not isinstance(value, dict) or value.get('format') != 'node_tree':
        raise ApiError('导图必须是 node_tree 格式的 JSON 对象')
    seen = set()

    def check(node, depth=0):
        if not isinstance(node, dict) or depth > 64 or len(seen) >= 1000:
            raise ApiError('导图结构无效，最多 1000 节点、64 层')
        node_id = text(node.get('id'), '节点 ID', 100)
        if node_id in seen:
            raise ApiError('节点 ID 不能重复')
        seen.add(node_id)
        result = {'id': node_id, 'topic': text(node.get('topic'), '节点文字', 200)}
        if 'direction' in node:
            if node['direction'] not in {'left', 'right'}:
                raise ApiError('节点方向无效')
            result['direction'] = node['direction']
        children = node.get('children', [])
        if not isinstance(children, list):
            raise ApiError('children 必须是数组')
        result['children'] = [check(child, depth + 1) for child in children]
        return result

    root = check(value.get('data'))
    return {'meta': {'name': root['topic'], 'version': '1'}, 'format': 'node_tree', 'data': root}


def encode(value):
    return json.dumps(validate_map(value), ensure_ascii=False)
