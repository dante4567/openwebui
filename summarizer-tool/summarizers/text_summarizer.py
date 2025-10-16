import os
from openai import OpenAI
from .base import BaseSummarizer

# Use LiteLLM or OpenAI API
API_BASE_URL = os.environ.get('OPENAI_API_BASE', 'http://litellm:4000/v1')
API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-1234')  # LiteLLM doesn't validate
MODEL = os.environ.get('MODEL', 'gpt-4o-mini')

SUMMARIZE_PROMPT = """You are a summarizing agent.
It is your job to responsibly capture the entirety of what is being described in incoming documents.
You can skip small details, but you must make sure to hit all the major points.
These summaries will be used for GTD reference filing and RAG.

Rules:
- Always sanitize data and remove unnecessary newlines
- Never mention yourself in summaries
- Never infer, only summarize what is presented
- Never describe the text as "summarized" - just give the summary
- Be concise but comprehensive
- Focus on actionable information and key points

Example 1:
Input: "I've got updates on the tiny brains...brain organoids...can grow them...hook them up to a computer..."
Output: "Brain organoids (tiny human brains grown from stem cells) can be grown in jars or connected to computers for industrial use via FinalSpark."

Example 2:
Input: "hi, i'm isopod (formerly hornet) i'm a software engineer i write code, make costumes, and write music"
Output: "Isopod (formerly hornet) is a software engineer who writes code, makes costumes, and composes music."
"""

class TextSummarizer(BaseSummarizer):
    def __init__(self):
        self.client = OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY
        )

    def summarize(self, data):
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SUMMARIZE_PROMPT},
                    {"role": "user", "content": f"Summarize the following text:\n\n{data}"}
                ],
                temperature=0.5,
                max_tokens=500
            )

            summary = response.choices[0].message.content

            return {
                'type': 'text',
                'source': API_BASE_URL,
                'content': summary
            }

        except Exception as e:
            print(f"Error: {e}")
            return {
                'type': 'text',
                'source': API_BASE_URL,
                'error': str(e)
            }


