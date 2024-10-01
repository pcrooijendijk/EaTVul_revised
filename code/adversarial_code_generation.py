import openai
from openai import OpenAI
import os

openai.api_key = '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'

client = OpenAI(
    api_key = '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'
,
)

def generate_adv_snippet(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = [{"role": "user", "content": prompt}],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.7,
    )
    answer = response.choices[0]["message"]["content"].strip()
    return answer

def generate_new_prompt(content, pre_context, post_context):

    new_prompts = []

    for idx in range(len(content)):
      prompt = content[idx]['prompt'].replace('\n', '').replace('\r', '')
      pre_con = pre_context[idx]
      post_con = post_context[idx]
      front_context = "With the partial preceding codes provided as:"
      end_context = "and with the partial following codes provided as"
      new_promp = front_context + pre_con + ". " + prompt + " " + end_context + post_con
      new_promp = new_promp.replace(r' """ ', "")
      new_prompts.append(new_promp)

    return new_prompts

def save_adv_snippet(new_prompts):
    adv_snippets = []

    for new_prom in new_prompts:
        message = [{ "role": "system", "content": "You are an experienced programmer." },
                {"role": "user", "content":new_prom},]
        answer = generate_adv_snippet(message)
        adv_snippets.append(answer)
    return adv_snippets

content = [{'prompt':"print('Hello World')\n"}]
pre_context = ['def hello():']
post_context = ['# Call the function']

prompt = "Please generate a function in C that contains a loop, two structs named a_chan and b_const, and define a static const char named a_rray initialized with NULL."

def chat_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# print(generate_adv_snippet(prompt))
chat_gpt(prompt)