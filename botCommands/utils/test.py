import requests

res = requests.get("https://api.github.com/repos/Kav-K/Stream4Bot/commits").json()
commitAuthor = res[0]["commit"]["author"]["name"]
commitMessage = res[0]["commit"]["message"]

print(commitAuthor)
print(commitMessage)