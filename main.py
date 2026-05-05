import pickle
from time import sleep
import logging as log

import github
from github import Auth, Github
from discord_webhook import DiscordWebhook, DiscordEmbed

from _secrets import *


def notify(header: str, commit: github.Commit.Commit):
    msg = f"# {header}\n\n```{commit.commit.message}```\n<{commit.html_url}>"
    webhook = DiscordWebhook(url=discord_webhook_url_main, content=msg)
    response = webhook.execute()
    log.info(msg)


def main():
    log.basicConfig(
        format='%(asctime)-15s [%(levelname)-8s]: %(message)s',
        level=log.DEBUG,
        handlers=[
            log.FileHandler("unreal_commit_notifier.log"),
            log.StreamHandler(),
        ]
    )
    pkl_fn = "lastcommit.pkl"
    paths_to_match = [
        "/nDisplay",
        "ChaosVehicle",
    ]
    last_commit = None
    while True:
        log.debug("Checking for new commits...")
        try:
            try:
                with open(pkl_fn, 'rb') as f:
                    last_commit = pickle.load(f)
            except FileNotFoundError:
                pass

            log.debug(f"Last commit: {last_commit}")
            auth = Auth.Token(gh_pat)
            g = Github(auth=auth)

            repo = g.get_repo("EpicGames/UnrealEngine")
            for i, commit in enumerate(repo.get_commits("ue5-main")):
                if last_commit is None:
                    last_commit = commit.sha
                    log.debug(f"Initializing script at commit {last_commit}")
                log.debug(f"Checking commit #{i}: {commit.sha}")
                if last_commit == commit.sha:
                    break
                for f in commit.files:
                    if f.filename.endswith(".uplugin") and f.status == "added":
                        notify("New plugin", commit)
                        break
                    for p in paths_to_match:
                        if p.lower() in f.filename.lower():
                            notify(f"Changes in {p}", commit)
                            break
                    else:
                        continue
                    break
                if i == 0:
                    last_commit = commit.sha
                if i == 1000:
                    log.debug("Reached 1000 commits")
                    break
            g.close()
        except Exception as e:
            webhook = DiscordWebhook(url=discord_webhook_url_debug)
            embed = DiscordEmbed(title="Unreal Commit Notifier", color="ff0000")
            embed.add_embed_field(
                name="Exception",
                value=str(e),
                inline=False,
            )
            webhook.add_embed(embed)
            webhook.execute()
            log.exception("An error occurred while checking for commits.")
        finally:
            with open(pkl_fn, 'wb') as f:
                pickle.dump(last_commit, f, pickle.HIGHEST_PROTOCOL)
        log.debug("Iteration complete, sleeping for 30 minutes...")
        sleep(60*30)


if __name__ == '__main__':
    main()
