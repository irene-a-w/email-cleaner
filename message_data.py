class message:
    def __init__(self, message_id, from_name=None, from_email=None):
        self.id = message_id
        self.from_name = from_name
        self.from_email = from_email
        self.unsub_link = None

class unsubscribe_list:
    def __init__(self, from_email, unsub_link=None):
        self.from_name = []
        self.msg_ids = []
        self.from_email = from_email
        self.unsub_link = unsub_link

    def add_from_name(self, alt_name):
        if alt_name not in self.from_name:
            self.from_name.append(alt_name)

    def add_msg_id(self, id):
        if id not in self.msg_ids:
            self.msg_ids.append(id)
