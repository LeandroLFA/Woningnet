import requests
import json
import logging
import urllib.parse
from pathlib import Path
import config

API_URL = (
    'https://amsterdam.mijndak.nl/screenservices/DAKWP/Overzicht/WoningOverzicht/'
    'DataActionHaalPassendAanbod'
)
PAGE_URL = getattr(config, 'PAGE_URL', 'https://amsterdam.mijndak.nl/')
PAYLOAD_PATH = Path(__file__).parent / 'payload.json'

def load_payload() -> dict:
    if not PAYLOAD_PATH.exists():
        logging.warning(f"payload.json niet gevonden op {PAYLOAD_PATH}")
        return {}
    try:
        raw = PAYLOAD_PATH.read_text(encoding='utf-8')
        data = json.loads(raw)
        return json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        logging.error(f"Fout bij inladen payload.json: {e}")
        return {}

def unify_item(item: dict) -> dict:
    photo = item.get('Foto_Locatie')
    cl = item.get('Cluster') or {}
    pub_cluster = cl.get('PublicatieId')
    if pub_cluster and str(pub_cluster) != '0':
        cid = str(pub_cluster)
        price_min = float(cl.get('PrijsMin') or 0)
        price_max = float(cl.get('PrijsMax') or 0)
        opp_min = float(cl.get('WoonVertrekkenTotOppMin') or 0)
        opp_max = float(cl.get('WoonVertrekkenTotOppMax') or 0)
        rooms_min = int(cl.get('AantalKamersMin') or 0)
        rooms_max = int(cl.get('AantalKamersMax') or 0)
        adres = cl.get('Naam', '')
        huur = price_min if price_min == price_max else f"{price_min}-{price_max}"
        opp = opp_min if opp_min == opp_max else f"{opp_min}-{opp_max}"
        kamers = rooms_min if rooms_min == rooms_max else f"{rooms_min}-{rooms_max}"
        return {
            'PublicatieId': cid,
            'id': cid,
            'type': 'cluster',
            'Adres': adres,
            'Huur': huur,
            'Oppervlakte': opp,
            'Kamers': kamers,
            'detail_url': f"{PAGE_URL}?EntiteitId={cid}",
            'photo': photo,
            'raw': item
        }
    eu = item.get('Eenheid') or {}
    ad = item.get('Adres') or {}
    uid = str(eu.get('EntiteitId') or item.get('Id') or '')
    price = float(eu.get('NettoHuur') or 0)
    opp_val = float(eu.get('WoonVertrekkenTotOpp') or 0)
    rooms = int(eu.get('AantalKamers') or 0)
    adres = f"{ad.get('Straatnaam','').strip()} {ad.get('Huisnummer','')}".strip()
    return {
        'PublicatieId': uid,
        'id': uid,
        'type': 'unit',
        'Adres': adres,
        'Huur': price,
        'Oppervlakte': opp_val,
        'Kamers': rooms,
        'detail_url': f"{PAGE_URL}?EntiteitId={uid}",
        'photo': photo,
        'raw': item
    }

def fetch_aanbod(get_session_cookies) -> list:
    payload = load_payload()
    session = requests.Session()
    cookies = get_session_cookies() or {}
    for k, v in cookies.items():
        session.cookies.set(k, v)
    nr2 = cookies.get('nr2Users', '')
    decoded = urllib.parse.unquote(nr2)
    crf = next((p.split('crf=')[-1] for p in decoded.split(';') if p.strip().startswith('crf=')), None)
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json; charset=UTF-8',
        'x-csrftoken': crf,
        'referer': PAGE_URL,
        'origin': 'https://amsterdam.mijndak.nl'
    }
    try:
        resp = session.post(API_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Fout fetching aanbod: {e}")
        return []
    data = resp.json()
    raw_list = data.get('data', {}).get('PublicatieLijst', {}).get('List', [])
    return [unify_item(it) for it in raw_list if isinstance(it, dict)]

def filter_geschikt(items: list) -> list:
    geschikt = []
    for w in items:
        if w['type'] == 'unit':
            if not (config.MIN_HUUR <= w['Huur'] <= config.MAX_HUUR and
                    w['Oppervlakte'] >= config.MIN_OPPERVLAKTE and
                    config.MIN_KAMERS <= w['Kamers'] <= config.MAX_KAMERS):
                continue
        else:
            if '-' in str(w['Huur']):
                min_h, max_h = map(float, w['Huur'].split('-'))
            else:
                min_h = max_h = float(w['Huur'])
            if max_h < config.MIN_HUUR or min_h > config.MAX_HUUR:
                continue
        geschikt.append(w)
    return geschikt


