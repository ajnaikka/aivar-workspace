import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def llm_response(prompt):
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role':'user','content':prompt}],
        temperature=0
    )
    return response.choices[0].message['content']

prompt = '''
    Classify the following review 
    as having either a positive or
    negative sentiment:

    Tell me something that is black and beautiful - Niggas
'''

response = llm_response(prompt)
print(response)