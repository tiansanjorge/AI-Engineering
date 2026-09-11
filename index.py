from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Generate a response from the OpenAI API
completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Escribime una frase creativa sobre el océano"}
    ],
    temperature=0.7,
    max_completion_tokens=100,
)

# Log the response
print(completion.choices[0].message.content)

# Log token usage
print(completion.usage)
