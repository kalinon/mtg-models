import pandas as pd
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import TweetTokenizer
import numpy as np
from pandas import DataFrame
import python.checks as checks

card_types = [
    # Types
    'subtypes',
    'supertypes',
    'types',

    # DFC Types
    'face_type',
    'face_subtype',
    'back_type',
    'back_subtype',
]

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

def process_data(json_data):
    set_df = pd.json_normalize(json_data)

    # Exclude Unsets
    unsets = ['ugl', 'unh', 'ust', 'und', 'unf']
    set_df = set_df[~set_df['set_code'].isin(unsets)]

    # Drop columns that contain 'uri'
    drop_columns(set_df, set_df.filter(regex='uri').columns)
    # Drop columns that end with '_id'
    drop_columns(set_df, set_df.filter(regex='_id$').columns)
    # Drop other columns
    drop_columns(set_df, ['multiverse_ids'])

    # Fill empty columns
    fill_empty_columns(set_df)

    set_df['dfc'] = set_df['card_faces'].apply(lambda x: len(x) > 0)

    # Parse double faced cards
    set_df = dfc(set_df)

    clean_keywords(set_df)
    clean_oracle_text(set_df)
    check_array_columns(array_columns, set_df)
    mana_colors(set_df)
    card_meta(set_df)
    release_dates(set_df)
    price_buckets(set_df)
    multiclass(set_df)

    # Tokenize Oracle Text
    set_df['oracle_tokens'] = set_df['oracle_text'].apply(
        lambda x: process_oracle(x))

    set_df = process_types(set_df)
    set_df = meta_types(set_df)

    # Keyword total
    set_df['keyword_count'] = set_df['keywords'].apply(lambda x: len(x))
    # Total keywords and meta types
    set_df['total_abilities'] = set_df['keyword_count'] + \
                                set_df['meta_type_count']

    print_stats(set_df)

    # Flatten arrays
    print("Flattening Arrays")
    for column in array_columns:
        set_df = flatten_array(set_df, column, drop=True)

    # filter out basic lands
    set_df = set_df[set_df['supertypes.basic'] != 1]

    # Flatten oracle tokens and clean them
    set_df = flatten_array(set_df, 'oracle_tokens', prefix='tkn')
    clean_tokens(set_df)
    clean_types(set_df)

    print_stats(set_df)

    # float_to_int(set_df)
    check_bool(set_df)
    set_df = encode_columns(set_df, [
        'power', 'toughness', 'loyalty',
        # 'cmc_grp',
        # 'border_color', 'layout', 'frame',
    ])
    bool_to_int(set_df)

    set_df = encode_columns(
        set_df, df_columns(set_df, r"^legalities\."))
    set_df = encode_face_columns(set_df, [
        'power', 'toughness', 'loyalty',
    ])

    print(f"Final shape of dataframe: {set_df.shape}")
    return set_df


def flatten_array(data: DataFrame, key: str, prefix=None, drop=False):
    print(f'  - Flattening {key}...')

    # "Explode" the lists into separate rows
    df_exploded = data[['name', key]].explode(key)
    # Get dummies and sum them groupwise
    df_dummies = pd.get_dummies(df_exploded[key]).groupby(level=0).any().astype(int)
    if prefix is None:
        prefix = key
    # Prefix column names to differentiate them
    df_dummies.columns = f'{prefix}.' + df_dummies.columns
    # Join back with the original DataFrame
    tmp = data.join(df_dummies)
    if drop:
        tmp = tmp.drop(columns=key)
    return tmp


def drop_columns(data, cols):
    # Drop these columns
    return data.drop(cols, axis=1, inplace=True)


def check_array_columns(columns, data):
    for column in columns:
        # Create a mask where each value is True if the 'colors' value is NaN or None and False otherwise
        mask = data[column].isnull()
        # Use this mask to assign an empty list to the 'colors' values where the mask is True
        data.loc[mask, column] = data.loc[mask, column].apply(lambda x: [])


# Transform the data in double faced cards
def dfc(data):
    # Let's first create a dataframe that just has the card name and the column 'card_faces'
    double_cards_df = data[['name', 'card_faces', 'dfc']].dropna()
    # We also filter it, so we get cards that actually have 2 sides
    double_cards_df = double_cards_df[double_cards_df['card_faces'].apply(len) == 2]

    # If we actually have information about the 2 faces, we separate them into 2 columns
    double_cards_df[['face1', 'face2']] = pd.DataFrame(
        double_cards_df['card_faces'].tolist(),
        index=double_cards_df.index
    )

    # Now let's drop the column 'card_faces'
    double_cards_df.drop(columns=["card_faces", 'dfc'], axis=1, inplace=True)

    # We now go into each key within the dictionary of face1 and face2 and separate them into columns
    double_cards_df[double_cards_df['face1'].apply(pd.Series).columns + "_1"] = double_cards_df['face1'].apply(
        pd.Series)
    double_cards_df[double_cards_df['face2'].apply(pd.Series).columns + "_2"] = double_cards_df['face2'].apply(
        pd.Series)

    # Define a list of columns we want to keep from the 2 sided cards
    cols_to_keep = [
        'name', 'cmc',
        'oracle_text_1', 'oracle_text_2',
        # 'image_uris_1', 'image_uris_2',
        'colors_1', 'colors_2',
        'power_1', 'power_2',
        'toughness_1', 'toughness_2',
        'loyalty_1', 'loyalty_2'
    ]

    # For each column in the dataframe, if it's not a selected column, we drop it
    for i in double_cards_df.columns:
        if i not in cols_to_keep:
            double_cards_df.drop(i, axis=1, inplace=True)

    # We now need to consolidate the 2 oracle texts into 1, we join them together
    double_cards_df['oracle_text_dobles'] = double_cards_df['oracle_text_1'] + "\n" + double_cards_df[
        'oracle_text_2']

    # Reset the indexes
    double_cards_df = double_cards_df.reset_index(drop=True)

    # We now merge them by card name
    data = data.merge(
        double_cards_df,
        on=["name"], how="left"
    ).drop("card_faces", axis=1)

    # Now that we have our oracle text from the 2 card sides joined together, we want to use it to replace
    # the actual "oracle_text" from the original dataframe, which is actually empty

    # If oracle_text is empty (meaning it's a double faced card), we replace it with our 'oracle_text_dobles' column
    data['oracle_text'] = np.where(
        data['oracle_text'] == "",
        data['oracle_text_dobles'],
        data['oracle_text']
    )

    # And now that column is useless so we drop it
    data = data.drop("oracle_text_dobles", axis=1)

    # We also want to update any columns that are empty with the values from the _1 columns
    for i in data.columns:
        if i.endswith("_1"):
            col = i.replace("_1", "")
            data[col] = np.where(
                data[col].isna(),
                data[i],
                data[col]
            )

    # We also want to update any colors if empty with the values from the colors_1 column
    data["colors"] = np.where(
        data["colors"].apply(len) == 0,
        data["colors_1"],
        data["colors"]
    )

    # We first separate the card type of the front from the card type of the back
    data[['face', 'back']] = data['type_line'].str.split(' // ', n=1, expand=True)

    # We then separate the face type using the "-" as separator
    data[['face_type', 'face_subtype']] = data['face'].str.split(' — ', expand=True)

    # We then separate the back type using the "-" as separator
    data[['back_type', 'back_subtype']] = data['back'].str.split(' — ', expand=True)

    # We now lowercase the strings and split them into lists
    for i in ['face_type', 'face_subtype', 'back_type', 'back_subtype']:
        data[i] = data[i].str.lower()
        data[i] = data[i].str.split(' ')

    return data


def fill_empty_columns(data):
    # Fill any oracle_text that is null with an empty string
    data['oracle_text'].fillna('', inplace=True)
    # If a card does not have a flavor text, let's put "no flavor text" instead
    data['flavor_text'] = data['flavor_text'].fillna("no_flavor_text").astype(str)
    # If a card does not have an edhrec_rank, let's replace it with int 999999
    data['edhrec_rank'] = np.where(data['edhrec_rank'] == 0, 999999, data['edhrec_rank'])


def fix_cleave(data):
    # data['keywords.cleave'] = np.where(data['oracle_text'].str.contains('Cleave'), 1, 0)
    data['oracle_text'] = np.where(
        # data['keywords.cleave'] == 1,
        'cleave' in data['keywords'],
        data['oracle_text'].str.replace(
            "[", "", regex=False
        ).str.replace(
            "]", "", regex=False
        ) + '\n' + data['oracle_text'].str.replace(
            r"[\(\[].*?[\)\]] ", "", regex=True
        ),
        data['oracle_text']
    )


def replace_card_names(row):
    # Split the card name into parts
    name_parts = row['name'].split(' // ')

    # Replace each part in the oracle text
    for part in name_parts:
        row['oracle_text'] = row['oracle_text'].replace(part, "CARDNAME")

    return row['oracle_text']


def clean_oracle_text(data):
    # Fill any oracle_text that is null with an empty string
    data['oracle_text'].fillna('', inplace=True)
    # Text `(to be removed)`
    # Remove text between brackets in oracle_text
    data['oracle_text'] = data['oracle_text'].str.replace(r"\(.*\)", "", regex=True)
    fix_cleave(data)
    # Replace the card name in the 'oracle_text' column with "CARDNAME"
    data['oracle_text'] = data.apply(replace_card_names, axis=1)
    # Replace ’ with '
    data['oracle_text'] = data['oracle_text'].str.replace(r"’", "'", regex=True)


def mana_colors(data):
    data['colorless'] = np.where(data['colors'].apply(len) == 0, True, False)

    # Monocolored, Multicolored and others

    # If color column has just 1 character, it's monocolored (eg. "B" or "W")
    data['monocolored'] = np.where(data['colors'].apply(len) == 1, 1, 0)

    # If it has more than 1 character and it does not say Colorless, then it's multicolored
    data['multicolored'] = np.where(data['colors'].apply(len) > 1, 1, 0)

    # And these other variants
    data['two_colors'] = np.where(data['colors'].apply(len) == 2, 1, 0)
    data['three_colors'] = np.where(data['colors'].apply(len) == 3, 1, 0)
    data['four_colors'] = np.where(data['colors'].apply(len) == 4, 1, 0)
    data['five_colors'] = np.where(data['colors'].apply(len) == 5, 1, 0)

    # We count how many mana symbols we find in a card CMC
    data['mana_symbols_cost'] = data['mana_cost'].str.count('W|U|B|R|G').fillna(0)

    # We also count how many specific mana symbols
    data['devotion.W'] = data['mana_cost'].str.count('W').fillna(0)
    data['devotion.U'] = data['mana_cost'].str.count('U').fillna(0)
    data['devotion.B'] = data['mana_cost'].str.count('B').fillna(0)
    data['devotion.R'] = data['mana_cost'].str.count('R').fillna(0)
    data['devotion.G'] = data['mana_cost'].str.count('G').fillna(0)

    # Create a column that is 1 if it's a card with X in its mana cost
    data['X_spell'] = np.where(data['mana_cost'].str.contains('{X}'), 1, 0)

    # Create groupings for the cmc. For 7 or above, we group them together
    data['cmc_grp'] = np.where(
        data['cmc'] <= 6.0,
        (data['cmc'].astype('int').astype('str')) + "_drop",
        "7plus_drop"
    )

    # Mana symbols in oracle text

    # We create a column tha that is 1 if there are mana symbols inside the oracle text
    data['mana_symbols_oracle'] = np.where(data['oracle_text'].str.contains('{W}|{U}|{B}|{R}|{G}'), 1, 0)

    # We count how many mana symbols are in the oracle text
    data['mana_symbols_oracle_nbr'] = data['oracle_text'].str.count('{W}|{U}|{B}|{R}|{G}')


def card_meta(data):
    # Includes tapping ability
    # We create a column that is 1 if the card has {T} in the oracle_text
    data['meta.tapping_ability'] = np.where(data['oracle_text'].str.contains('{T}'), 1, 0)
    # Includes multiple choice
    # We create a column that is 1 if the card has '• ' in the oracle_text
    data['meta.multiple_choice'] = np.where(data['oracle_text'].str.contains('• '), 1, 0)


# Define a function that takes the oracle text, removes undesired characters, stopwords and tokenizes it
def process_oracle(oracle):
    """Process oracle function.
      Input:
          oracle: a string containing an oracle
      Output:
          oracle_clean: a list of words containing the processed oracle
      """
    import string
    stemmer = PorterStemmer()
    stopwords_english = stopwords.words('english')

    oracle = re.sub(r'\$\w*', '', oracle)
    oracle = re.sub(r'^RT\s+', '', oracle)
    oracle = re.sub(r'#', '', oracle)
    oracle = re.sub(r"\d+", '', oracle)

    # tokenize tweets
    tokenizer = TweetTokenizer(
        preserve_case=False,
        strip_handles=True,
        reduce_len=True,
    )
    oracle_tokens = tokenizer.tokenize(oracle)

    oracle_clean = []
    for word in oracle_tokens:
        if (word not in stopwords_english and  # remove stopwords
                word not in string.punctuation):  # remove punctuation

            # oracle_clean.append(word)
            stem_word = stemmer.stem(word)  # stemming word
            oracle_clean.append(stem_word)

    # Remove tokens that are just numbers, symbols or artifacts
    remove_tokens = ['iii', 'None', '•', 'x', 'c', 'r', '−', 'g', 'iv', '}:',
                     'eight', 'nine', 'ten', '—', 'ii', 'u', 'b', 'w', 'p',
                     '.', '..', '...', '. . .', '___', ']:']
    oracle_clean = [word for word in oracle_clean if word not in remove_tokens]

    return oracle_clean


# Merge all types into one column
def process_types(data: DataFrame):
    """Process types function.
      Input:
          data: a DataFrame containing the data
      Output:
          data: a DataFrame containing the data with the types merged
      """

    # create a subset of the data with only the columns we need
    data_types = data[['name'] + card_types].dropna()

    # Create a column that is a list of all the types
    data_types['all_types'] = data_types[card_types].values.tolist()
    # flatten the list
    data_types['all_types'] = data_types['all_types'].apply(lambda x: [item for sublist in x for item in sublist])
    # remove duplicates
    data_types['all_types'] = data_types['all_types'].apply(lambda x: list(set(x)))

    drop_columns(data_types, card_types)
    data = data.merge(data_types, on='name', how='left')

    return data


def meta_types(data: DataFrame):
    set_df_kw = data[['name', 'oracle_text', 'all_types', 'meta.tapping_ability', 'keywords',
                      'power', 'toughness']].dropna()

    for k in checks.check_list.keys():
        set_df_kw[k] = set_df_kw.apply(checks.check_list[k], axis=1)

    drop_columns(set_df_kw, ['oracle_text', 'all_types', 'meta.tapping_ability',
                             'keywords', 'power', 'toughness'])

    # Create a column that sums them for each card
    set_df_kw['meta_type_count'] = set_df_kw[checks.check_list.keys()].sum(axis=1)

    # Merge the meta types with the main data
    data = data.merge(set_df_kw, on='name', how='left')

    meta_columns = list(checks.check_list.keys())

    # Populate empty values with False
    data[meta_columns] = np.where(
        data[meta_columns].isna(),
        False,
        data[meta_columns]
    )
    data[meta_columns] = data[meta_columns].astype(bool)

    return data


def price_buckets(data: DataFrame):
    price_cols = [
        'prices.usd',
        'prices.usd_foil',
        'prices.usd_etched',
        'prices.eur',
        'prices.eur_foil',
        'prices.tix',
    ]
    data[price_cols] = np.where(
        data[price_cols].isna(),
        -1.00,
        data[price_cols]
    )
    data[price_cols] = data[price_cols].astype(float)

    # Create 5 categories
    price_labels = ['bronze', 'silver', 'gold', 'platinum', 'diamond']

    # Define the cuts of each category
    usd_bins = [-1.00, 0.25, 1.00, 5.00, 10.00, 1000.00]
    eur_bins = [-1.00, 0.25, 1.00, 5.00, 10.00, 1000.00]
    tix_bins = [-1.00, 0.02, 0.05, 0.5, 1.00, 1000.00]

    # Apply them to the price columns
    data['binusd'] = pd.cut(data['prices.usd'].astype(float), bins=usd_bins, labels=price_labels)
    data['bineur'] = pd.cut(data['prices.eur'].astype(float), bins=eur_bins, labels=price_labels)
    data['bintix'] = pd.cut(data['prices.tix'].astype(float), bins=tix_bins, labels=price_labels)

    # Convert the categorical columns to string
    data['binusd'] = data['binusd'].astype(str)
    data['bineur'] = data['bineur'].astype(str)
    data['bintix'] = data['bintix'].astype(str)

    return data


def release_dates(data: DataFrame):
    # Convert the column to datetime
    data['released_at'] = pd.to_datetime(data['released_at'])

    # Extract year and month numbers
    data['year'] = pd.DatetimeIndex(data['released_at']).year.astype('str')
    data['month'] = pd.DatetimeIndex(data['released_at']).month.astype('str')


def clean_keywords(data: DataFrame):
    # replace special characters in keywords array with _
    data['keywords'] = data['keywords'].apply(lambda x: [re.sub('[^A-Za-z0-9]+', '_', i) for i in x])


def clean_tokens(data: DataFrame):
    # Create a df to count occurrence of each type column and filter out any that has lower than 0 occurrences
    print(f"Clean Tokens")
    # Get a list of all the type columns
    tkn_col_list = []

    for e in list(data.columns):
        for element in e.split():
            if element.startswith("tkn."):
                tkn_col_list.append(element)

    print(f"  Token Columns Length: {len(tkn_col_list)}")

    # Create a df to count occurrence of each token column and filter out any that has lower than 3 occurrences
    count_tkn_df = pd.DataFrame(data[tkn_col_list].sum().sort_values(ascending=False))
    count_tkn_df.columns = ['count_tkns']
    count_tkn_df['tkn_column'] = count_tkn_df.index
    count_tkn_df = count_tkn_df.reset_index(drop=True)
    count_tkn_df = count_tkn_df[['tkn_column', 'count_tkns']]
    count_tkn_df = count_tkn_df.query("count_tkns >= 3")

    # Get a list of the ones that we will keep
    tkn_cols_to_keep = list(count_tkn_df['tkn_column'].unique())

    # Use the list to get another list of the columns we will want to REMOVE
    tkn_cols_to_drop = list(set(tkn_col_list) - set(tkn_cols_to_keep))

    print(f"  Number of token columns to remove: {len(tkn_cols_to_drop)}")
    return drop_columns(data, tkn_cols_to_drop)


def clean_types(data: DataFrame):
    print(f"Clean Types")
    # Get a list of all the type columns
    type_col_list = []

    for e in list(data.columns):
        for t in card_types:
            for element in e.split():
                if element.startswith(f"{t}."):
                    # print(element)
                    type_col_list.append(element)

    print(f"  Type Columns Length: {len(type_col_list)}")

    # Create a df to count occurrence of each type column and filter out any that has lower than 0 occurrences
    count_type_df = pd.DataFrame(data[type_col_list].sum().sort_values(ascending=False))
    count_type_df.columns = ['count_type']
    count_type_df['type_column'] = count_type_df.index
    count_type_df = count_type_df.reset_index(drop=True)
    count_type_df = count_type_df[['type_column', 'count_type']]
    count_type_df = count_type_df.query("count_type >= 0")

    # Get a list of the ones that we will keep
    type_cols_to_keep = list(count_type_df['type_column'].unique())

    # Use the list to get another list of the columns we will want to REMOVE
    type_cols_to_drop = list(set(type_col_list) - set(type_cols_to_keep))

    print(f"  Number of type columns to remove: {len(type_cols_to_drop)}")
    if len(type_cols_to_drop) > 0:
        drop_columns(data, type_col_list)
    return data


def float_to_int(data: DataFrame):
    # Convert float columns to int
    float_cols = data.select_dtypes(include=[float]).columns
    print(f"Number of float columns: {len(float_cols)}")
    data[float_cols] = np.where(
        data[float_cols].isna(),
        -1.00,
        data[float_cols]
    )
    data[float_cols] = data[float_cols].astype(int)


def bool_to_int(data: DataFrame):
    # Convert bool columns to int
    bool_cols = data.select_dtypes(include=[bool]).columns
    print(f"Number of bool columns: {len(bool_cols)}")
    data[bool_cols] = np.where(
        data[bool_cols].isna(),
        False,
        data[bool_cols]
    )
    data[bool_cols] = data[bool_cols].astype(int)


# Set missing values to False
def check_bool(data: DataFrame):
    bool_cols = data.select_dtypes(include=[bool]).columns
    print(f"Number of bool columns: {len(bool_cols)}")
    data[bool_cols] = np.where(
        data[bool_cols].isna(),
        False,
        data[bool_cols]
    )


def encode_columns(data: DataFrame, columns: list, drop: bool = True):
    for col in columns:
        # Get one hot encoding of columns B
        one_hot = pd.get_dummies(data[col])
        # Add the column name to each new encoded column
        one_hot.columns = f'{col}.' + one_hot.columns
        # Drop original column as it is now encoded
        if drop:
            data.drop(col, axis=1, inplace=True)
        # Join the encoded df
        data = data.join(one_hot)

    return data


def encode_face_columns(data: DataFrame, columns: list):
    for col in columns:
        for i in [1, 2]:
            face_col = f"{col}_{i}"
            # Get one hot encoding of columns B
            one_hot = pd.get_dummies(data[face_col])
            # Add the column name to each new encoded column
            one_hot.columns = f'{col}.' + one_hot.columns
            data[one_hot.columns] = np.where(
                data[one_hot.columns] == 0,
                one_hot[one_hot.columns],
                data[one_hot.columns]
            )
            data.drop(face_col, axis=1, inplace=True)

    return data


def df_columns(data: DataFrame, regex):
    col_list = []
    for e in list(data.columns):
        for element in e.split():
            if re.match(regex, element):
                col_list.append(element)
    return list(col_list)


def multiclass(data: DataFrame):
    data['multiclass.colrs'] = data['colors'].apply(lambda x: ''.join(x))
    # set multiclass.colrs to C if colorless is true
    data['multiclass.colrs'] = np.where(
        data['colorless'] is True,
        'C',
        data['multiclass.colrs']
    )

    data['multiclass.rarty'] = data['rarity']
    data['multiclass.binusd'] = data['binusd']
    data['multiclass.bineur'] = data['bineur']
    data['multiclass.bintix'] = data['bintix']


def print_total_type_cols(data: DataFrame):
    count = 0
    for e in list(data.columns):
        for t in card_types:
            for element in e.split():
                if element.startswith(f"{t}."):
                    count += 1
    print(f"Total type columns: {count}")


def print_stats(data: DataFrame):
    print("--------------------")
    print(f"Shape of dataframe: {data.shape}")
    print_total_type_cols(data)
    print("--------------------")
