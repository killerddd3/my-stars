import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

token = os.getenv("GH_TOKEN")
username = os.getenv("USERNAME")
URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {token}"}




def run_query(query, variables):
    response = requests.post(URL, json={'query': query, 'variables': variables}, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Query failed: {response.status_code}")


# --- Query 定义保持不变 ---
ALL_STARS_QUERY = """query($login: String!, $cursor: String) {
  user(login: $login) {
    starredRepositories(first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { nameWithOwner url description }
    }
  }
}"""

LIST_ITEMS_QUERY = """query($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on UserList {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { ... on Repository { nameWithOwner url description } }
      }
    }
  }
}"""


def fetch_all_stars():
    """全量抓取 Stars (串行，因为依赖 Cursor)"""
    all_stars = {}
    has_next, cursor = True, None
    while has_next:
        res = run_query(ALL_STARS_QUERY, {"login": username, "cursor": cursor})
        data = res['data']['user']['starredRepositories']
        for repo in data['nodes']:
            all_stars[repo['nameWithOwner']] = {
                "url": repo['url'], "description": repo['description'] or "No description"
            }
        has_next = data['pageInfo']['hasNextPage']
        cursor = data['pageInfo']['endCursor']
    return all_stars


def fetch_single_list(l_id, l_name):
    """抓取单个 List 的所有内容 (用于线程池)"""
    repos = []
    has_next, cursor = True, None
    while has_next:
        res = run_query(LIST_ITEMS_QUERY, {"id": l_id, "cursor": cursor})
        items_data = res['data']['node']['items']
        for repo in items_data['nodes']:
            repos.append(repo)
        has_next = items_data['pageInfo']['hasNextPage']
        cursor = items_data['pageInfo']['endCursor']
    return l_name, repos


def fetch_data_parallel():
    # 1. 先抓全量 Stars (这是大头，但必须串行)
    all_stars = fetch_all_stars()

    # 2. 获取 List 列表
    lists_res = run_query(
        """query($login: String!) { user(login: $login) { lists(first: 100) { nodes { id name } } } }""",
        {"login": username})
    list_configs = lists_res['data']['user']['lists']['nodes']

    # 3. 多线程抓取各个 List 内容
    lists_content = {}
    categorized_names = set()

    # 使用线程池，max_workers 建议设为 5-10，避免触发 GitHub 的频率限制
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_list = {executor.submit(fetch_single_list, l['id'], l['name']): l['name'] for l in list_configs}

        for future in as_completed(future_to_list):
            l_name, repos = future.result()
            lists_content[l_name] = repos
            for r in repos:
                categorized_names.add(r['nameWithOwner'])

    # 4. 计算未分类
    uncategorized = [
        {"nameWithOwner": name, "url": info['url'], "description": info['description']}
        for name, info in all_stars.items() if name not in categorized_names
    ]

    return lists_content, uncategorized


def generate_slug(text):
    """将标题转换为 GitHub 锚点格式"""
    # 转换为小写，去掉非字母数字字符（保留空格和中划线），空格换成中划线
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug

# --- 保存逻辑 ---
def save_md(lists_content, uncategorized):
    # 获取并排序所有分类名称
    sorted_list_names = sorted(lists_content.keys())

    with open("lists.md", "w", encoding="utf-8") as f:
        f.write(f"# GitHub Stars & Lists - {username}\n\n")

        # --- 1. 生成目录 (Contents) ---
        f.write("## Contents\n\n")
        for name in sorted_list_names:
            slug = generate_slug(name)
            f.write(f"- [{name}](#{slug})\n")

        if uncategorized:
            f.write(f"- [未分类 (Uncategorized)](#未分类-uncategorized)\n")

        f.write("\n---\n\n")  # 分割线

        # --- 2. 生成正文 ---
        for name in sorted_list_names:
            repos = lists_content[name]
            f.write(f"## {name} ({len(repos)})\n")
            for r in repos:
                desc = r.get('description') or "No description"
                f.write(f"- [{r['nameWithOwner']}]({r['url']}) - {desc}\n")
            f.write("\n")

        # 写入未分类部分
        if uncategorized:
            f.write(f"## 未分类 (Uncategorized) ({len(uncategorized)})\n")
            for r in uncategorized:
                f.write(f"- [{r['nameWithOwner']}]({r['url']}) - {r['description']}\n")


if __name__ == "__main__":
    if token and username:
        l_content, uncat = fetch_data_parallel()
        save_md(l_content, uncat)
    else:
        print("请检查环境变量")
