import time
from datetime import datetime
import requests
import pandas as pd
import creds
from TrafficTelegramBot import TrafficTelegramBot

accident_id = 238
roadworks_id = 237


# These IDs are for future usage if I decide to
# reserved_id = 232 to 238

def create_link(df_without_link: pd.DataFrame) -> pd.DataFrame:
    """
    Create a column of Google Maps links from Latitude and Longitude columns

    :param df_without_link: Dataframe with 'Latitude' and 'Longitude'
    :return: dataframe with 'Link' column
    """
    df_without_link['Link'] = [f"https://www.google.com/maps/search/?api=1&query={a},{b}"
                               for a, b in zip(df_without_link['Latitude'], df_without_link['Longitude'])]
    return df_without_link


def currentTime() -> str:
    """
    Returns the string of current time in HH:MM
    For updating messages
    :return: string
    """
    return f"{datetime.now().hour}:{datetime.now().minute}"


def get_traffic_updates(LTA_API=creds.LTA_api) -> pd.DataFrame:
    """
    Gets details from TrafficIncidents API endpoint and parses into a dataframe
    In the event of error, tries again every 5 mins
    :param LTA_API: Api key to make requests to LTA
    :return: dataframe of Traffic incidents
    """
    headers = {"AccountKey": LTA_API}
    url = 'http://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents'

    while True:
        # Request get from url with headers

        JsonData = requests.get(url=url, headers=headers).json()

        # Also mentioned in TO DO, try to improve error handling. Try in this instance catches when the key 'value'
        # cannot be found. However, it is not able to catch server errors or local errors.
        # TODO: Improve error handling to catch when it is maintenance or due to local network issues

        try:
            #

            dataframe = pd.DataFrame(JsonData['value'])
            return create_link(dataframe)

        except Exception as e:

            # For now, although never ideal, all exceptions are allowed to pass and monitor
            # Waits for 5 mins before trying again
            print(JsonData)
            print(e)
            print("Error encountered while getting update. Maintenance? Retying in 5 mins")
            time.sleep(300)


def return_differences(first: pd.DataFrame, second: pd.DataFrame) -> tuple:
    """
    Gets the update between the first and second dataframe
    Where the second dataframe is a later call

    :param first: initial dataframe
    :param second: delayed dataframe
    :return: tuple of two dataframes, new and removed updates
    """

    # By using indicator= True, it will show us which dataframe contains rows that are not in the other
    # For example, in new_updates, we merge on the second dataframe with first dataframe to show rows that are only
    # in the second dataframe. The '_merge_ column is generated by indicator.
    # Thereafter, the query operation is used to get rows with only column '_merge' == "left_only".
    # Finally, drop operation to drop the column '_merge' .

    new_updates = second.merge(first, how='left',
                               indicator=True).query("_merge == 'left_only'").drop(['_merge'], axis=1)

    # The same is done here however we merge on the first to show rows in the first dataframe only. The query and drop
    # operations are the same as above.

    removed_updates = first.merge(second, how='left',
                                  indicator=True).query("_merge == 'left_only'").drop(['_merge'], axis=1)

    return new_updates, removed_updates


def new_removed_message(new: pd.DataFrame, removed: pd.DataFrame):
    """
    parse the new and removed updates into messages
    Sends messages into channel
    :param new: dataframe of new updates
    :param removed: dataframe of removed updates
    :return : string to pass to telegram api
    """

    # Using HTML formatting
    # Initialise empty string

    string = ""
    # If there are no new updates

    if len(new) > 0:
        string = string + "<strong><u>NEW</u></strong> \n"
        for count, row in new.iterrows():
            string = string + f"\n<b>{row['Type']}</b> \n" \
                              f"{row['Message']} \n" \
                              f"<a href='{row['Link']}'>Estimated Location</a>\n"

    # If there are no removed updates
    if len(removed) > 0:
        string = string + "\n<strong><u>REMOVED</u></strong>\n"
        for count, row in removed.iterrows():
            string = string + f"\n<b>{row['Type']}</b> \n" \
                              f"{row['Message']} \n"

    # params for telegram send_message API

    return string


def log_update(message: str):
    """
    Simple function to print with the current date and time, will be replaced with logging
    :param message: string of message to print
    """
    print(f"{datetime.now().replace(second=0, microsecond=0)}\n{message}")


def parse_dataframe_to_html(parse_dataframe: pd.DataFrame):
    """
    Parses dataframe accordingly whether It's for roadwork or non roadwork

    :param parse_dataframe: dataframe of roadwork/non-roadwork
    :return:
    """
    # If roadwork is in columns parse for roadworks
    if "Roadwork" in parse_dataframe['Type'].unique():
        string = f"<strong><u>Roadworks on expressways </u></strong>\n" \
                 f"<i>Note: This list is only updated every 10 mins. </i>\n" \
                 f"<i>Last updated: {currentTime()}</i>\n\n"

        for count, row in parse_dataframe.iterrows():
            string = string + f"{row['Message']}\n"
        return string

    else:
        different_types = list(parse_dataframe['Type'].unique())
        string = f"<strong><u>Non-Roadwork Incidents</u></strong>\n\n" \
                 f"<i>Note: This list shows all current major incidents and updates every 2 mins if " \
                 f"updates are present.</i>" \
                 f"<i>Last updated: {currentTime()}</i>\n\n"
        for item in different_types:
            string = string + f"<b><u>{item}</u></b>\n"
            item_df = parse_dataframe[parse_dataframe['Type'] == item]
            for count, row in item_df.iterrows():
                string = string + f"\n{row['Message']} \n" \
                                  f"<a href='{row['Link']}'>Estimated Location</a>\n"

        return string


def filter_expressways(all_roadworks: pd.DataFrame):
    expressways = ['AYE', 'BKE', 'CTE', 'ECP', 'KPE', 'KJE', 'MCE', 'NSC', 'PIE', 'SLE', 'TPE']
    expressways_string = '|'.join(item for item in expressways)

    return all_roadworks[all_roadworks['Message'].str.contains(expressways_string)]


TTB = TrafficTelegramBot(creds.telegram_api, creds.chat_id)

log_update("Starting bot")

# get the first dataframe

initial = get_traffic_updates()
roadworks_initial = filter_expressways(initial.query("Type == 'Roadwork'"))
time.sleep(120)

# initial counter, we only want to update roadworks every 5 iterations

roadworks_counter = 5

while True:

    update = get_traffic_updates()

    major_initial = initial.query("Type != 'Roadwork'")
    major_update = update.query("Type != 'Roadwork'")

    new, removed = return_differences(major_initial, major_update)

    # if no new updates at all, print "No updates"

    if roadworks_counter == 5:
        roadworks_counter = 0
        # TODO: Split text as this is temporary solution due to message length limit

        roadworks_update = filter_expressways(update.query("Type == 'Roadwork'"))

        new_roadworks, removed_roadworks = return_differences(roadworks_initial, roadworks_update)

        if len(new_roadworks) == 0 & len(removed_roadworks) == 0:
            log_update("No updates for roadworks")

        else:
            update_roadworks = parse_dataframe_to_html(roadworks_update)
            TTB.update_channel('edit', text=update_roadworks, message_id=roadworks_id)
            roadworks_initial = roadworks_update

    if len(new) == 0 & len(removed) == 0:

        log_update("No updates")

    else:
        message_to_send = new_removed_message(new, removed)
        update_pin = parse_dataframe_to_html(major_update)
        # trial removing sending messages completely. making it purely by updates
        # TTB.update_channel("send", text=message_to_send)
        TTB.update_channel('edit', text=update_pin, message_id=accident_id)

    initial = update
    roadworks_counter += 1
    time.sleep(120)
