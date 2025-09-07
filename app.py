from flask import Flask, render_template, request, jsonify, send_from_directory
import re
import ast
import keyword
import os
import httpx
import json
import requests
try:
    from groq import Groq
except ImportError:
    Groq = None



app = Flask(__name__)

# Initialize cloud-based free AI models for web deployment
class CloudAIClient:
    def __init__(self):
        self.groq_client = None
        
        # Clear any proxy environment variables that might interfere
        for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            if proxy_var in os.environ:
                print(f"Removing proxy environment variable: {proxy_var}")
                os.environ.pop(proxy_var, None)
        
        groq_api_key = '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'
        if not groq_api_key:
            print("Warning: GROQ_API_KEY not found in environment variables")
            return
            
        try:
            # Try to initialize Groq client, but don't fail the entire app if it doesn't work
            if Groq is not None:
                # Clear all proxy-related environment variables that might interfere
                proxy_vars = ['http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY']
                for var in proxy_vars:
                    if var in os.environ:
                        print(f"Removing {var} from environment")
                        os.environ.pop(var, None)
                
                # Try to initialize with minimal parameters
                try:
                    # Import groq directly to avoid any import issues
                    import groq
                    
                    # Try to create client with explicit httpx configuration
                    import httpx
                    
                    # Create a custom httpx client without proxy settings
                    http_client = httpx.Client(
                        follow_redirects=True,
                        timeout=30.0
                    )
                    
                    self.groq_client = groq.Groq(
                        api_key=groq_api_key,
                        http_client=http_client
                    )
                    print("Groq client initialized successfully")
                    
                    # Test the connection
                    try:
                        models = self.groq_client.models.list()
                        print(f"Available models: {[model.id for model in models.data]}")
                    except Exception as e:
                        print(f"Warning: Could not list models: {e}")
                        
                except Exception as e:
                    print(f"Failed to initialize Groq client: {e}")
                    print("Continuing without AI features - using fallback explanations")
                    self.groq_client = None
            else:
                print("Groq library not available")
                self.groq_client = None
                
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            print("Continuing without AI features - using fallback explanations")
            self.groq_client = None
    
    def query_groq(self, prompt):
        """Query Groq API with streaming completions"""
        if not self.groq_client:
            print("Groq client not initialized")
            return None
            
        try:
            # Initialize empty response content
            full_response = []
            
            # Use compound-beta model specifically
            model_name = "compound-beta"
            try:
                models = self.groq_client.models.list()
                if hasattr(models, 'data') and models.data:
                    available_models = [model.id for model in models.data]
                    print(f"Available models: {available_models}")
                    if "compound-beta" in available_models:
                        model_name = "compound-beta"
                        print(f"Using compound-beta model")
                    else:
                        # Find a suitable alternative model that doesn't require terms acceptance
                        suitable_models = [m for m in available_models if 'llama' in m.lower() or 'gpt' in m.lower() or 'gemma' in m.lower()]
                        if suitable_models:
                            model_name = suitable_models[0]
                            print(f"compound-beta not available, using {model_name}")
                        else:
                            model_name = available_models[0] if available_models else "compound-beta"
            except Exception as e:
                print(f"Warning: Could not list models, using compound-beta: {e}")
            
            print(f"Using model: {model_name}")
            
            # Prepare the messages
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful code explanation assistant. Explain code clearly and simply for beginners. Also review the code and list likely bugs, errors, edge cases, and performance issues. Use HTML formatting with <h1> to <h6> tags and <b> tags. Include a <h2>Potential Issues / Bugs</h2> section if any."
                },
                {
                    "role": "user",
                    "content": f"Explain this code step by step in detail. Break down each part and explain what it does. Detect bugs and risks. Use HTML (<h1>-<h6>, <b>). Provide a <h2>Potential Issues / Bugs</h2> list if found.\n\nCode:\n```\n{prompt}\n```"
                }
            ]
            
            print("Sending request to Groq API...")
            
            # Create streaming completion
            stream = self.groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                stream=True
            )
            
            print("Received streaming response...")
            
            # Process the streaming response
            for chunk in stream:
                try:
                    if hasattr(chunk, 'choices') and chunk.choices and hasattr(chunk.choices[0], 'delta'):
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            content = delta.content
                            full_response.append(content)
                            print(content, end='', flush=True)  # Stream to console
                except Exception as chunk_error:
                    print(f"\nError processing chunk: {chunk_error}")
                    continue
            
            # Combine all chunks into a single response
            result = "".join(full_response).strip()
            print(f"\nGroq API response received ({len(result)} chars)")
            if not result:
                print("Warning: Empty response from Groq API")
            return result if result else None
            
        except Exception as e:
            print(f"Groq API error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return None
    
    
    def generate_explanation(self, prompt):
        """Generate explanation using Groq API with fallback"""
        print(f"Generating explanation for prompt of length: {len(prompt)}")
        
        # Try Groq API
        try:
            result = self.query_groq(prompt)
            if result and len(result) > 10:  # Ensure we got a meaningful response
                print(f"Successfully generated AI explanation ({len(result)} chars)")
                return result
            else:
                print(f"AI response was empty or too short. Response: '{result}'")
        except Exception as e:
            print(f"Error during AI explanation: {str(e)}")
            print(f"Error type: {type(e).__name__}")
        
        # Fallback to simple template-based response
        print("Falling back to simple explanation")
        return self.generate_simple_explanation(prompt)
    
    def generate_simple_explanation(self, prompt):
        """Fallback explanation generator"""
        if "python" in prompt.lower():
            return "This Python code performs various operations including function definitions, variable assignments, and control flow statements."
        elif "javascript" in prompt.lower():
            return "This JavaScript code contains function declarations, variable assignments, and DOM manipulation or logic operations."
        else:
            return "This code contains various programming constructs and performs specific operations."

ai_client = CloudAIClient()

class CodeAnalyzer:
    def __init__(self):
        self.python_keywords = keyword.kwlist
        self.js_keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 'class', 'async', 'await']
        self.use_ai = ai_client.groq_client is not None  # Only use AI if Groq client is available
        # Basic patterns for additional languages (heuristic)
        self.language_patterns = {
            'python': [
                r'def\s+\w+\s*\(', r'import\s+\w+', r'from\s+\w+\s+import', r'if\s+__name__\s*==\s*["\']__main__["\']', r'print\s*\('
            ],
            'javascript': [
                r'function\s+\w+\s*\(', r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'var\s+\w+\s*=', r'console\.log\s*\(', r'=>\s*\{'
            ],
            'typescript': [
                r'interface\s+\w+', r'type\s+\w+\s*=', r'\w+<\w+>', r':\s*\w+', r'private\s+\w+', r'public\s+\w+'
            ],
            'java': [
                r'public\s+(class|static|void)', r'package\s+[\w\.]+;', r'import\s+[\w\.\*]+;', r'new\s+\w+\s*\('
            ],
            'csharp': [
                r'using\s+\w+(\.\w+)*;', r'namespace\s+\w+', r'class\s+\w+\s*\{', r'public\s+(class|static|void)'
            ],
            'cpp': [
                r'#include\s+<\w+\.h?>', r'std::\w+', r'int\s+main\s*\(', r'cout\s*<<'
            ],
            'c': [
                r'#include\s+<\w+\.h>', r'int\s+main\s*\(', r'printf\s*\('
            ],
            'go': [
                r'package\s+\w+', r'func\s+\w+\s*\(', r'import\s*\(', r'fmt\.Print'
            ],
            'ruby': [
                r'def\s+\w+', r'end\s*$', r'puts\s+"', r'module\s+\w+'
            ],
            'php': [
                r'<\?php', r'echo\s+\$\w+', r'function\s+\w+\s*\(', r'\$\w+\s*='
            ],
            'rust': [
                r'fn\s+\w+\s*\(', r'let\s+mut\s+\w+', r'println!\s*!?\s*\(', r'pub\s+\w+'
            ],
            'kotlin': [
                r'fun\s+\w+\s*\(', r'val\s+\w+\s*:', r'var\s+\w+\s*:', r'data\s+class\s+\w+'
            ],
            'swift': [
                r'func\s+\w+\s*\(', r'let\s+\w+\s*=', r'var\s+\w+\s*=', r'import\s+\w+'
            ],
            'sql': [
                r'SELECT\s+\*?\s*FROM', r'INSERT\s+INTO', r'UPDATE\s+\w+\s+SET', r'DELETE\s+FROM'
            ],
            'bash': [
                r'^#!/bin/bash', r'\becho\b', r'\bif\s+\[', r'\bfor\s+\w+\s+in\b'
            ],
            'html': [
                r'<html', r'<div', r'<span', r'<script', r'<!DOCTYPE'
            ],
            'css': [
                r'\.[\w-]+\s*\{', r'#[\w-]+\s*\{', r'@media\s+', r'@keyframes\s+'
            ],
        }
    
    def detect_language(self, code):
        """Detect programming language based on syntax patterns across many languages."""
        code = code.strip()
        best_language = 'unknown'
        best_score = 0
        for language_name, patterns in self.language_patterns.items():
            score = sum(1 for pattern in patterns if re.search(pattern, code, re.MULTILINE | re.IGNORECASE))
            if score > best_score:
                best_language = language_name
                best_score = score
        return best_language
    
    def analyze_code_with_ai(self, code, language):
        """Analyze code using AI and return formatted explanation"""
        try:
            prompt = f"Analyze this {language} code and provide a detailed explanation:\n\n{code}"
            explanation = ai_client.generate_explanation(prompt)
            
            if not explanation:
                raise ValueError("No explanation generated by AI")
                
            # Format the response to match the expected structure
            return {
                'language': language,
                'overall_explanation': explanation,
                'line_explanations': [
                    {
                        'line_number': i + 1,
                        'code': line,
                        'explanation': ""  # AI provides overall explanation
                    }
                    for i, line in enumerate(code.split('\n'))
                    if line.strip()
                ]
            }
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            # Fall back to non-AI analysis
            if language == 'python':
                return self.analyze_python_code_fallback(code)
            elif language == 'javascript':
                return self.analyze_javascript_code_fallback(code)
            else:
                return self.analyze_generic_code_fallback(code, language)

    def analyze_code_with_ai_with_language(self, code, language, answer_language: str = 'english'):
        """Analyze code using AI and request the answer in the selected language (english/hinglish)."""
        try:
            lang_pref = (answer_language or 'english').strip().lower()
            if lang_pref not in ['english', 'hinglish']:
                lang_pref = 'english'
            lang_instruction = (
                'Write the explanation in Hinglish (mix Hindi + English), simple and friendly.'
                if lang_pref == 'hinglish' else
                'Write the explanation in clear, simple English.'
            )

            prompt = (
                f"Analyze this {language} code and provide a detailed explanation. {lang_instruction} "
                f"Use HTML headings (<h1>-<h6>) and <b> for emphasis.\n\nCode:\n{code}"
            )
            explanation = ai_client.generate_explanation(prompt)

            if not explanation:
                raise ValueError("No explanation generated by AI")

            return {
                'language': language,
                'overall_explanation': explanation,
                'line_explanations': [
                    {
                        'line_number': i + 1,
                        'code': line,
                        'explanation': ""
                    }
                    for i, line in enumerate(code.split('\n'))
                    if line.strip()
                ]
            }
        except Exception as e:
            print(f"AI analysis (with language) failed: {e}")
            if language == 'python':
                result = self.analyze_python_code_fallback(code)
            elif language == 'javascript':
                result = self.analyze_javascript_code_fallback(code)
            else:
                result = self.analyze_generic_code_fallback(code, language)

            if (answer_language or '').lower() == 'hinglish':
                result['overall_explanation'] = (
                    f"<h3>Short Summary (Hinglish)</h3> Yeh {language} code kuch operations karta hai aur logical steps follow karta hai. "
                    f"Neeche line-by-line basic breakdown diya hai."
                )
            return result

    def analyze_generic_code_with_ai(self, code, language, answer_language: str = 'english'):
        """Generic AI analysis for any language with simple line echo."""
        return self.analyze_code_with_ai_with_language(code, language, answer_language)

    def analyze_generic_code_fallback(self, code, language):
        """Fallback generic analysis for unknown or other languages."""
        explanations = []
        lines = code.split('\n')
        potential_issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                continue
            explanations.append({
                'line_number': i,
                'code': stripped,
                'explanation': 'Code statement'
            })
            # Very simple heuristics
            if 'TODO' in stripped or 'FIXME' in stripped:
                potential_issues.append(f"Line {i}: Contains TODO/FIXME; might be incomplete work.")
            if '==' in stripped and 'if' in lines[i-1] if i-1 < len(lines) else False:
                pass
            if language in ['c', 'cpp'] and 'gets(' in stripped:
                potential_issues.append(f"Line {i}: uses gets(), which is unsafe; prefer fgets().")
            if language in ['python'] and 'eval(' in stripped:
                potential_issues.append(f"Line {i}: uses eval(); security risk if inputs are untrusted.")
            if language in ['javascript'] and 'innerHTML' in stripped and '=' in stripped:
                potential_issues.append(f"Line {i}: assigning to innerHTML may cause XSS if input is untrusted.")
        overall = f"This {language} code performs a series of operations."
        result = {
            'language': language,
            'overall_explanation': overall,
            'line_explanations': explanations
        }
        if potential_issues:
            result['potential_issues'] = potential_issues
        return result
    
    def analyze_python_code(self, code, answer_language: str = 'english'):
        """Analyze Python code and generate explanations"""
        if self.use_ai:
            return self.analyze_code_with_ai_with_language(code, 'python', answer_language)
        
        return self.analyze_python_code_fallback(code)
    
    def analyze_python_code_fallback(self, code):
        """Fallback Python analysis without AI"""
        explanations = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            explanation = self.explain_python_line(line)
            if explanation:
                explanations.append({
                    'line_number': i,
                    'code': line,
                    'explanation': explanation
                })
        
        # Overall function analysis
        overall = self.get_python_overview(code)
        
        return {
            'language': 'python',
            'overall_explanation': overall,
            'line_explanations': explanations
        }
    
    def explain_python_line(self, line):
        """Generate explanation for a single Python line"""
        line = line.strip()
        
        if line.startswith('def '):
            func_name = re.search(r'def\s+(\w+)', line)
            if func_name:
                return f"Defines a function named '{func_name.group(1)}'"
        
        elif line.startswith('class '):
            class_name = re.search(r'class\s+(\w+)', line)
            if class_name:
                return f"Defines a class named '{class_name.group(1)}'"
        
        elif line.startswith('import ') or line.startswith('from '):
            return "Imports external libraries or modules"
        
        elif line.startswith('if '):
            return "Conditional statement - executes code if condition is true"
        
        elif line.startswith('elif '):
            return "Alternative condition - checks this if previous conditions were false"
        
        elif line.startswith('else:'):
            return "Default case - executes if all previous conditions were false"
        
        elif line.startswith('for '):
            return "Loop statement - repeats code for each item in a sequence"
        
        elif line.startswith('while '):
            return "Loop statement - repeats code while condition is true"
        
        elif line.startswith('return '):
            return "Returns a value from the function"
        
        elif line.startswith('print('):
            return "Outputs text or values to the console"
        
        elif '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
            var_name = line.split('=')[0].strip()
            return f"Assigns a value to variable '{var_name}'"
        
        else:
            return "Executes a statement or expression"
    
    def analyze_javascript_code(self, code, answer_language: str = 'english'):
        """Analyze JavaScript code and generate explanations"""
        if self.use_ai:
            return self.analyze_code_with_ai_with_language(code, 'javascript', answer_language)
        
        return self.analyze_javascript_code_fallback(code)
    
    def analyze_javascript_code_fallback(self, code):
        """Fallback JavaScript analysis without AI"""
        explanations = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            explanation = self.explain_javascript_line(line)
            if explanation:
                explanations.append({
                    'line_number': i,
                    'code': line,
                    'explanation': explanation
                })
        
        # Overall function analysis
        overall = self.get_javascript_overview(code)
        
        return {
            'language': 'javascript',
            'overall_explanation': overall,
            'line_explanations': explanations
        }
    
    def explain_javascript_line(self, line):
        """Generate explanation for a single JavaScript line"""
        line = line.strip()
        
        if line.startswith('function '):
            func_name = re.search(r'function\s+(\w+)', line)
            if func_name:
                return f"Defines a function named '{func_name.group(1)}'"
        
        elif re.match(r'const\s+\w+\s*=', line):
            var_name = re.search(r'const\s+(\w+)', line)
            if var_name:
                return f"Declares a constant variable '{var_name.group(1)}'"
        
        elif re.match(r'let\s+\w+\s*=', line):
            var_name = re.search(r'let\s+(\w+)', line)
            if var_name:
                return f"Declares a block-scoped variable '{var_name.group(1)}'"
        
        elif re.match(r'var\s+\w+\s*=', line):
            var_name = re.search(r'var\s+(\w+)', line)
            if var_name:
                return f"Declares a variable '{var_name.group(1)}'"
        
        elif line.startswith('if '):
            return "Conditional statement - executes code if condition is true"
        
        elif line.startswith('else if '):
            return "Alternative condition - checks this if previous conditions were false"
        
        elif line.startswith('else'):
            return "Default case - executes if all previous conditions were false"
        
        elif line.startswith('for '):
            return "Loop statement - repeats code for each iteration"
        
        elif line.startswith('while '):
            return "Loop statement - repeats code while condition is true"
        
        elif line.startswith('return '):
            return "Returns a value from the function"
        
        elif 'console.log(' in line:
            return "Outputs text or values to the browser console"
        
        elif '=>' in line:
            return "Arrow function - a concise way to write functions"
        
        else:
            return "Executes a statement or expression"
    
    def get_python_overview(self, code):
        """Generate overall explanation for Python code"""
        if 'def ' in code:
            return "This Python code defines one or more functions with specific functionality."
        elif 'class ' in code:
            return "This Python code defines a class with methods and properties."
        elif 'for ' in code or 'while ' in code:
            return "This Python code contains loops to repeat operations."
        else:
            return "This Python code performs a series of operations and calculations."
    
    def get_javascript_overview(self, code):
        """Generate overall explanation for JavaScript code"""
        if 'function ' in code or '=>' in code:
            return "This JavaScript code defines one or more functions with specific functionality."
        elif 'document.' in code:
            return "This JavaScript code manipulates HTML elements on a web page."
        elif 'async' in code or 'await' in code:
            return "This JavaScript code handles asynchronous operations."
        else:
            return "This JavaScript code performs a series of operations and calculations."
    
    def estimate_complexity(self, code, language):
        """Very simple heuristic-based Big-O estimator (time/space) with notes."""
        try:
            normalized = code if isinstance(code, str) else str(code)
            # strip strings to avoid false positives
            normalized = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"]*"|\'[^\']*\'', '', normalized)
            lower = normalized.lower()
            time_c = "O(1)"
            space_c = "O(1)"
            notes = []
            
            # Loop counts
            loop_count = len(re.findall(r'\bfor\b|\bwhile\b', lower))
            
            # Nested loop heuristic (basic)
            nested2 = bool(re.search(r'\b(for|while)\b[\s\S]*?\n[\t ]+.*\b(for|while)\b', normalized))
            nested3 = bool(re.search(r'(\b(for|while)\b[\s\S]*?\n[\t ]+.*){2}\b(for|while)\b', normalized))
            
            # Recursion heuristic (function name called inside itself)
            func_names = set()
            if language == 'python':
                func_names |= set(re.findall(r'\bdef\s+(\w+)\s*\(', normalized))
            if language in ['javascript', 'typescript']:
                func_names |= set(re.findall(r'\bfunction\s+(\w+)\s*\(', normalized))
            if language in ['c', 'cpp', 'java', 'csharp', 'go', 'rust', 'kotlin', 'swift']:
                func_names |= set(re.findall(r'\b(\w+)\s*\([^;{)]*\)\s*\{', normalized))
            recursive = False
            for name in func_names:
                if re.search(r'\b' + re.escape(name) + r'\s*\(', normalized.split(name, 1)[-1]):
                    recursive = True
                    break
            
            # Sorting / divide-and-conquer hints
            if re.search(r'\bsort(ed)?\s*\(', lower) or '.sort(' in lower:
                time_c = "O(n log n)"
                notes.append("Detected sorting; typical time O(n log n)")
            
            # Determine time complexity from loops/recursion if not already n log n
            if time_c == "O(1)":
                if nested3:
                    time_c = "O(n^3)"
                    notes.append("Detected triple-nested loops (heuristic)")
                elif nested2:
                    time_c = "O(n^2)"
                    notes.append("Detected nested loops (heuristic)")
                elif loop_count >= 1 or recursive:
                    time_c = "O(n)"
                    if recursive:
                        notes.append("Detected possible recursion; assuming linear for typical cases")
            
            # Space complexity heuristic
            # If we see list/array building, maps, or pushes, assume O(n)
            if re.search(r'\bappend\(|\bextend\(|\bpush\(|\bmap\(|\bfilter\(|\bnew\s+Array\b|\[[^\]]*\]', lower):
                space_c = "O(n)"
            
            return {
                'time': time_c,
                'space': space_c,
                'notes': notes
            }
        except Exception:
            return {
                'time': 'O(?)',
                'space': 'O(?)',
                'notes': ['Failed to estimate complexity']
            }
    
    def improve_code(self, code, language, answer_language: str = 'english'):
        """Suggest improvements and propose an optimized version of the code.
        Uses AI when available; otherwise returns heuristic suggestions and original code.
        """
        if self.use_ai:
            try:
                lang_label = language or 'code'
                lang_hint = 'Write tips in clear, simple English.' if (answer_language or 'english').lower() == 'english' else 'Write tips in simple and friendly Hinglish.'
                prompt = (
                    f"Improve the following {lang_label} for readability, performance, and best practices. "
                    f"{lang_hint} Keep functionality identical.\n"
                    "Return concise bullet tips first, then the improved code in a fenced block with the correct language tag.\n\n"
                    f"Code:\n```{language}\n{code}\n```"
                )
                resp = ai_client.generate_explanation(prompt) or ''
                # extract first fenced code block
                m = re.search(r'```[a-zA-Z0-9_+\-]*\n([\s\S]*?)```', resp)
                improved = m.group(1).strip() if m else code
                tips = re.sub(r'```[\s\S]*?```', '', resp).strip()
                return {
                    'language': language,
                    'improved_code': improved,
                    'tips': tips
                }
            except Exception as e:
                print(f"AI improve failed: {e}")
                # fall through to heuristic
        # Heuristic fallback suggestions
        tips = []
        if language == 'python':
            if 'print(' in code and 'logging' not in code:
                tips.append("Use the logging module instead of print() for production code.")
            if ' + ' in code and ('"' in code or "'" in code):
                tips.append("Prefer f-strings for string formatting (Python 3.6+).")
        if language in ['javascript', 'typescript']:
            if re.search(r'\bvar\s+', code):
                tips.append("Prefer let/const over var.")
            if '==' in code and '===' not in code:
                tips.append("Use strict equality (===) when appropriate.")
        if language in ['c', 'cpp']:
            tips.append("Avoid gets(), prefer fgets(); check all return values.")
        if not tips:
            tips.append("Apply consistent formatting and naming conventions.")
        return {
            'language': language,
            'improved_code': code,
            'tips': "\n- " + "\n- ".join(tips)
        }
    
analyzer = CodeAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_code():
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        # Detect language
        language = analyzer.detect_language(code)
        
        # Optional answer language (english or hinglish)
        answer_language = (data.get('answer_language') or 'english').lower()
        if answer_language not in ['english', 'hinglish']:
            answer_language = 'english'

        if language == 'python':
            result = analyzer.analyze_python_code(code, answer_language)
        elif language == 'javascript':
            result = analyzer.analyze_javascript_code(code, answer_language)
        else:
            # Use AI for other languages when available; otherwise generic fallback
            if analyzer.use_ai:
                result = analyzer.analyze_generic_code_with_ai(code, language, answer_language)
            else:
                result = analyzer.analyze_generic_code_fallback(code, language)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/complexity', methods=['POST'])
def complexity():
    try:
        data = request.get_json()
        code = (data or {}).get('code', '').strip()
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        language = analyzer.detect_language(code)
        result = analyzer.estimate_complexity(code, language)
        result['language'] = language
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Complexity analysis failed: {str(e)}'}), 500

@app.route('/improve', methods=['POST'])
def improve():
    try:
        data = request.get_json()
        code = (data or {}).get('code', '').strip()
        answer_language = (data or {}).get('answer_language') or 'english'
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        language = analyzer.detect_language(code)
        result = analyzer.improve_code(code, language, answer_language)
        result['language'] = language
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Improve failed: {str(e)}'}), 500

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon from the project logo."""
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'img'),
        'icon.png',
        mimetype='image/png',
        cache_timeout=0
    )

# Test route to verify static file serving
@app.route('/test-icon')
def test_icon():
    return f"""
    <html>
    <head>
        <title>Test Icon</title>
        <link rel="icon" type="image/png" href="{{{{ url_for('static', filename='img/icon.png') }}}}">
    </head>
    <body>
        <h1>Test Icon Page</h1>
        <p>Check if the favicon appears in your browser tab.</p>
        <p>Direct link to icon: <a href="{{{{ url_for('static', filename='img/icon.png') }}}}">icon.png</a></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0' , debug=True)
