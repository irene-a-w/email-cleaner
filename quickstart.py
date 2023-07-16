from __future__ import print_function

import os.path
import pytz
import base64

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium.webdriver.support.wait import WebDriverWait


def create_service(credentials_info_file, api_name, api_version, scopes):
    SCOPES = scopes
    creds = None

    # check if token exist else sign user in and get new token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_info_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # save user credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(api_name, api_version, credentials=creds)
        return service
    except Exception as e:
        print(e)
        print(f'failed to create service for {api_name}')
        os.remove('token.json')
        return None


def list_messages(service, user_id, label_ids):
    message_list = service.users().messages().list(userId=user_id, labelIds=label_ids).execute()
    return message_list


def list_messages_by_date(service, user_id, label_ids, dates, user_timezone):
    # dates must be in yyyy-mm-dd format
    before = dates['before'] # timestamp must be 00:00:00
    after = dates['after'] # timestamp must be 23:59:59
    time_str = ""
    if after != "":
        after += " 00:00:00"
        after_epoch = datetime.strptime(after, "%Y-%m-%d %H:%M:%S").astimezone(user_timezone).timestamp()
        time_str += f"after:{int(after_epoch)}"

    if before != "":
        if len(time_str) > 0:
            time_str += " "
        before += " 00:00:00"
        before_epoch = datetime.strptime(before, "%Y-%m-%d %H:%M:%S").astimezone(user_timezone).timestamp()
        time_str += f"before: {int(before_epoch)}"
    print("time", time_str)
    message_list = service.users().messages().list(userId=user_id, labelIds=label_ids, q=time_str).execute()
    return message_list


def get_message(service, user_id, message_id, format, headers):
    message = service.users().messages().get(userId=user_id, id=message_id, format=format, metadataHeaders=headers).execute()
    return message


def trash_message(service, user_id, message_id):
    service.users().messages().trash(userId=user_id, id=message_id).execute()


def batch_trash_message(service, user_id, msg_list):
    for msg in msg_list:
        msg_id = msg['id']
        trash_message(service, user_id, msg_id)
    print("completed batch trash")

# permanently deletes messages
def batch_delete_messages(service, user_id, msg_list):
    # get list of message ids
    delete_msg_ids = []
    for msg in msg_list:
        msg_id = msg['id']
        delete_msg_ids.append(str(msg_id))
    service.users().messages().batchDelete(userId=user_id, body={"ids": delete_msg_ids}).execute()
    print("completed batch delete")

def get_message_info_from_lists(service, msg_list, file_format):
    # print(msg_list)
    all_msg_info = []
    for msg in msg_list:
        current = get_message(service, 'me', msg['id'], file_format, None)
        all_msg_info.append(current)
    return all_msg_info

def get_senders_from_message_list(service, msg_list):
    senders = {}
    for msg in msg_list:
        current = get_message(service, 'me', msg['id'], 'metadata', ['From', 'List-Unsubscribe'])
        cur_headers = current['payload']
        # get who the message is from
        # print(cur_headers, msg['id'])
        cur_sender = cur_headers[0]['value']
        if cur_sender not in senders:
            senders[cur_sender] = 1
        else:
            senders[cur_sender] += 1
    return senders


def decode_msg(message):
    for p in message["payload"]["parts"]:
        if p["mimeType"] in ["text/plain"]:
            data = base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8")
            return data


def unsubscribe(link):
    options = Options()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    driver.get(link)

    # check if the webpage contains any buttons to press
    check_submit = driver.find_elements(By.XPATH, '//input[@type="submit"]')
    # if there is no submit, then successfully unsubscribed
    if len(check_submit) == 0:
        print("unsubscribed.")
        return True

    # check if there are any checkboxes needed to unsubscribe
    checkboxes = driver.find_elements(By.XPATH, '//input[@type="checkbox"]')
    for elem in checkboxes:
        if not elem.is_selected():
            elem.click()

    # click submit button
    check_submit[0].click()

    # if page redirects, then print success, otherwise user must manually unsubscribe
    wait = WebDriverWait(driver, 5)
    if driver.current_url != link:
        print("unsubscribed")
        return True

    return False



def main():
    credentials = 'credentials.json'
    api_name = 'gmail'
    api_version = 'v1'
    scope_list = ['https://mail.google.com/']
    service = create_service(credentials, api_name, api_version, scope_list)
    try:
        # get list of messages
        # msg_list = list_messages(service, 'me', 5)
        # get messages from list
        # msg_detail_list = get_message_info_from_lists(service, msg_list['messages'], 'metadata')
        # print(msg_detail_list)
        # print(get_message(service, 'me', '189522174248b4e1', 'full'))
        # try to delete mail

        date_dict = {'before': '2023-07-15', 'after': '2023-07-10'}
        user_timezone = pytz.timezone("US/Central") # need to implement timezone for GUI interface

        # msg_by_time = list_messages_by_date(service, 'me', ['UNREAD'], date_dict, user_timezone)
        # print
        # send_count = get_senders_from_message_list(service, msg_by_time['messages'])
        # print(send_count)
        unsubscribe('https://www.nitrocollege.com/hs/manage-preferences/unsubscribe?languagePreference=en&d=VnfP3Q8zMss2VTbssJ41RkPXW41S35V1Q69WGW3_R5921JxwY5VWxCRs17r7tjVQtBSP4LV_RRN85NPRNCHYkrW586p248B3YnCW8j-8fh5smRTfV1yf0N31HSwFW7HXSR47jjPygW2f1Gb53wSBQ923R3&v=3&utm_campaign=act1p_nit_s_co_so_smt1_07152023&utm_source=hs_email&utm_medium=email&utm_content=266360933&_hsenc=p2ANqtz--kcutuxlCSK49AKsSiZ4Fq337uWTNxdlK-tNG3pN_OEISJKGHJLiMzf7-CO_UVBzxawyNXAx1IuhFLrGbKl1kPg_u5TQ&_hsmi=266360933')


    except HttpError as error:
        # TODO handle the error
        print(f'An error occurred: {error}')



if __name__ == '__main__':
    main()

# notes:
# dont need to parse email, just get list unsubscribe header
