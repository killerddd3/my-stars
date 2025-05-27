import os
import requests
from github import Github

# 获取 GitHub 认证信息
token = os.environ["GITHUB_TOKEN"]
username = os.environ["GITHUB_USERNAME"]

# 初始化 GitHub API 客户端
g = Github(token)

# 创建 Markdown 内容
markdown_content = "# GitHub Starred Lists\n\n"
markdown_content += f"Starred lists created by [{username}](https://github.com/{username}).\n\n"

# 存储所有已分配仓库的集合（避免重复）
assigned_repos = set()

# ----------------------
# 1. 处理已创建的 Starred Lists
# ----------------------
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}
lists_url = f"https://api.github.com/users/{username}/starred_lists"
response = requests.get(lists_url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Failed to fetch starred lists: {response.text}")

lists = response.json()

# 遍历每个列表并获取仓库
for list_item in lists:
    list_name = list_item["name"]
    list_description = list_item["description"] or ""
    list_url = list_item["url"]
    
    # 获取列表中的仓库
    repos_response = requests.get(f"{list_url}/items", headers=headers)
    if repos_response.status_code != 200:
        print(f"Failed to fetch repos for list {list_name}: {repos_response.text}")
        continue
    
    repos = repos_response.json()
    
    # 添加列表标题
    markdown_content += f"## {list_name}\n"
    markdown_content += f"{list_description}\n\n"
    markdown_content += "| Repository | Description | Stars |\n"
    markdown_content += "|------------|-------------|-------|\n"
    
    # 添加列表中的每个仓库，并记录已分配的仓库
    for repo in repos:
        repo_full_name = repo["full_name"]
        assigned_repos.add(repo_full_name)  # 记录已分配的仓库
        repo_desc = repo["description"] or ""
        repo_stars = repo["stargazers_count"]
        repo_url = repo["html_url"]
        
        # 转义 Markdown 表格中的竖线
        repo_desc = repo_desc.replace("|", "\\|")
        
        markdown_content += f"| [{repo_full_name}]({repo_url}) | {repo_desc} | ⭐️ {repo_stars} |\n"
    
    markdown_content += "\n\n"

# ----------------------
# 2. 处理未分配到任何 List 的仓库（Unknown 分类）
# ----------------------
unknown_repos = []

# 获取用户所有 Starred 仓库（可能需要分页处理，此处简化为单次请求）
all_starred = g.get_user(username).get_starred()

for repo in all_starred:
    repo_full_name = repo.full_name
    if repo_full_name not in assigned_repos:
        unknown_repos.append(repo)

# 添加 Unknown 分类
if unknown_repos:
    markdown_content += "## Unknown\n"
    markdown_content += "Repositories not assigned to any Starred List.\n\n"
    markdown_content += "| Repository | Description | Stars |\n"
    markdown_content += "|------------|-------------|-------|\n"
    
    for repo in unknown_repos:
        repo_full_name = repo.full_name
        repo_desc = repo.description or ""
        repo_stars = repo.stargazers_count
        repo_url = repo.html_url
        
        repo_desc = repo_desc.replace("|", "\\|")
        markdown_content += f"| [{repo_full_name}]({repo_url}) | {repo_desc} | ⭐️ {repo_stars} |\n"
    
    markdown_content += "\n\n"

# 写入 Markdown 文件
with open("lists.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

print("Successfully generated lists.md with Unknown category")
