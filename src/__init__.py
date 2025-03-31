from pychatgpt import pyChatGPT
import os


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

'''
    - First, install the requirements by running `pip install -r requirements.txt`.
    
    Run this script to start a conversation with ChatGPT.
'''
if __name__ == '__main__':
    while True:
        conversation_id = input(
            'Please enter your conversation id (if you want to continue old chat): '
        )
        chat = pyChatGPT.ChatGPT('', conversation_id)
        break

    clear_screen()
    print('Conversation started. Type "quit" to quit.\n')

    print("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
    while True:
        prompt = input('\nYou: ')
        if not prompt:
            continue
        if prompt.lower() == 'quit':
            break
        print('\nChatGPT: ', end='')

        response = chat.send_message(prompt)
        print(response['message'], end='')
        print("\n\n---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
