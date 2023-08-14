import itertools
import os
import re
import time
from logging import (DEBUG, INFO, FileHandler, Formatter, StreamHandler,
                     getLogger)
from urllib import parse

import questionary
import requests
from bs4 import BeautifulSoup as bs
from questionary import Choice


def search(name, tag, gender, personality, type, vanilla, orderby, hidden, featured):
    # https://db.bepis.moe/koikatsu?name=i&tag=vtuber&gender=female&personality=0&type=base&vanilla=true&orderby=popularity&hidden=true&featured=true
    cards_ = []
    for i in itertools.count():
        payload = {
            "name": name,
            "tag": tag,
            "gender": gender,
            "personality": personality,
            "type": type,
            "vanilla": str(vanilla).lower(),
            "orderby": orderby,
            "hidden": str(hidden).lower(),
            "featured": str(featured).lower(),
            "page": str(i+1)
        }
        res = requests.get("https://db.bepis.moe/koikatsu", params=payload)
        soup = bs(res.text, "lxml")
        try:
            cards = soup.select("#inner-card-body > div > div")
        except Exception:
            break
        else:
            if cards is None:
                break
        # page_active = soup.select_one("li[class='page-item active']")
        # page_end = soup.select_one("li[class=")
        logger.debug(f"page: {i+1}, card: {24*(i+1)}")
        for card in cards:
            card_ = {}
            title = card.select_one("span").get_text(strip=True)
            url = card.select_one("a[class='btn btn-primary btn-sm']").get("href")
            card_["title"] = title
            card_["url"] = url
            cards_.append(card_)
    return cards_

def count(url):
    id = re.sub(r"\D", "", url)
    payload = {
        "cardType": "KK",
        "cardId": int(id)
    }
    requests.post("https://db.bepis.moe/card/count", data=payload)
def download(card):
    count(card["url"])
    time.sleep(1)
    url = parse.urljoin("https://db.bepis.moe", card["url"])
    name = os.path.basename(url)
    path = os.path.join("./cards/Koikatsu", name)
    if not os.path.exists(path):
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            with open(path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
        logger.info(f"Downloaded. Title: {card['title']}, URL: {card['url']}")
def ask():
    name = questionary.text("Name?").ask()
    tag = questionary.text("Tag?").ask()
    gender = questionary.select(
        "Sex?",
        choices=[
            Choice(title="ALL", value=""),
            Choice(title="Female", value="female"),
            Choice(title="Male", value="male")
        ]
    ).ask()
    personality = ""
    type = questionary.select(
        "Type?",
        choices=[
            Choice(title="ALL", value=""),
            Choice(title="Base", value="base"),
            Choice(title="Steam", value="steam"),
            Choice(title="Steam Patch", value="steampatch"),
            Choice(title="Emotion Creators", value="ec"),
            Choice(title="Sunshine", value="sunshine")
        ]
    ).ask()
    vanilla = questionary.confirm("Vanilla Only?").ask()
    orderby = questionary.select(
        "Orderby?",
        choices=[
            Choice(title="Popularity", value="popularity"),
            Choice(title="Uploaded Time (asc)", value="dateasc"),
            Choice(title="Uploaded Time (desc)", value="")
        ]
    ).ask()
    hidden = questionary.confirm("Show Hidden?").ask()
    featured = questionary.confirm("Best Only?").ask()
    return name, tag, gender, personality, type, vanilla, orderby, hidden, featured

def make_logger(name):
    logger = getLogger(name)
    logger.setLevel(DEBUG)

    st_handler = StreamHandler()
    st_handler.setLevel(INFO)
    st_handler.setFormatter(Formatter("[{levelname}] {message}", style="{"))
    logger.addHandler(st_handler)

    fl_handler = FileHandler(filename=".log", encoding="utf-8", mode="w")
    fl_handler.setLevel(DEBUG)
    fl_handler.setFormatter(
        Formatter(
            "[{levelname}] {asctime} [{filename}:{lineno}] {message}", style="{"
        )
    )
    logger.addHandler(fl_handler)

    return logger


if __name__ == "__main__":
    logger = make_logger(__name__)
    logger.info("BepisDB Downloader started...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists("./cards"):
        logger.error("cards directory is not.")
        os.mkdir("./cards")
        os.mkdir("./cards/Koikatsu")
        logger.info("cards directory created.")
    name, tag, gender, personality, type, vanilla, orderby, hidden, featured = ask()
    cards = search(name, tag, gender, personality, type, vanilla, orderby, hidden, featured)
    logger.info("Download Started.")
    for card in cards:
        download(card)
        time.sleep(1)
    logger.info("Download Complete.")
