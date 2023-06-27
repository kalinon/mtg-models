# Download Data
import json
import numpy as np
import func


def download_data():
    import requests
    import json

    bulk_data_endpoint = 'https://api.scryfall.com/bulk-data'
    oracle_cards_file = 'oracle_cards.json'

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


def fetch_cards():
    import pandas as pd
    import json
    import requests

    with open('./oracle_cards.json', 'rt', encoding='utf-8') as f:
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

        print(card["id"] + " - " + card["name"])
        response = requests.get(
            "http://192.168.7.23:32079/api/v1/scryfall_card/" + card["id"])
        # response = requests.get("http://mtg-helper-api-ro.mtg-helper/api/v1/scryfall_card/" + card["id"])
        if response.status_code == 200:
            data = json.loads(response.text)
            cards.append(data)

    print(f'total cards: {len(cards)}')

    with open(f'./cards.json', 'w') as f:
        json.dump(cards, f)


def preprocess(load_data_path: str, preprocess_data_path: str):
    import pandas as pd
    import pickle

    array_columns = [
        'games',

        # Types
        'subtypes',
        'supertypes',
        'types',

        # DFC Types
        'face_type',
        'face_subtype',
        'back_type',
        'back_subtype',

        # Physical
        'finishes',
        'frame_effects',
        'promo_types',

        # Colors
        'colors',
        'color_identity',

        # Abilities
        'keywords',
        'produced_mana',
    ]

    # loading the train data
    with open('./cards.json', 'rt', encoding='utf-8') as f:
        json_data = json.load(f)

    set_df = pd.json_normalize(json_data)

    # Drop columns that contain 'uri'
    func.drop_columns(set_df, set_df.filter(regex='uri').columns)
    # Drop columns that end with '_id'
    func.drop_columns(set_df, set_df.filter(regex='_id$').columns)
    # Drop other columns
    func.drop_columns(set_df, ['multiverse_ids'])

    # Fill empty columns
    func.fill_empty_columns(set_df)

    set_df['dfc'] = set_df['card_faces'].apply(lambda x: len(x) > 0)

    # Parse double faced cards
    set_df = func.dfc(set_df)

    func.clean_oracle_text(set_df)
    func.check_array_columns(array_columns, set_df)
    func.mana_colors(set_df)
    func.card_meta(set_df)
    func.release_dates(set_df)
    func.price_buckets(set_df)

    # Tokenize Oracle Text
    set_df['oracle_tokens'] = set_df['oracle_text'].apply(
        lambda x: func.process_oracle(x))

    set_df = func.process_types(set_df)
    set_df = func.meta_types(set_df)

    # Keyword total
    set_df['keyword_count'] = set_df['keywords'].apply(lambda x: len(x))
    # Total keywords and meta types
    set_df['total_abilities'] = set_df['keyword_count'] + \
        set_df['meta_type_count']
    print(f"Shape of dataframe: {set_df.shape}")

    # Flatten arrays
    for column in array_columns:
        set_df = func.flatten_array(set_df, column, drop=True)

    # filter out basic lands
    set_df = set_df[set_df['supertypes.basic'] != 1]

    # Flatten oracle tokens and clean them
    set_df = func.flatten_array(set_df, 'oracle_tokens', prefix='tkn')
    func.clean_tokens(set_df)
    func.clean_types(set_df)
    print(f"Shape of dataframe: {set_df.shape}")

    # func.float_to_int(set_df)
    func.check_bool(set_df)
    set_df = func.encode_columns(set_df, [
        'power', 'toughness', 'loyalty',
        # 'cmc_grp',
        # 'border_color', 'layout', 'frame',
    ])
    set_df = func.encode_columns(
        set_df, func.df_columns(set_df, r"^legalities\."))
    set_df = func.encode_face_columns(set_df, [
        'power', 'toughness', 'loyalty',
    ])

    print(f"Final shape of dataframe: {set_df.shape}")
    with open('./cards.csv', 'wt', encoding='utf-8') as f:
        set_df.to_csv(f)


#     with open(f'{load_data_path}/df', 'wb') as f:
#         pickle.dump(set_df, f)
#
#     return (print('Done!'))

# download_data()
# fetch_cards()
# load_data('.', './tmp/output')
# preprocess('./tmp/output', './tmp/pre')

# preprocess_dfc('./tmp/output', './tmp/pre')
# preprocess_data('./tmp/output', './tmp/pre')
# preprocess_data2('./tmp/output', './tmp/pre')
