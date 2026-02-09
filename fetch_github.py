import requests
import os

token = os.getenv("GH_TOKEN")
username = os.getenv("USERNAME")

URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {token}"}


def run_query(query, variables):
    response = requests.post(URL, json={'query': query, 'variables': variables}, headers=HEADERS)
    if response.status_code == 200:
        res_json = response.json()
        if "errors" in res_json:
            print(f"API Error: {res_json['errors']}")
        return res_json
    else:
        raise Exception(f"Query failed: {response.status_code}")


# 1. 获取所有 Star 的 Query
ALL_STARS_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    starredRepositories(first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        nameWithOwner
        url
        description
      }
    }
  }
}
"""

# 2. 获取所有 List 的 ID 和名字
LISTS_BASE_QUERY = """
query($login: String!) {
  user(login: $login) {
    lists(first: 100) {
      nodes { id name }
    }
  }
}
"""

# 3. 获取特定 List 下的仓库 (分页)
LIST_ITEMS_QUERY = """
query($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on UserList {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          ... on Repository { nameWithOwner url description }
        }
      }
    }
  }
}
"""


def fetch_data():
    # A. 获取所有 Star
    print("正在获取所有 Star 仓库数据...")
    all_stars = {}  # key: nameWithOwner, value: dict
    has_next = True
    cursor = None
    while has_next:
        res = run_query(ALL_STARS_QUERY, {"login": username, "cursor": cursor})
        stars_data = res['data']['user']['starredRepositories']
        for repo in stars_data['nodes']:
            all_stars[repo['nameWithOwner']] = {
                "url": repo['url'],
                "desc": repo['description'] or "No description"
            }
        has_next = stars_data['pageInfo']['hasNextPage']
        cursor = stars_data['pageInfo']['endCursor']
        print(f"  已记录 {len(all_stars)} 个 Star...")

    # B. 获取所有 List 及其包含的仓库
    print("\n正在获取各个 List 分类...")
    lists_res = run_query(LISTS_BASE_QUERY, {"login": username})
    lists_nodes = lists_res['data']['user']['lists']['nodes']

    categorized_names = set()  # 记录已经分过类的仓库名
    lists_content = {}  # key: list_name, value: list of repos

    for l in lists_nodes:
        l_id, l_name = l['id'], l['name']
        print(f"正在抓取列表: {l_name}...")
        lists_content[l_name] = []
        has_next, cursor = True, None
        while has_next:
            res = run_query(LIST_ITEMS_QUERY, {"id": l_id, "cursor": cursor})
            items_data = res['data']['node']['items']
            for repo in items_data['nodes']:
                name = repo['nameWithOwner']
                lists_content[l_name].append(repo)
                categorized_names.add(name)  # 标记为已分类
            has_next = items_data['pageInfo']['hasNextPage']
            cursor = items_data['pageInfo']['endCursor']
        print(f"  {l_name} 包含 {len(lists_content[l_name])} 个仓库")

    # C. 计算未分类 (差集)
    uncategorized = []
    for name, info in all_stars.items():
        if name not in categorized_names:
            uncategorized.append({
                "nameWithOwner": name,
                "url": info['url'],
                "description": info['desc']
            })

    return lists_content, uncategorized


def save_md(lists_content, uncategorized):
    with open("lists.md", "w", encoding="utf-8") as f:
        f.write(f"# GitHub Stars & Lists - {username}\n\n")

        # 先写自定义列表
        for name, repos in lists_content.items():
            f.write(f"## {name} ({len(repos)})\n")
            for r in repos:
                desc = r['description'] or "No description"
                f.write(f"- [{r['nameWithOwner']}]({r['url']}) - {desc}\n")
            f.write("\n")

        # 再写未分类列表
        if uncategorized:
            f.write(f"## 未分类 (Uncategorized) ({len(uncategorized)})\n")
            for r in uncategorized:
                f.write(f"- [{r['nameWithOwner']}]({r['url']}) - {r['description']}\n")
            f.write("\n")
    print(f"\n✅ 完成！未分类仓库共 {len(uncategorized)} 个。")


if __name__ == "__main__":
    if not token or not username:
        print("请检查环境变量 GH_TOKEN 和 USERNAME")
    else:
        l_content, uncat = fetch_data()
        save_md(l_content, uncat)
