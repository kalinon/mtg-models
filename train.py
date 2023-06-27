import pickle

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

from python.data_gen import preprocess_data, fetch_cards
from python.func import df_columns, card_types

# fetch_cards()
# preprocess_data()

# loading the train data
with open('data/df', 'rb') as f:
    df = pickle.load(f)


def train(data, target, columns):
    print("--------------------")
    print(f'Target: {target}')
    x = data[columns]
    y = data[target]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.5, random_state=42)
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    x_test = scaler.transform(x_test)
    model = LogisticRegression(
        max_iter=1000,
        # class_weight={0: 1, 1: 3}
    )
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    print('Accuracy:', accuracy_score(y_test, y_pred))
    print('Confusion Matrix:\n')

    matrix = confusion_matrix(y_test, y_pred)
    print(f'\tTrue negatives (actual = 0, predicted = 0): {matrix[0][0]}')
    print(f'\tFalse positives (actual = 0, predicted = 1): {matrix[0][1]}')
    print(f'\tFalse negatives (actual = 1, predicted = 0): {matrix[1][0]}')
    print(f'\tTrue positives (actual = 1, predicted = 1): {matrix[1][1]}\n')

    print('Classification Report:\n', classification_report(y_test, y_pred))


features = (df_columns(df, r'^(power|toughness|keywords|meta|tkn)\.') +
            df_columns(df, rf'^(sub|super)?types\.') +
            [
                'monocolored',
                'multicolored'
            ])

train(df, 'colors.W', features)
train(df, 'colors.U', features)
train(df, 'colors.B', features)
train(df, 'colors.R', features)
train(df, 'colors.G', features)
train(df, 'colorless', features)