import os
import openai
import json
from time import time,sleep
import datetime

from chat_history import ChatHistory


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector


def chatgpt_completion(messages, model="gpt-3.5-turbo", filename="muse"):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=1000,
        temperature=0.9,
    )
    text = response['choices'][0]['message']['content']
    filename = f"{time()}_{filename}.txt"
    save_file('gpt3_logs/%s' % filename, str(messages) + '\n\n==========\n\n' + text)
    return text

def gpt3_completion(prompt, prompt_type):
    base_convo = list()
    base_convo.append({'role': 'system', 'content': default_system})
    base_convo.append({'role': 'user', 'content': prompt})
    return chatgpt_completion(base_convo, filename=prompt_type)


def flatten_convo(conversation):
    convo = ''
    for i in conversation:
        convo += '%s: %s\n' % (i['role'].upper(), i['content'])
    return convo.strip()


if __name__ == '__main__':
    convo_length = 30
    openai.api_key = open_file('key_openai.txt')
    default_system = 'I am an AI named Muse. My primary goal is to help the user plan, brainstorm, outline, and otherwise construct their AI Twitch streamer dialogue.'
    base_convo = list()
    base_convo.append({'role': 'system', 'content': default_system})
    base_convo.append({'role': 'user', 'content': open_file('.\prompts\emily_dialogue.txt')})

    print(str(base_convo))
    chat_history = ChatHistory('full_chat_history')
    conversation = list()
    counter = 0
    while True:
        # get user input, save to file
        a = input('\n\nUSER: ')
        chat_history.append_message('user', a)
        convo_length = 2000  # Amount of words to use
        conversation = list()
        # append base_convo to conversation
        conversation.extend(base_convo)
        culled_messages = chat_history.get_culled_messages(convo_length)
        conversation.extend(culled_messages)
        flat = flatten_convo(conversation)
        #print(flat)
        # infer user intent, disposition, valence, needs
        prompt = open_file('prompt_anticipate.txt').replace('<<INPUT>>', flat)
        print(" - Sending request to GPT-3 for Anticipation data")
        anticipation = gpt3_completion(prompt, "anticipation")
        # print('\n\nANTICIPATION: %s' % anticipation)
        print(" - Received Anticipation data")
        # summarize the conversation to the most salient points
        prompt = open_file('prompt_salience.txt').replace('<<INPUT>>', flat)
        salience = gpt3_completion(prompt, "salience")
        # print('\n\nSALIENCE: %s' % salience)
        print(" - Received salience data, sending request to MUSE")
        # update SYSTEM based upon user needs and salience
        conversation[0]['content'] = default_system + ''' Here's a brief summary of the conversation: %s - And here's what I expect the user's needs are: %s''' % (salience, anticipation)
        # generate a response
        response = chatgpt_completion(conversation)
        conversation.append({'role': 'assistant', 'content': response})
        print('\n\nMUSE: %s' % response)
        # increment counter and consolidate memories
        counter += 2
        # if counter >= 10:
        #     # reset conversation
        #     conversation = list()
        #     conversation.append({'role': 'system', 'content': default_system})