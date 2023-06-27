# Download Data
import json
import numpy as np
import python.func as func


def download_data(data_dir: str = "./data"):
    import requests
    import json

    bulk_data_endpoint = 'https://api.scryfall.com/bulk-data'
    oracle_cards_file = data_dir + '/oracle_cards.json'

    response = requests.get(bulk_data_endpoint)
    if response.status_code == 200:
        data = json.loads(response.text)
        for item in data['data']:
            if item['type'] == 'oracle_cards':
                download_uri = item['download_uri']
                break
        else:
            print("Oracle cards not found")
            exit()

        with requests.get(download_uri, stream=True) as r:
            r.raise_for_status()
            with open(oracle_cards_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"Oracle cards file downloaded as {oracle_cards_file}")
    else:
        print(f"Error: {response.status_code}")


def fetch_cards(data_dir: str = "./data"):
    import pandas as pd
    import json
    import requests

    oracle_cards_file = data_dir + '/oracle_cards.json'
    cards_data_file = data_dir + '/cards.json'

    with open(oracle_cards_file, 'rt', encoding='utf-8') as f:
        json_data = json.load(f)

    cards = []
    for card in json_data:
        released = pd.to_datetime(card['released_at'])
        if released.year < 2004:
            continue
        if card['type_line'] == "Card // Card" or card["type_line"] == "Card" or 'Token' in card['type_line']:
            continue
        if card['name'] == 'Smelt // Herd // Saw':
            continue

        # # filter out set_codes UGL, UNH, UST, UND, UNF
        # if card['set_code'] in ['ugl', 'unh', 'ust', 'und', 'unf']:
        #     continue

        # print(card["id"] + " - " + card["name"])
        response = requests.get(
            "http://192.168.7.23:32079/api/v1/scryfall_card/" + card["id"])
        # response = requests.get("http://mtg-helper-api-ro.mtg-helper/api/v1/scryfall_card/" + card["id"])
        if response.status_code == 200:
            data = json.loads(response.text)
            cards.append(data)

    print(f'total cards: {len(cards)}')

    with open(cards_data_file, 'w') as f:
        json.dump(cards, f)


def preprocess_data(load_data_path: str = './data', output_file: str = 'cards.csv'):
    import pandas as pd
    import pickle

    # loading the train data
    with open(f'{load_data_path}/cards.json', 'rt', encoding='utf-8') as f:
        json_data = json.load(f)

    set_df = func.process_data(json_data)

    with open(f'{load_data_path}/{output_file}', 'wt', encoding='utf-8') as f:
        set_df.to_csv(f)

    with open(f'{load_data_path}/df', 'wb') as f:
        pickle.dump(set_df, f)

    return print('Done!')
