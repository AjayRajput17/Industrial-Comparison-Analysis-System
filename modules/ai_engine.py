
import os
from groq import Groq
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file")

client = Groq(api_key=api_key)

def generate_comments(df, mode):
    if df.empty:
        return df

    comments = []

    for _, row in df.iterrows():
        if mode == "modified":
            prompt = f"Summarize changes: {row.get('CHANGES')}"
            try:
                res = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                comments.append(res.choices[0].message.content.strip())
            except:
                comments.append(str(row.get("CHANGES")))
        elif mode == "new":
            comments.append("Completely New Part Added")
        else:
            comments.append("Part Removed in New Report")

    df["COMMENTS"] = comments
    return df
