import json
import logging
import os


class ChatHistory:
    def __init__(self, filename):
        self.directory = 'chat_history'
        self.filename = filename
        self.chat_history = self.load_chat_history()

    def load_chat_history(self):
        filename = os.path.join(self.directory, f'{self.filename}.json')
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                chat_history = json.load(f)
        else:
            chat_history = []
        return chat_history

    def append_message(self, user_type, message):
        new_message = {'role': user_type, 'content': message}
        self.chat_history.append(new_message)
        self.save()

    def get_culled_messages(self, max_length=300):
        total_length = 0
        chat_history_culled = self.chat_history.copy()
        for message in self.chat_history:
            content = message['content']
            total_length += self._get_total_length_of_content(content)

        while total_length > max_length:
            message_to_remove = chat_history_culled.pop(0)
            content = message_to_remove['content']
            content_length = self._get_total_length_of_content(content)
            total_length -= content_length

        logging.info("Total Length: " + str(total_length))
        logging.info("Num Messages: " + str(len(chat_history_culled)))
        return chat_history_culled

    def save(self):
        # loop through chat_history and convert any messages that are encoded json into json
        for message in self.chat_history:
            content = message['content']
            if isinstance(content, str):
                try:
                    message['content'] = json.loads(content)
                except json.decoder.JSONDecodeError as ex:
                    # logging.info("Failed to decode json: " + content)
                    pass
        filename = os.path.join(self.directory, f'{self.filename}.json')
        with open(filename, 'w') as f:
            json.dump(self.chat_history, f, indent=2)

    def _get_total_length_of_content(self, content):
        total_length = 0
        if isinstance(content, str):
            total_length = len(content.split())
        elif isinstance(content, dict) and 'dialogue' in content:
            total_length = len(content['dialogue'].split())

        return total_length
