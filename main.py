import time
from datetime import datetime
import requests
import pandas as pd
import creds


def create_link(df_without_link: pd.DataFrame):
    df_without_link['Link'] = [f"https://www.google.com/maps/search/?api=1&query={a},{b}"
                               for a, b in zip(df_without_link['Latitude'], df_without_link['Longitude'])]
    return df_without_link


def get_traffic_updates():
    headers = {"AccountKey": creds.LTA_api}
    url = 'http://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents'

    while True:
        JsonData = requests.get(url=url, headers=headers).json()
        try:
            dataframe = pd.DataFrame(JsonData['value'])
            return create_link(dataframe)
        except Exception as e:
            print(JsonData)
            print(e)
            print("Error encountered while getting update. Maintenance? Retying in 5 mins")
            time.sleep(300)


def return_differences(first: pd.DataFrame, second: pd.DataFrame):
    """ where first is the first dataframe
     and second is the second dataframe
     merge with indicator to observe which row appears
     use query to get only those that appear left_only
     drop _merge column
     pretesting was done in ipynb before shortening"""

    new_updates = second.merge(first, how='left',
                               indicator=True).query("_merge == 'left_only'").drop(['_merge'], axis=1)
    removed_updates = first.merge(second, how='left',
                                  indicator=True).query("_merge == 'left_only'").drop(['_merge'], axis=1)

    return new_updates, removed_updates


def update_channel(new, removed):
    string = f" <strong><u>NEW</u></strong> \n"
    if len(new) > 0:
        for count, row in new.iterrows():
            string = string + f"\n<b>{row['Type']}</b> \n" \
                              f"{row['Message']} \n" \
                              f"<a href='{row['Link']}'>Estimated Location</a>\n"
        string = string + "\n<strong><u>REMOVED</u></strong>\n"

    if len(removed) > 0:
        for count, row in removed.iterrows():
            string = string + f"\n<b>{row['Type']}</b> \n" \
                              f"{row['Message']} \n"

    # params for telegram send_message API

    params = {
        "chat_id": creds.chat_id,
        "text": string,
        "parse_mode": "HTML"
    }

    endpoint = f"https://api.telegram.org/bot{creds.telegram_api}/sendMessage"
    req = requests.get(endpoint, params=params).json()
    try:
        if req['ok']:
            log_update("Successfully updated")
    except Exception as e:
        print(datetime.now().replace(second=0, microsecond=0))
        print(e)
        print("Encountered error")


def log_update(message):
    print(f"{datetime.now().replace(second=0, microsecond=0)}\n{message}")


# get the first dataframe

log_update("Starting bot")

initial = get_traffic_updates()

time.sleep(120)

while True:

    update = get_traffic_updates()

    new, removed = return_differences(initial, update)

    if len(new) == 0 & len(removed) == 0:

        log_update("No updates")

    else:
        update_channel(new, removed)

    initial = update

    time.sleep(120)
