from datasets import load_dataset

dataset = load_dataset(
    "ai4privacy/pii-masking-micro-100k",
    split="train"
)

print(dataset)
print(dataset.column_names)
print(dataset[0])

print("\n DATASET CHECk")

total = len(dataset)

with_pii = sum(
    len(mask)> 0
    for mask in dataset["privacy_mask"]
)

without_pii = total - with_pii

print("Total rows:", total)
print("Rows with PII", with_pii)
print("rows without PII", without_pii)


from collections import Counter

language_counts = Counter(dataset["language"])

print("\nTop languages")
print(language_counts.most_common(10))