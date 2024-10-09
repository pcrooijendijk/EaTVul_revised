from transformers import AutoModelForCausalLM, AutoTokenizer

def generate_adv_snippet(prompt):
    # Load a pre-trained GPT-like model from Hugging Face
    model_name = "gpt2"  # You can replace this with models like "EleutherAI/gpt-neo-1.3B" or other code-specific models
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    # Tokenize input
    inputs = tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True)
    
    # Generate response
    outputs = model.generate(inputs.input_ids, max_length=1000, temperature=0.7, num_return_sequences=1)
    
    # Decode the output to text
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    return generated_text

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
        answer = generate_adv_snippet(new_prom)
        adv_snippets.append(answer)
    
    return adv_snippets

# Example usage
content = [{'prompt': "print('Hello World')\n"}]
pre_context = ['def hello():']
post_context = ['# Call the function']

new_prompts = generate_new_prompt(content, pre_context, post_context)
adv_snippets = save_adv_snippet(new_prompts)
print(adv_snippets)
