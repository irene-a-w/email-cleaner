from __future__ import print_function

import os.path
import base64
import pytz
import time
import threading
import concurrent.futures


from datetime import datetime
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium.webdriver.support.wait import WebDriverWait

from message_data import unsubscribe_list


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


def list_messages(service, user_id, label_ids, page_token):
    label_ids += ['INBOX']
    message_list = service.users().messages().list(userId=user_id, labelIds=label_ids, maxResults=10, pageToken=page_token).execute()
    return message_list


def list_messages_by_filter(service, user_id, label_ids, filter, next_page):
    label_ids += ['INBOX']
    query_str = ''
    # dates must be in yyyy-mm-dd format
    before = filter['before'] # timestamp must be 00:00:00
    after = filter['after'] # timestamp must be 23:59:59
    time_str = ""
    if after != "":
        after += " 00:00:00"
        after_epoch = datetime.strptime(after, "%Y-%m-%d %H:%M:%S").astimezone(filter['timezone']).timestamp()
        time_str += f"after: {int(after_epoch)}"

    if before != "":
        if len(time_str) > 0:
            time_str += " "
        before += " 00:00:00"
        before_epoch = datetime.strptime(before, "%Y-%m-%d %H:%M:%S").astimezone(filter['timezone']).timestamp()
        time_str += f"before: {int(before_epoch)}"
    query_str = time_str

    if filter['from'] != '':
        query_str += f" from: {filter['from']}"
    message_list = service.users().messages().list(userId=user_id, labelIds=label_ids, maxResults=500, pageToken=next_page, q=query_str).execute()
    return message_list


def get_total_messages_filter(service, msg_list, labels, filter):
    labels += ['INBOX']
    count = len(msg_list.get('messages', []))
    if 'nextPageToken' in msg_list:
        token = msg_list["nextPageToken"]
        while token:
            cur_page = list_messages_by_filter(service, 'me', labels, filter, token)
            token = cur_page.get("nextPageToken", None)
            if not token:
                count += len(cur_page.get('messages', []))
            else:
                count += 500

    return count


def get_message(service, user_id, message_id, format, headers):
    message = service.users().messages().get(userId=user_id, id=message_id, format=format, metadataHeaders=headers).execute()
    return message


# need to make a list of all message id's concurrently
def trash_message(service, user_id, message_id):
    service.users().messages().trash(userId=user_id, id=message_id).execute()


def trash_messages_in_page(service, user_id, msg_list):
    [trash_message(service, user_id, msg['id']) for msg in msg_list]


def trash_all_messages(service, msg_list, labels, filter):
    labels += ['INBOX']
    trash_messages_in_page(service, 'me', msg_list['messages'])
    if 'nextPageToken' in msg_list:
        token = msg_list["nextPageToken"]
        while token:
            cur_page = list_messages_by_filter(service, 'me', labels, filter, token)
            if 'message' in cur_page:
                token = cur_page.get("nextPageToken", None)
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as exe:
                    _ = [exe.submit(trash_message, service, 'me', msg) for msg in cur_page['messages']]

    print("finished deleting all found messages.")


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
    sender_info = {}
    sender_count = {}
    # print(msg_list)
    for msg in msg_list:
        current = get_message(service, 'me', msg['id'], 'metadata', ['From', 'List-Unsubscribe'])
        cur_headers = current['payload']['headers']
        cur_sender = None
        cur_unsub_link = None
        for hdr in cur_headers:
            if hdr['name'] == 'From':
                cur_sender = hdr['value']
            if hdr['name'] == 'List-Unsubscribe':
                cur_unsub_link = hdr['value']

        # split sender to name / email
        # find the first index of "<"
        cur_name = None
        if "<" in cur_sender:
            left_bracket = cur_sender.index("<")
            cur_name = cur_sender[:left_bracket-1]
            cur_email = cur_sender[left_bracket+1:-1]
        else:
            cur_email = cur_sender
        sender_count[cur_email] = 1 + sender_count.get(cur_email, 0)

        # keep track of the messages
        if cur_email not in sender_info:
            msg_obj = unsubscribe_list(cur_email)
            sender_info[cur_email] = msg_obj
        else:
            msg_obj = sender_info.get(cur_email)

        if cur_name:
            msg_obj.add_from_name(cur_name)
        else:
            msg_obj.add_from_name(cur_email)
        msg_obj.add_msg_id(msg['id'])
        if not msg_obj.unsub_link and cur_unsub_link:
            # parse to find only the link
            start_idx = cur_unsub_link.find('https')
            comma_idx = cur_unsub_link.find(',')
            if comma_idx > -1 and comma_idx < start_idx:
                # this case means that the link is in the second half of the list
                parsed_link = cur_unsub_link[start_idx:-1]
            elif comma_idx > -1 and comma_idx > start_idx:
                parsed_link = cur_unsub_link[start_idx:comma_idx-1]
            else:
                # check if it has it in there otherwise just leave it lol
                parsed_link = cur_unsub_link[1:-1]
            msg_obj.unsub_link = parsed_link

    return [sender_count, sender_info]


def get_unsubscribe_link(email, sender_info):
    # sender_info is a dictionary
    sender_obj = sender_info.get(email)
    return sender_obj.unsub_link


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
    check_submit = driver.find_elements(By.XPATH, '//button[@type="submit"]') or driver.find_elements(By.XPATH, '//input[@type="button"]')
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
    hover = ActionChains(driver).move_to_element(check_submit[0])
    hover.perform()
    check_submit[0].click()

    # if page redirects, then print success, otherwise user must manually unsubscribe
    driver.implicitly_wait(5)
    print("unsubscribed.")

    return True


def logout():
    if os.path.exists("token.json"):
        os.remove('token.json')


def new_service():
    credentials = 'credentials.json'
    api_name = 'gmail'
    api_version = 'v1'
    scope_list = ['https://mail.google.com/']
    service = create_service(credentials, api_name, api_version, scope_list)
    return service


def main():
    service = new_service()

    # try:
        # get list of messages
        # msg_list = list_messages(service, 'me', 5)
        # get messages from list
        # msg_detail_list = get_message_info_from_lists(service, msg_list['messages'], 'metadata')
        # print(msg_detail_list)
        # print(get_message(service, 'me', '189522174248b4e1', 'full'))
        # try to delete mail


    # user_timezone = pytz.timezone("US/Central") # need to implement timezone for GUI interface
    # date_dict = {'before': '2023-07-01', 'after': '2023-03-21', 'timezone': user_timezone, 'from': ''}
    # msg_by_time = list_messages_by_filter(service, 'me', ['UNREAD'], date_dict, None)
    # print(msg_by_time)
    # cnt = get_total_messages_filter(service, msg_by_time, ['UNREAD'], date_dict)
    # print(cnt)
    # trash_all_messages(service, msg_by_time, ['INBOX'], date_dict)
        # send_count = get_senders_from_message_list(service, msg_by_time['messages'])
        # print(send_count)

    # except HttpError as error:
    #     # TODO handle the error
    #     print(f'An error occurred: {error}')



if __name__ == '__main__':
    main()

