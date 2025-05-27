import os
import requests
from github import Github

# 获取 GitHub 认证信息
token = os.environ["GITHUB_TOKEN"]
username = os.environ["GITHUB_USERNAME"]

# 初始化 GitHub API 客户端
g = Github(token)

# 获取用户
user = g.get_user(username)

# 创建 Markdown 内容
markdown_content = "# GitHub Starred Lists\n\n"
markdown_content += f"Starred lists created by [{username}](https://github.com/{username}).\n\n"

# 获取所有 Starred Lists
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 注意：GitHub Starred Lists API 目前可能需要特定的媒体类型
# 以下端点可能需要调整，根据 GitHub 官方文档更新
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
    
    # 添加列表中的每个仓库
    for repo in repos:
        repo_name = repo["full_name"]
        repo_desc = repo["description"] or ""
        repo_stars = repo["stargazers_count"]
        repo_url = repo["html_url"]
        
        # 转义 Markdown 表格中的竖线
        repo_desc = repo_desc.replace("|", "\\|")
        
        markdown_content += f"| [{repo_name}]({repo_url}) | {repo_desc} | ⭐️ {repo_stars} |\n"
    
    markdown_content += "\n\n"

# 写入 Markdown 文件
with open("lists.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

print("Successfully generated lists.md")
