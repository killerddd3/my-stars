import requests
import os

token = os.getenv("GH_TOKEN")
username = os.getenv("USERNAME")

query = """
{
  user(login: "%s") {
    lists(first: 100) {
      nodes {
        name
        repositories {
          totalCount
          nodes {
            nameWithOwner
            url
            description
          }
        }
      }
    }
  }
}
""" % username

def fetch_lists():
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post("https://api.github.com/graphql", 
                             json={"query": query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        lists = data['data']['user']['lists']['nodes']
        
        with open("LISTS.md", "w", encoding="utf-8") as f:
            f.write(f"# GitHub Custom Lists by {username}\n\n")
            for lst in lists:
                f.write(f"## {lst['name']} ({lst['repositories']['totalCount']})\n")
                for repo in lst['repositories']['nodes']:
                    f.write(f"- [{repo['nameWithOwner']}]({repo['url']}) - {repo['description']}\n")
                f.write("\n")
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    fetch_lists()
