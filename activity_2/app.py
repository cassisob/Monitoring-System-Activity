# IMPORTING NECESSARY LIBRARIES

from datetime import datetime, time
from flask import Flask, jsonify, render_template, request
import numpy as np
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
import pymsteams

from sklearn.discriminant_analysis import StandardScaler
from sklearn.neighbors import LocalOutlierFactor
from sklearn.linear_model import LinearRegression



# GLOBAL VARIABLES

app = Flask(__name__)

MODEL_LOF = LocalOutlierFactor(n_neighbors=20, contamination=0.02)

TRANSACTION_DATA = pd.DataFrame({'time': [], 'status': [], 'F1': []})
TRANSACTION_DATA['time'] = pd.to_datetime(TRANSACTION_DATA['time'])

ANOMALIES_DATA = pd.DataFrame({'time': [], 'status': [], 'F1': []})
ANOMALIES_DATA['time'] = pd.to_datetime(ANOMALIES_DATA['time'])

TEAMS_WEBHOOK = "YOUR_COMPANY_TEAMS_WEBHOOK"



# GENERAL FUNCTIONS

# CALCULATES TRENDS
def calculate_trend(statusType):

    half_hour_ago = TRANSACTION_DATA['time'].max() - pd.Timedelta(hours=0.3)
    data_to_analyze = TRANSACTION_DATA[TRANSACTION_DATA['time'] >= half_hour_ago]
    data_to_analyze = data_to_analyze[data_to_analyze['status'] == statusType][['time', 'F1']]

    if len(data_to_analyze) > 0:

        min_date = data_to_analyze['time'].min()
        data_to_analyze['x_seconds'] = (data_to_analyze['time'] - min_date).astype('timedelta64[s]').astype('int64')

        # Convertendo segundos para minutos
        data_to_analyze['x_minutes'] = data_to_analyze['x_seconds'] / 60
        
        # Preparando os dados para o modelo
        X = data_to_analyze[['x_minutes']].values
        y = data_to_analyze['F1'].values
        
        # Criando o modelo de regressão linear
        model = LinearRegression()

        # Obtendo o coeficiente angular (slope)
        slope = model.fit(X, y).coef_[0]
        
        # Classificando a tendência com base no coeficiente angular
        if slope > 0.4:
            return 2 # "Rising a lot"
        elif slope > 0.1:
            return 1 # "Rising"
        elif slope > -0.1 and slope < 0.1:
            return 0 # "Stable"
        elif slope > -0.4:
            return -1 # "Falling"
        else:
            return -2 # "Falling a lot"
        
    return 0


def is_anomalous_lof(new_data, model, X_train):
    # Normalizar os dados de treino
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Adicionar e normalizar o novo dado ao conjunto de dados de treinamento
    new_data_scaled = scaler.transform([[new_data['F1']]])
    X_new = np.vstack((X_train_scaled, new_data_scaled))
    
    # Ajustar o modelo com os novos dados e prever o outlier
    model.fit(X_new)
    lof_outlier_new = model.fit_predict(X_new)
    
    # Verificar se o novo dado é um outlier
    return lof_outlier_new[-1] == -1


def check_missing_zero_values():
    global TRANSACTION_DATA

    statuses = ['approved', 'processing', 'denied', 'backend_reversed', 'reversed', 'refunded', 'failed']

    # SINCE WE ARE SIMULATING THE DATA, WE CANNOT USE THE CURRENT DATETIME
    # five_minutes_ago = datetime.now() - pd.Timedelta(hours=1)
    one_minute_future = TRANSACTION_DATA['time'].max() + pd.Timedelta(minutes=1)
    future_data = pd.DataFrame({'time' : [one_minute_future] * 7, 'status': statuses, 'F1': [0] * 7})

    TRANSACTION_DATA = pd.concat([TRANSACTION_DATA, future_data]).reset_index().sort_values(by='time')


def send_teams_alert(status):
    teams = pymsteams.connectorcard(TEAMS_WEBHOOK)
    teams.title("TRANSACTION RISING A LOT NOTIFICATION")
    teams.summary("TRANSACTION RISING A LOT NOTIFICATION")

    transaction_status_section = pymsteams.cardsection()
    transaction_status_section.activityTitle("TRANSACTION STATUS")
    transaction_status_section.activityText(status)
    teams.addSection(transaction_status_section)

    five_minutes_ago = TRANSACTION_DATA['time'].max() - pd.Timedelta(hours=0.5)
    data = TRANSACTION_DATA[TRANSACTION_DATA['time'] >= five_minutes_ago]
    data = data[data['status'] == status][['F1']]

    event_time_section = pymsteams.cardsection()
    event_time_section.activityTitle("QUANTITY OF TRANSACTIONS: LAST FIVE MINUTES")
    event_time_section.activityText(str(data['F1'].sum()))
    teams.addSection(event_time_section)

    # UNCOMMENT THE LINE TO SEND THE MESSAGE
    # teams.send()

# FLASK ROUTES TO RUN THE APPLICATION

# MAIN ROUTE, TRANSACTIONS DASHBOARD
# METHOD (GET)  - SEND A DATAFRAME TO SIMULATE TRANSACTIONS, RUNS THE HTML PAGE
# METHOD (POST) - UPDATE THE DASHBOARD'S DATA
@app.route('/', methods=['GET', 'POST'])
def index():
    global ANOMALIES_DATA, TRANSACTION_DATA

    if request.method == 'GET':

        simulate_transactions = pd.read_csv('transactions_2.csv')

        today = datetime.now().date()

        def convert_to_datetime_str(time_str):
            time_str = time_str.replace("h ", ":")
            return f"{today} {time_str}:00"

        # Apply the function to the 'time' column
        simulate_transactions['time'] = simulate_transactions['time'].apply(convert_to_datetime_str)

        return render_template('index.html', simulate_transactions=simulate_transactions.to_json(orient=("records")))
    
    else:
        
        # SINCE WE ARE SIMULATING THE DATA, WE CANNOT USE THE CURRENT DATETIME
        # one_hour_ago = datetime.now() - pd.Timedelta(hours=1)
        one_hour_ago = TRANSACTION_DATA['time'].max() - pd.Timedelta(hours=1)
        half_hour_ago = TRANSACTION_DATA['time'].max() - pd.Timedelta(hours=0.5)

        last_transaction_hour_data =  TRANSACTION_DATA[TRANSACTION_DATA['time'] >= one_hour_ago]

        last_anomalies_hour_data = ANOMALIES_DATA[ANOMALIES_DATA['time'] >= one_hour_ago]
        

        transaction_failed_data = last_transaction_hour_data[last_transaction_hour_data['status'] == 'failed'][['time', 'F1']]
        transaction_reversed_data = last_transaction_hour_data[last_transaction_hour_data['status'] == 'reversed'][['time', 'F1']]
        transaction_denied_data = last_transaction_hour_data[last_transaction_hour_data['status'] == 'denied'][['time', 'F1']]


        data_to_send = {
            'Failed'    : transaction_failed_data.astype(str).values.tolist(),
            'Reversed'  : transaction_reversed_data.astype(str).values.tolist(),
            'Denied'    : transaction_denied_data.astype(str).values.tolist(),
            'Anomalies' : {
                'Failed'    : last_anomalies_hour_data[last_anomalies_hour_data['status'] == 'failed'][['time', 'F1']].astype(str).values.tolist(),
                'Reversed'  : last_anomalies_hour_data[last_anomalies_hour_data['status'] == 'reversed'][['time', 'F1']].astype(str).values.tolist(),
                'Denied'    : last_anomalies_hour_data[last_anomalies_hour_data['status'] == 'denied'][['time', 'F1']].astype(str).values.tolist()
            },
            'Trend'     : {
                'Failed'    : calculate_trend('failed'),
                'Reversed'  : calculate_trend('reversed'),
                'Denied'    : calculate_trend('denied')
            },
            'Overall'   : {
                'Failed'    : str(transaction_failed_data['F1'].sum()),
                'Reversed'  : str(transaction_reversed_data['F1'].sum()),
                'Denied'    : str(transaction_denied_data['F1'].sum())
            }
        }

        return jsonify(data_to_send)


# TRANSACTIONS ROUTE
# RECEIVE TRANSACTIONS BY JSON
@app.route('/receive', methods=['POST'])
def data():
    global TRANSACTION_DATA, ANOMALIES_DATA, first

    data_to_add = request.get_json()
    

    def check_missing_zero_values():
        global TRANSACTION_DATA

        statuses = ['approved', 'processing', 'denied', 'backend_reversed', 'reversed', 'refunded', 'failed']
        one_minute_future = TRANSACTION_DATA['time'].max() + pd.Timedelta(minutes=1)

        if pd.isnull(one_minute_future):
            one_minute_future = datetime.combine(datetime.now().date(), time(0, 0))

        future_data = pd.DataFrame({'time': [one_minute_future] * 7, 'status': statuses, 'F1': [0] * 7})
        TRANSACTION_DATA = pd.concat([TRANSACTION_DATA, future_data], ignore_index=True).sort_values(by='time')

        return

    while True:

        if data_to_add['time'] in TRANSACTION_DATA['time'].astype(str).values.tolist():
            break
        else:
            check_missing_zero_values()

    data_to_add['time'] = pd.to_datetime(data_to_add['time'])
    mask = (TRANSACTION_DATA['time'] == data_to_add['time']) & (TRANSACTION_DATA['status'] == data_to_add['status'])
    TRANSACTION_DATA.loc[mask, 'F1'] = data_to_add['F1']


    transaction_failed_data = TRANSACTION_DATA[TRANSACTION_DATA['status'] == 'failed']
    transaction_reversed_data = TRANSACTION_DATA[TRANSACTION_DATA['status'] == 'reversed']
    transaction_denied_data = TRANSACTION_DATA[TRANSACTION_DATA['status'] == 'denied']


    anomalous = False

    if data_to_add['status'] == 'failed':
        X_train = transaction_failed_data[['F1']].values
        anomalous = is_anomalous_lof(data_to_add, MODEL_LOF, X_train)

    elif data_to_add['status'] == 'reversed':
        X_train = transaction_reversed_data[['F1']].values
        anomalous = is_anomalous_lof(data_to_add, MODEL_LOF, X_train)

    elif data_to_add['status'] == 'denied':
        X_train = transaction_denied_data[['F1']].values
        anomalous = is_anomalous_lof(data_to_add, MODEL_LOF, X_train)

    try:
        ANOMALIES_DATA
    except NameError:
        ANOMALIES_DATA = pd.DataFrame(columns=['time', 'status', 'F1'])

    if anomalous:
        anomalous_data = pd.DataFrame([data_to_add])
        ANOMALIES_DATA = pd.concat([ANOMALIES_DATA, anomalous_data], axis=0, ignore_index=True)
    
    return 'TRANSACTION COMPLETED'


# SCHEDULER FUNCTIONS
# RESPONSIBLE TO SEND TEAMS ALERTS
def scheduler_trends():
        
    if calculate_trend('failed') == 2:
        send_teams_alert('failed')
    
    if calculate_trend('reversed') == 2:
        send_teams_alert('reversed')

    if calculate_trend('denied') == 2:
        send_teams_alert('denied')


if __name__ == '__main__':
    # SETTING UP THE SCHEDULER FUNCTIONS
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scheduler_trends, trigger="interval", seconds=5)
    scheduler.start()

    app.run(debug=True)
