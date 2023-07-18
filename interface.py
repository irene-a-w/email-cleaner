# creates GUI interface
import PySimpleGUI as sg
import datetime
import pytz
import os.path

from main import logout, new_service, list_messages_by_filter, get_total_messages_filter, trash_all_messages, get_senders_from_message_list

service = new_service() if os.path.exists("token.json") else None
connection_msg = 'connected to gmail account' if os.path.exists("token.json") else 'not connected to gmail account'
msg_list = {}
timezones = ['US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific']
layout = [
    [sg.Button('connect gmail account', key='-CONNECT-'), sg.Button('logout', key='-CLOSE-'), sg.Text(connection_msg, key='-CONNECTIONSTATUS-')],
    [sg.Text('find emails to delete'), sg.Text('input dates in yyyy-mm-dd format'), sg.Text('', key='-DATEERROR-')],
    [sg.Text('after:'), sg.Input(key='-AFTERDATE-', size=(10, 5)),
        sg.CalendarButton('calendar', close_when_date_chosen=True,  target='-AFTERDATE-', format='%Y-%m-%d', no_titlebar=False),
        sg.Text('before:'), sg.Input(key='-BEFOREDATE-', size=(10, 5)),
        sg.CalendarButton('calendar', close_when_date_chosen=True,  target='-BEFOREDATE-', format='%Y-%m-%d', no_titlebar=False),
        sg.Text('timezone'), sg.OptionMenu(values=timezones, key='-TIMEZONE-')],
    [sg.Text('from:'), sg.Input(key='-FILTERFROM-')],
    [sg.Checkbox('only include unread emails', key='-READ-'), sg.Checkbox('load emails with unsubscribe link', key='-UNSUBLINK-')],
     [sg.Button('search', key='-SEARCHEMAIL-'), sg.Button('delete', key='-DELETE-')],
    [sg.Text('', key='-RESULTSTATUS-')],
    [sg.Table(headings=['sender names', 'email', 'count'], values=[], def_col_width=20, auto_size_columns=False, enable_events=True, justification='center', key='-TABLE-')]
]

window = sg.Window('email cleaner', layout)
def window_main():
    global service
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        if event == '-CONNECT-':
            if not service:
                service = new_service()
                window['-CONNECTIONSTATUS-'].update('connected to gmail account.')

        if event == '-CLOSE-':
            logout()

        if event == '-SEARCHEMAIL-':
            before = values['-BEFOREDATE-']
            after = values['-AFTERDATE-']
            pattern = values['-FILTERFROM-']
            unread = values['-READ-']
            timezone = values['-TIMEZONE-']
            if (before != '' or after != '') and not timezone:
                break
            get_messages(before, after, pattern, unread, timezone)

            if values['-UNSUBLINK-'] and msg_list:
                table_data = get_unsubscribe_list()
                window['-TABLE-'].update(table_data)


        if event == '-DELETE-':
            before = values['-BEFOREDATE-']
            after = values['-AFTERDATE-']
            pattern = values['-FILTERFROM-']
            unread = values['-READ-']
            timezone = values['-TIMEZONE-']
            labels = []
            if unread:
                labels += 'UNREAD'

            if pattern == '':
                timezone_obj = pytz.timezone(timezone)
                filter = {'before': before, 'after': after, 'timezone': timezone_obj}
            else:
                filter = pattern
            delete_messages(labels, filter)
            window['-RESULTSTATUS'].update('finished deleting all found messages.')

        if event == '-TABLE-':
            selected_index = values['-TABLE-']
            print(selected_index[0])

    window.close()

def get_messages(before, after, pattern, unread, timezone):
    global window, service, msg_list
    if not service:
        return

    labels = []
    if unread:
        labels.append('UNREAD')
    # verify date is correctly inputted
    if len(before) > 0:
        try:
            datetime.date.fromisoformat(before)
        except ValueError:
            window['-DATEERROR-'].update('wrong date format')
            return
    if len(after) > 0:
        try:
            datetime.date.fromisoformat(after)
        except ValueError:
            window['-DATEERROR-'].update('wrong date format')
            return

    timezone_obj = ''
    if timezone:
        timezone_obj = pytz.timezone(timezone)
    filter = {'before': before, 'after': after, 'timezone': timezone_obj, 'from': pattern}

    msg_list = list_messages_by_filter(service, 'me', labels, filter, None)
    num_found = get_total_messages_filter(service, msg_list, labels, filter)
    window['-RESULTSTATUS-'].update(f'found {num_found} emails.')


def delete_messages(labels, filter):
    global service, msg_list
    trash_all_messages(service, msg_list, labels, filter)
    # reset msg_list after deleting all msgs
    msg_list = {}


def get_unsubscribe_list():
    # TODO need to combine sender names if they are the same ... prob have to do that in main
    global service, msg_list
    senders = get_senders_from_message_list(service, msg_list['messages'])
    table_rows = []
    for email in senders[0]:
        sender_name = senders[0]
        sender_info = senders[1][email]
        occurance = sender_name[email]
        unsub_link = sender_info.unsub_link
        display = ', '.join(sender_info.from_name)
        cur = [display, email, occurance]
        if unsub_link:
            table_rows.append(cur)
    return table_rows


window_main()