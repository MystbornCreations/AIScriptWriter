import concurrent.futures
import os
import openai
import json
from time import time, sleep
import datetime

from chat_history import ChatHistory


class FileManager:
    @staticmethod
    def open_file(filepath):
        with open(filepath, 'r', encoding='utf-8') as infile:
            return infile.read()

    @staticmethod
    def save_file(filepath, content):
        with open(filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(content)

    @staticmethod
    def load_json(filepath):
        with open(filepath, 'r', encoding='utf-8') as infile:
            return json.load(infile)

    @staticmethod
    def save_json(filepath, payload):
        with open(filepath, 'w', encoding='utf-8') as outfile:
            json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


class Utils:
    @staticmethod
    def timestamp_to_datetime(unix_time):
        return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")

    @staticmethod
    def flatten_convo(conversation):
        convo = ''
        for i in conversation:
            convo += '%s: %s\n' % (i['role'].upper(), i['content'])
        return convo.strip()


class GPT3:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = api_key

    def gpt3_embedding(self, content, engine='text-embedding-ada-002'):
        content = content.encode(encoding='ASCII', errors='ignore').decode()  # fix any UNICODE errors
        response = openai.Embedding.create(input=content, engine=engine)
        vector = response['data'][0]['embedding']  # this is a normal list
        return vector

    def chatgpt_completion(self, messages, model="gpt-3.5-turbo", filename="muse"):
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=1000,
            temperature=0.9,
        )
        text = response['choices'][0]['message']['content']
        filename = f"{time()}_{filename}.txt"
        FileManager.save_file('gpt3_logs/%s' % filename, str(messages) + '\n\n==========\n\n' + text)
        return text

    def gpt3_completion(self, prompt, prompt_type, default_system):
        base_convo = list()
        base_convo.append({'role': 'system', 'content': default_system})
        base_convo.append({'role': 'user', 'content': prompt})
        return self.chatgpt_completion(base_convo, filename=prompt_type)


class MuseAssistant:
    def __init__(self, api_key, default_system, convo_length):
        self.gpt3 = GPT3(api_key)
        self.default_system = default_system
        self.base_convo = [
            {'role': 'system', 'content': default_system},
            {'role': 'user', 'content': FileManager.open_file('.\prompts\emily_dialogue.txt')}
        ]
        self.chat_history = ChatHistory('full_chat_history')
        self.convo_length = convo_length

    def start(self):
        conversation = self.prepare_conversation()
        flat = Utils.flatten_convo(conversation)
        print(flat)
        while True:
            user_input = input('\n\nUSER: ')
            self.chat_history.append_message('user', user_input)
            conversation = self.prepare_conversation()
            flat = Utils.flatten_convo(conversation)

            # Run infer_anticipation and extract_salience concurrently
            with concurrent.futures.ThreadPoolExecutor() as executor:
                anticipation_future = executor.submit(self.infer_anticipation, flat)
                salience_future = executor.submit(self.extract_salience, flat)
                anticipation = anticipation_future.result()
                salience = salience_future.result()

            print(" - Sending request to MUSE")

            conversation[0]['content'] = self.default_system + ''' Here's a brief summary of the conversation: %s - And here's what I expect the user's needs are: %s''' % (salience, anticipation)
            response = self.generate_response(conversation)
            print('\n\nMUSE: %s' % response)
            self.chat_history.append_message('assistant', response)
            # Copy response to clipboard
            os.system(f'echo {response} | clip')
            print("Copied response to clipboard")

    def prepare_conversation(self):
        conversation = list(self.base_convo)
        culled_messages = self.chat_history.get_culled_messages(self.convo_length)
        conversation.extend(culled_messages)
        return conversation

    def infer_anticipation(self, flat_convo):
        prompt = FileManager.open_file('prompt_anticipate.txt').replace('<<INPUT>>', flat_convo)
        print(" - Sending request to GPT-3 for Anticipation data")
        anticipation = self.gpt3.gpt3_completion(prompt, "anticipation", self.default_system)
        print(" - Received Anticipation data")
        return anticipation

    def extract_salience(self, flat_convo):
        prompt = FileManager.open_file('prompt_salience.txt').replace('<<INPUT>>', flat_convo)
        print("\n - Sending request to GPT-3 for Salience data")
        salience = self.gpt3.gpt3_completion(prompt, "salience", self.default_system)
        print(" - Received salience data")
        return salience

    def generate_response(self, conversation):
        return self.gpt3.chatgpt_completion(conversation)


if __name__ == '__main__':
    api_key = FileManager.open_file('key_openai.txt')
    default_system = 'I am an AI named Muse. My primary goal is to help the user plan, brainstorm, outline, and otherwise construct their AI Twitch streamer dialogue.'
    convo_length = 1500 # Number of words to keep in chat history

    muse_assistant = MuseAssistant(api_key, default_system, convo_length)
    muse_assistant.start()
