import pickle
from time import sleep
import logging as log

import github
from github import Auth, Github
from discord_webhook import DiscordWebhook, DiscordEmbed

from _secrets import *


def notify_filtered(header: str, commit: github.Commit.Commit):
    msg = f"# {header}\n\n```{commit.commit.message}```\n<{commit.html_url}>"
    send_message(msg, discord_webhook_url_filtered)


def notify_general(commit: github.Commit.Commit):
    msg = f"[`{commit.sha[:7]}`](<{commit.html_url}>) {commit.commit.message.splitlines()[0]} *({commit.commit.author.name})*"
    send_message(msg, discord_webhook_url_all)


def send_message(msg: str, webhook_url: str):
    webhook = DiscordWebhook(url=webhook_url, content=msg, rate_limit_retry=True)
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
        "Switchboard",
    ]
    old_latest_commit = None
    new_latest_commit = None
    while True:
        log.debug("Checking for new commits...")
        try:
            try:
                with open(pkl_fn, 'rb') as f:
                    old_latest_commit = pickle.load(f)
            except FileNotFoundError:
                pass
            new_latest_commit = old_latest_commit
            log.debug(f"Last commit: {old_latest_commit}")
            auth = Auth.Token(gh_pat)
            g = Github(auth=auth)

            repo = g.get_repo("EpicGames/UnrealEngine")
            new_commits = []
            for i, commit in enumerate(repo.get_commits("ue5-main")):
                log.debug(f"Checking commit #{i}: {commit.sha}")
                if i == 0:
                    log.debug(f"New latest commit: {commit.sha}")
                    new_latest_commit = commit.sha
                if i == 1000:
                    log.debug("Reached 1000 commits, stopping")
                    break
                if old_latest_commit is None:
                    log.debug(f"Initializing script at commit {old_latest_commit}, stopping")
                    break
                if old_latest_commit == commit.sha:
                    log.debug(f"Reached last seen commit {old_latest_commit}, stopping")
                    break
                for f in commit.files:
                    if f.filename.endswith(".uplugin") and f.status == "added":
                        notify_filtered("New plugin", commit)
                        break
                    for p in paths_to_match:
                        if p.lower() in f.filename.lower():
                            notify_filtered(f"Changes in {p}", commit)
                            break
                    else:
                        # File didn't match any of our filter, move to next file
                        continue
                    # We had a match, move to next commit
                    break
                else:
                    # No filter matched, sending to general
                    new_commits.append(commit)
            for commit in reversed(new_commits):
                notify_general(commit)
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
                pickle.dump(new_latest_commit, f, pickle.HIGHEST_PROTOCOL)
        log.debug("Iteration complete, sleeping for 30 minutes...")
        sleep(60*30)


if __name__ == '__main__':
    main()
