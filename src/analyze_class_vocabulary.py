import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

df = pd.read_csv("data/processed/privacy_classification_matched.csv")

safe_texts = df.loc[df["label"] == 0, "text"]
sensitive_texts = df.loc[df["label"] == 1, "text"]


vectorizer = CountVectorizer(
    stop_words="english",
    max_features=1000
)

word_counts = vectorizer.fit_transform(df["text"])

feature_names = vectorizer.get_feature_names_out()

safe_counts = word_counts[df["label"].to_numpy() == 0].sum(axis=0)
sensitive_counts = word_counts[df["label"].to_numpy() == 1].sum(axis=0)


def show_top_words(counts, title, top_n=15):
    counts = counts.A1

    word_table = pd.DataFrame({
        "word": feature_names,
        "count": counts
    })

    word_table = word_table.sort_values(
        "count",
        ascending=False
    )

    print(f"\n{title}")
    print(word_table.head(top_n).to_string(index=False))


show_top_words(safe_counts, "TOP SAFE WORDS")
show_top_words(sensitive_counts, "TOP SENSITIVE WORDS")