import random
import pandas as pd

random.seed(42)

names = ["alex", "sam", "taylor", "jordan", "casey"]
domains = ["example.com", "example.org", "example.net"]

safe_templates = [
    "How can I change my email address?",
    "Can I update my contact email?",
    "Where do I manage my email settings?"
]

sensitive_templates = [
    "My email address is {email}.",
    "Please send the confirmation to {email}.",
    "You can contact me at {email}."
]



template_pairs = [
    (
        "Please update my email address for {context}.",
        "Please update my email address for {context} to {email}."
    ),
    (
        "My contact email for {context} needs changing.",
        "My contact email for {context} is {email}."
    ),
    (
        "I want to verify my email address for {context}.",
        "I want to verify {email} for {context}."
    )
]

contexts = [
    "my banking profile",
    "my shopping account",
    "the mobile application",
    "my travel booking",
    "my work account"
]

rows = []

for i in range (len(template_pairs)*len(contexts)):
    template_id = i % len(template_pairs)
    context_id = i // len(template_pairs)
    safe_template, sensitive_template = template_pairs[template_id]
    context = contexts[context_id]

    name = random.choice(names)
    domain = random.choice(domains)
    email = f"{name}{i}@{domain}"

    safe_text = safe_template.format(context=context)

    sensitive_text = sensitive_template.format(
        context=context,
        email=email
    )

    for label, text in [(0, safe_text), (1, sensitive_text)]:
        rows.append({
            "group_id": i,
            "template_id": template_id,
            "category": "email",
            "text": text,
            "label": label
        })
    
df = pd.DataFrame(rows)

print("Dataset shape:", df.shape)

print("\nClass distribution:")
print(df["label"].value_counts().sort_index())

print("\nDuplicate texts:")
print(df["text"].duplicated().sum())

print("\nSample examples:")
print(df.head(6).to_string(index=False))



print("\n Examples per template:")
print(pd.crosstab(df["template_id"], df["label"]))

print("\n Duplicates texts:")
print(df["text"].duplicated().sum())