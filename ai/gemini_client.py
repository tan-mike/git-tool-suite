"""
Gemini AI Client for Joke and Birthday features.
"""

import requests
import random
import datetime

from config import Config


class GeminiClient:
    def __init__(self):
        self.api_key = Config.get_api_key()
    
    def call_gemini(self, prompt):
        """Calls the Gemini REST API directly."""
        if not self.api_key:
            return "Error: API key is not configured."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if 'candidates' in data and data['candidates']:
                content = data['candidates'][0].get('content', {})
                if 'parts' in content and content['parts']:
                    return content['parts'][0].get('text', "Error: Could not parse response.")
            
            print("Warning: Gemini response contained no candidates. Full response:", data)
            return "Error: The AI returned an empty response."
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Gemini API call failed: {e}")
            return f"Error: Network error - {e}"
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")
            return "Error: An unexpected error occurred."
    
    def get_joke(self):
        """Generates a contextual joke based on time of day/week."""
        mixed_jokes = [
            "Tell a quick, playful joke that bridges tech and everyday humor. Keep it witty, concise, and easy to get.",
            "Make a fun, office-safe joke that could be shared between coworkers. Keep it witty, concise, and easy to get.",
            "Tell a smart, simple joke that could cheer someone up after a long day. Keep it witty, concise, and easy to get.",
            "Tell a short, clever joke that would make someone smile during a coffee break. Keep it witty, concise, and easy to get.",
            "Tell a wholesome, slightly quirky joke about daily life — nothing dark or slapstick. Keep it witty, concise, and easy to get.",
            "Tell a light, funny observation about human habits or work life. Keep it witty, concise, and easy to get.",
            "Tell a short,clever and quirky joke about friends that would make someone smile during a coffee break. Keep it witty, concise, and easy to get.",
        ]
        
        prompt = random.choice(mixed_jokes)
        return self.call_gemini(prompt)
    
    def get_birthday_message(self, name):
        """Generates a birthday message for the specified person."""
        prompt = f"Write a warm, friendly, and lightly humorous birthday message for {name}. Keep it wholesome, short (under 100 words), and make one witty reference to software development or clean code."
        return self.call_gemini(prompt)
    
    def generate_pr_content(self, diff_text, source_branch, target_branch):
        """
        Analyzes git diff and generates PR title and description.
        
        Args:
            diff_text: The git diff output
            source_branch: Name of the source branch
            target_branch: Name of the target branch
            
        Returns:
            dict with 'title' and 'description' keys, or None on error
        """
        if not diff_text or not diff_text.strip():
            return {
                'title': 'No changes detected',
                'description': 'The diff appears to be empty. Please check your branch selection.'
            }
        
        # Truncate very large diffs to avoid token limits
        max_diff_length = 8000
        if len(diff_text) > max_diff_length:
            diff_text = diff_text[:max_diff_length] + "\n\n... (diff truncated for analysis)"
        
        prompt = f"""Analyze this git diff and generate a pull request title and description.

Source Branch: {source_branch}
Target Branch: {target_branch}

Git Diff:
```
{diff_text}
```

Generate:
1. A concise, descriptive PR title (max 80 characters) that summarizes the main changes
2. A Summarised PR description with:
   - Brief summary of what changed
   - Key changes (bullet points)
   - Any notable implementation details

Format your response EXACTLY as:
TITLE: [your title here]
DESCRIPTION:
[your description here]

Keep it short, simple, professional and technical. Focus on what changed and why it matters."""

        response = self.call_gemini(prompt)
        
        # Parse the response
        if response.startswith("Error:"):
            return None
        
        try:
            # Extract title and description from response
            lines = response.strip().split('\n')
            title = ""
            description_lines = []
            in_description = False
            
            for line in lines:
                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                elif line.startswith("DESCRIPTION:"):
                    in_description = True
                elif in_description:
                    description_lines.append(line)
            
            description = '\n'.join(description_lines).strip()
            
            # Fallback if parsing fails
            if not title:
                title = "Update from " + source_branch
            if not description:
                description = response
            
            return {
                'title': title,
                'description': description
            }
        except Exception as e:
            print(f"ERROR parsing PR content: {e}")
            return None

    def generate_commit_message(self, diff_text):
        """
        Generates a commit message based on the provided diff.
        """
        if not diff_text or not diff_text.strip():
            return "No changes detected."
            
        # Truncate if too long
        max_len = 6000
        if len(diff_text) > max_len:
            diff_text = diff_text[:max_len] + "\n...(truncated)"
            
        prompt = f"""Generate a git commit message for this diff.
Follow Conventional Commits format (type(scope): subject).
Keep it concise.

Diff:
{diff_text}

Output ONLY the commit message.
"""
        return self.call_gemini(prompt).strip()
