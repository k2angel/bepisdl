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


def search(type: str, payload: dict):
    # https://db.bepis.moe/koikatsu?name=i&tag=vtuber&gender=female&personality=0&type=base&vanilla=true&orderby=popularity&hidden=true&featured=true
    cards_ = []
    url = parse.urljoin("https://db.bepis.moe/", type)
    pattern = re.compile(r"/card/download/(\w+)_(\d+).\d+")
    for i in itertools.count():
        payload["page"] = str(i+1)
        res = requests.get(url, params=payload)
        soup = bs(res.text, "lxml")
        cards = soup.select("#inner-card-body > div > div")
        if not cards:
            logger.info(f"page: {i}, card: {len(cards)}")
            break
        # page_active = soup.select_one("li[class='page-item active']")
        # page_end = soup.select_one("li[class=")
        for card in cards:
            card_title = card.select_one("span").get_text(strip=True)
            card_url = card.select_one("a[class='btn btn-primary btn-sm']").get("href")
            card_type, card_id = pattern.match(card_url).groups()
            card_ = {
                "title": card_title,
                "url": card_url,
                "type": card_type,
                "id": int(card_id)
            }
            cards_.append(card_)
        time.sleep(1)
    return cards_

def count(type, id):
    payload = {
        "cardType": type,
        "cardId": id
    }
    requests.post("https://db.bepis.moe/card/count", data=payload)

def download(card):
    if card["type"] == "KK":
        count(card["type"], card["id"])
        time.sleep(1)
    url = parse.urljoin("https://db.bepis.moe", card["url"])
    name = os.path.basename(url)
    dir = os.path.join("./cards", card["type"])
    if not os.path.exists(dir):
        os.mkdir(dir)
    path = os.path.join(dir, name)
    if not os.path.exists(path):
        res = requests.get(url, stream=True)
        if res.status_code == 200:
            with open(path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024):
                    f.write(chunk)
        logger.info(f"Downloaded. Title: {card['title']}, URL: {card['url']}")

def ask():
    # https://db.bepis.moe/kkscenes?femalecount=2%2C&malecount=5%2C&vanilla=true&timeline=yes&hidden=true&featured=true
    type = questionary.select(
        "Type?",
        choices=[
            Choice(title="Card", value="koikatsu"),
            Choice(title="Scene", value="kkscenes"),
            Choice(title="Clothing", value="kkclothing")
        ]
    ).ask()
    name = questionary.text("Name?").ask()
    tag = questionary.text("Tag?").ask()
    hidden = questionary.confirm("Show Hidden?").ask()
    featured = questionary.confirm("Best Only?").ask()
    orderby = questionary.select(
        "Orderby?",
        choices=[
            Choice(title="Popularity", value="popularity"),
            Choice(title="Uploaded Time (asc)", value="dateasc"),
            Choice(title="Uploaded Time (desc)", value="")
        ]
    ).ask()
    query = {
            "name": name,
            "tag": tag,
            "orderby": orderby,
            "hidden": str(hidden).lower(),
            "featured": str(featured).lower(),
        }
    if type != "kkclothing":
        vanilla = questionary.confirm("Vanilla Only?").ask()
        query["vanilla"] = str(vanilla).lower()
        if type == "koikatsu":
            gender = questionary.select(
                "Sex?",
                choices=[
                    Choice(title="ALL", value=""),
                    Choice(title="Female", value="female"),
                    Choice(title="Male", value="male")
                ]
            ).ask()
            personality = ""
            game = questionary.select(
                "Game?",
                choices=[
                    Choice(title="ALL", value=""),
                    Choice(title="Base", value="base"),
                    Choice(title="Steam", value="steam"),
                    Choice(title="Steam R-18 Patch", value="steampatch"),
                    Choice(title="Emotion Creators", value="ec"),
                    Choice(title="Sunshine", value="sunshine")
                ]
            ).ask()
            query["gender"] = gender
            query["personality"] = personality
            query["type"] = game
        else:
            # https://db.bepis.moe/kkscenes?femalecount=2%2C&malecount=5%2C&vanilla=true&timeline=yes&hidden=true&featured=true
            femalecount = None
            malecount = None
            timeline = questionary.select(
                "Contains an animation timeline?",
                choices=[
                    Choice(title="ALL", value=""),
                    Choice(title="Yes", value="yes"),
                    Choice(title="No", value="no")
                ]
            ).ask()
            query["timeline"] = timeline
    return type, query

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
        logger.info("cards directory created.")
    type, payload = ask()
    cards = search(type, payload)
    logger.info("Download Started.")
    for card in cards:
        download(card)
        time.sleep(1)
    logger.info("Download Complete.")
