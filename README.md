# Dis.AI

Dis.AI is a Discord bot that allows you to create your own, fully personalized chatbots with long term memory. With Dis.AI, you can customize prompts, chat with PDFs & YouTube videos, search the web, have chatbots converse with each other, and much more!

<p align="center">
  <img width="200" height="200" src="https://github.com/jacobjude/Dis.AI/assets/118640159/7379714b-db37-4d81-84b3-09be3bf5de1a">
</p>

Note: The official Dis.AI bot is no longer operational. Thank you to everyone that used the bot and made it happen!

A few statistics that Dis.AI accrewed over its ~2 month run:
- [Over 179,000 active users across over 1000 servers](https://raw.githubusercontent.com/jacobjude/Dis.AI/main/DisAIstats.png)
- [1866 total servers](https://raw.githubusercontent.com/jacobjude/Dis.AI/main/SomeMoreStats.png) joined.
- Over [**1.1 million** GPT responses sent in a single month](https://raw.githubusercontent.com/jacobjude/Dis.AI/main/SomeMoreStats.png) (July 28th, 2023 - August 28th, 2023)
- Over[ 1,000 monthly votes](https://raw.githubusercontent.com/jacobjude/Dis.AI/main/DisAITopggStats.png) and [8 very kind (five-star) reviews](https://github.com/jacobjude/Dis.AI/blob/main/top.gg%20reviews.png) on top.gg :)


## Table of Contents
- [Commands](#commands)
- [Chatbot settings](#settings-options)
- [Other Features](#other-features)
- [Showcase](#showcase)
- [Contact](#contact)
- [License](#license)

#
### Fully customizable  🎨
- Customize the prompt, chat with PDFs & YouTube videos, search the web, have chatbots converse with each other, and so much more!

### Free to use✨
- No sign-ups or registrations; all features are completely free to use.

### Private  🥷
- Your conversations are never used for any data collection or training.

### and more...  (see below)🔥

## Commands
- `/create`: Creates a new chatbot.
- `/enable & /disable`: Enables/disables the specified chatbot in the current channel.
- `/settings`: Change the settings for a chatbot.
- `/conversation`: Make chatbots converse with each other.
- `/chatbotinfo`: View all settings for the specified chatbot.
- `/showenabledhere`: Shows all chatbots that are enabled in the current channel.
- `/listchatbots`: View all created chatbots.
- `/clearmemory`: Clears the specified chatbot's memory. (Optional: choose # of messages to delete)
- `/viewmemory`: View the memory of the specified chatbot.
- `/forcemessage`: Force a message from a chatbot.
- `/adminroles`: If admin roles are set, only users with admin roles can modify Dis.AI chatbots.
- `/credits`: View and purchase Dis.AI Credits.
- `/help`: Show the help page.
- `/vote`: Vote for Dis.AI to earn free credits.
- `/claim`: Claim free Dis.AI credits.

## Settings Options
- 📚 `Prompt Library`: Customize your chatbot's personality, instructions, and more.
- ➕ `Add Long Prompt`: Bypass Discord's character limit for prompts by uploading a .txt file.
- ✏️ `Edit Avatar`: Edit the avatar of the chatbot.
- 👥 `Include Usernames`: Allows chatbots to understand usernames.
- 📄/🎥 `PDF / YouTube Video`: Let your chatbot summarize and answer questions from a PDF or YouTube video.
- 📣 `Mention Mode`: If enabled, the chatbot will only respond if it's mentioned.
- 🧠 `Long Term Memory`: Enable or disable long term memory.
- 🌐 `Web Search`: Toggle auto web search.
- 🔄 `Toggle reactions`: Enable or disable the regenerate/continue buttons that appear at the end of chatbot responses.
- 📖 `Lorebooks`: Access the lorebooks for additional information.
- 🤖 `GPT Model`: Choose between GPT-3.5 or GPT-4 for your responses.
- 💉 `Inject Message`: Inject a message into the chatbot's conversation.
- 🔧 `Temperature`: A value that modifies the "randomness" of the output.
- 🔧 `Presence Penalty`: Penalize new tokens based on whether they appear in the text so far.
- 🔧 `Frequency Penalty`: Penalize new tokens based on their existing frequency in the text so far.
- 🔧 `Top P`: An alternative to temperature.

## Other Features
- A `credit system` in which users could vote or purchase credits to be able to use the bot. Payments were processed through the Stripe API.
- A `voting system` in which users could vote for Dis.AI on Top.GG (a Discord bot listing site) and be rewarded with credits. Votes were processed with the Top.GG API.
- `Long term memory` uses the Pinecone and OpenAI APIs to generate an embedding and upsert it to a vector DB.
- `Regenerate, continue, and delete reactions` that appear below chatbot responses to easily control outputs.
- Enable multiple chatbots in one channel for a dynamic `group conversation` where they understand and respond to each other based on mentions.
- Collected `usage statistics and analytics` that detailed exactly what commands and features users were using and when.
- Stored user information with `MongoDB`
  

## Preview
![image](https://github.com/jacobjude/Dis.AI/assets/118640159/8eef85de-c583-43b3-b860-35221005a179)
![image](https://github.com/jacobjude/Dis.AI/assets/118640159/57f046b5-decd-4f6e-b498-ec4a115c3771)
![image](https://github.com/jacobjude/Dis.AI/assets/118640159/dfca0898-1bda-4252-a5f8-d2d86aab666c)

(Note: The UI in this video is pretty old; the current version's UI is much improved.)

[Video showcase](https://github.com/jacobjude/Dis.AI/assets/118640159/b3f98f46-a355-42db-97cf-d89d9a0aab95)

## Contact
If you have any questions or need support, feel free to contact us at my [email.](mailto:jacob.jude03@gmail.com).

## License
This project is licensed under the [Apache License 2.0](LICENSE).
