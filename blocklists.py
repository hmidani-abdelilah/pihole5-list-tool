""" add/remove/reset blocklists """
import requests

import prompts

import constants
import utils

""" PiHole 5.1 installation defaults """
DEFAULT_LISTS = [
    "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
    "https://mirror1.malwaredomains.com/files/justdomains",
]

blockLists = {
    constants.B_FIREBOG_NOCROSS: {
        "url": "https://v.firebog.net/hosts/lists.php?type=nocross",
        "comment": "Firebog | Non-crossed lists",
    },
    constants.B_FIREBOG_ALL: {
        "url": "https://v.firebog.net/hosts/lists.php?type=all",
        "comment": "Firebog | All lists",
    },
    constants.B_FIREBOG_TICKED: {
        "url": "https://v.firebog.net/hosts/lists.php?type=tick",
        "comment": "Firebog | Ticked lists",
    },
}


def manage_blocklists(cur):
    """ what to do to blocklists """
    questions = [
        {
            "name": "action",
            "type": "list",
            "default": "add",
            "message": "Blocklist action:",
            "choices": [
                {"name": "Add a list", "value": "add",},
                {"name": "Reset to Pihole defaults", "value": "reset",},
                {"name": "Remove ALL Blocklists", "value": "empty",},
            ],
        }
    ]

    result = prompts.key_prompt(questions)
    action = result["action"]
    if action == "add":
        return add(cur)

    if action == "reset":
        return reset(cur)

    if action == "empty":
        return empty(cur)

    return False


def reset(cur):
    """ reset block lists to pihole install default """
    utils.info("\nThis will replace ALL blocklists with these defaults:")

    for url in DEFAULT_LISTS:
        utils.info("    - " + url)
    print()

    if prompts.confirm("Are you sure?", "n"):
        cur.execute("DELETE FROM adlist")
        for url in DEFAULT_LISTS:
            vals = (url, "Pi-hole defaults")
            cur.execute(
                "INSERT OR IGNORE INTO adlist (address, comment) VALUES (?,?)", vals
            )
        return True

    return False


def empty(cur):
    """ remove all block lists"""
    utils.danger("\n\tThis will REMOVE ALL blocklists!\n")

    if prompts.confirm("Are you sure?", "n"):
        cur.execute("DELETE FROM adlist")
        return True

    return False


def add(cur):
    """ prompt for and process blocklists """
    source = prompts.ask_blocklist()

    import_list = []

    if source in blockLists:
        url_source = blockLists[source]
        resp = requests.get(url_source["url"])
        import_list = utils.process_lines(resp.text, url_source["comment"])

    if source == constants.FILE:
        fname = prompts.ask_import_file()
        import_file = open(fname)
        import_list = utils.process_lines(import_file.read(), f"File: {fname}")

    if source == constants.PASTE:
        import_list = prompts.ask_paste()
        import_list = utils.process_lines(import_list, "Pasted content")

    if len(import_list) == 0:
        utils.die("No valid urls found, try again")

    if not prompts.confirm(f"Add {len(import_list)} block lists?"):
        return False

    added = 0
    exists = 0
    for item in import_list:
        cur.execute("SELECT COUNT(*) FROM adlist WHERE address = ?", (item["url"],))

        cnt = cur.fetchone()

        if cnt[0] > 0:
            exists += 1
        else:
            added += 1
            vals = (item["url"], item["comment"])
            cur.execute(
                "INSERT OR IGNORE INTO adlist (address, comment) VALUES (?,?)", vals
            )

    utils.success(f"{added} block lists added! {exists} already existed.")
    return True
