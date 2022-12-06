
### Tuesday, December 6, 2022 (Code is tested, working and updated 💯)
I got reports of OpenAI changing their API method, nothing is changed, they just added some extra headers (Check out ./Classes/chat.py)

# PyChatGPT
*If you want me to maintain this repo, please star ⭐️*


I have been looking for a way to interact with the new Chat GPT API, but most of the sources here on GitHub 
require you to have a Chromium instance running in the background. or by using the Web Inspector to grab Access Token manually.

No more. I have been able to reverse engineer the API and use a TLS client to mimic a real user, allowing the script to login without setting off any bot detection techniques by Auth0

Basically, the script logs in on your behalf, using a TLS client, then grabs the Access Token. It's pretty fast.

### Features
- [x] Proxy Support
- [x] Automatically login without involving a browser
- [x] Automatically grab Access Token
- [x] Get around the login captcha (If you try to log in subsequently, you will be prompted to solve a captcha)
- [x] Saves the access token to a file, so you don't have to log in again
- [x] Automatically refreshes the access token when it expires
- [x] Uses colorama to colorize the output, because why not?
- [x] Smart Conversation Tracking 

```
You: Hi there, My name is Rawa
Chat GPT: Hello Rawa, nice to meet you. Is there something you would like to talk about or ask me? I'm here to help with any questions you may have.
You: great, now say my name like Heisenberg
Chat GPT: Sure, Rawa like Heisenberg. Is there anything else you would like to talk about? I'm here to help with any questions you may have.
You: Sorry I meant like the episode of Breaking Bad where Walter White says Heisenberg
Chat GPT: Ah, I see. In that case, you could try saying it like this: "My name is Rawa, like Heisenberg." This is a reference to the character Walter White from the TV show Breaking Bad, who often used the pseudonym "Heisenberg" when conducting illegal activities. The character was known for his cool and calculated demeanor, so saying your name like Heisenberg in this context would mean saying it with confidence and authority.
 ```
[//]: # (Add A changelog here)

### Change Log

- Added conversation tracking (thanks to @yeeyangtee)
- Added a nice looking spinner when the script is waiting for a response from the API

### Shall we get started?
1. Clone the repository
2. Install the requirements using `pip install -r requirements.txt`
3. Open `config.json` and enter your email and password.
4. Run `main.py` and let the script do the rest.

### Other notes
If the token creation process is failing, on `main.py` on line 40
1. Try to use a proxy (I recommend using this always)
```python
Auth.OpenAIAuth(email_address=email, password=password, use_proxy=True, proxy="http://127.0.0.0:8080")
```
2. Don't try to log in too fast. At least wait 10 minutes if you're being rate limited.
3. If you're still having issues, try to use a VPN. On a VPN, the script should work fine.
### What's next?
I'm planning to add a few more features, such as:
- [ ] A python module that can be imported and used in other projects
- [ ] A way to save the conversation
- [ ] Better error handling

### Screenshots
1. Chatting with the bot
![Screenshot 1](https://media.discordapp.net/attachments/1038565125482881027/1049255804366237736/image.png)

2. The Script creating a token for you.
![Screenshot 2](https://media.discordapp.net/attachments/1038565125482881027/1049072247442264094/image.png?width=2468&height=885)

### The whole process
First, I'd like to tell you that "just making http" requests is not going to be enough, Auth0 is smart, each process is guarded by a 
`state` token, which is a JWT token. This token is used to prevent CSRF attacks, and it's also used to prevent bots from logging in.
If you look at the `auth.py` file, there are over nine functions, each one of them is responsible for a different task, and they all
work together to create a token for you. `allow-redirects` played a huge role in this, as it allowed to navigate through the login process

I work at MeshMonitors.io, We make amazing tools (Check it out yo!). I decided not to spend too much time on this, but here we are, I have been able to reverse engineer the API and use a TLS client to mimic a real user, allowing the script to login without setting off any bot detection techniques by Auth0

### Why did I do this?
No one has been able to do this, and I wanted to see if I could.

### Credits
- [OpenAI](https://openai.com/) for creating the ChatGPT API
- [FlorianREGAZ](https://github.com/FlorianREGAZ) for the TLS Client
