import re

query = "title:información AND summary:recuperación AND NOT section-name:precisión"

pattern = r'(\b(?:AND|OR|NOT)\b|\w+[-\w]*:\s*[^:]+?(?=\s+\b(?:AND|OR|NOT)\b|$))'

tokens = re.findall(pattern, query, re.IGNORECASE)
print(tokens)