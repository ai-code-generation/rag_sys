# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Code extraction utility for parsing code blocks from text responses."""

import re
import uuid
from typing import Dict, List, NamedTuple, Optional


class CodeBlock(NamedTuple):
    """Represents an extracted code block."""
    content: str
    language: Optional[str]
    start_line: int
    end_line: int


class ExtractedCode(NamedTuple):
    """Represents all extracted code from a response."""
    blocks: List[CodeBlock]
    has_code: bool
    total_blocks: int


class CodeExtractor:
    """Utility class for extracting code blocks from text responses."""
    
    # Language to file extension mapping
    LANGUAGE_EXTENSIONS = {
        'python': '.py',
        'py': '.py',
        'javascript': '.js',
        'js': '.js',
        'typescript': '.ts',
        'ts': '.ts',
        'java': '.java',
        'cpp': '.cpp',
        'c++': '.cpp',
        'c': '.c',
        'csharp': '.cs',
        'c#': '.cs',
        'go': '.go',
        'rust': '.rs',
        'php': '.php',
        'ruby': '.rb',
        'swift': '.swift',
        'kotlin': '.kt',
        'scala': '.scala',
        'r': '.r',
        'matlab': '.m',
        'shell': '.sh',
        'bash': '.sh',
        'sh': '.sh',
        'powershell': '.ps1',
        'sql': '.sql',
        'html': '.html',
        'css': '.css',
        'scss': '.scss',
        'sass': '.sass',
        'xml': '.xml',
        'json': '.json',
        'yaml': '.yaml',
        'yml': '.yml',
        'dockerfile': '.dockerfile',
        'makefile': '.makefile',
        'cmake': '.cmake',
        'gradle': '.gradle',
        'maven': '.xml',
        'terraform': '.tf',
        'hcl': '.hcl',
    }
    
    def __init__(self):
        """Initialize the code extractor."""
        # Pattern for fenced code blocks with optional language
        self.fenced_pattern = re.compile(
            r'```(?P<language>\w+)?\s*\n(?P<content>.*?)\n```',
            re.DOTALL | re.MULTILINE
        )
        
        # Pattern for indented code blocks (4+ spaces or 1+ tabs)
        self.indented_pattern = re.compile(
            r'^(?:    |\t).*$',
            re.MULTILINE
        )
        
        # Pattern for inline code (single backticks) - we'll skip these for file generation
        self.inline_pattern = re.compile(r'`([^`\n]+)`')
    
    def extract_code_blocks(self, text: str) -> ExtractedCode:
        """
        Extract all code blocks from the given text.
        
        Args:
            text: The text to extract code blocks from
            
        Returns:
            ExtractedCode object containing all found code blocks
        """
        blocks = []
        
        # Extract fenced code blocks (```language ... ```)
        blocks.extend(self._extract_fenced_blocks(text))
        
        # Extract indented code blocks (if no fenced blocks found)
        if not blocks:
            blocks.extend(self._extract_indented_blocks(text))
        
        return ExtractedCode(
            blocks=blocks,
            has_code=len(blocks) > 0,
            total_blocks=len(blocks)
        )
    
    def _extract_fenced_blocks(self, text: str) -> List[CodeBlock]:
        """Extract fenced code blocks (```language ... ```)."""
        blocks = []
        lines = text.split('\n')
        
        for match in self.fenced_pattern.finditer(text):
            language = match.group('language')
            content = match.group('content').strip()
            
            if not content:  # Skip empty code blocks
                continue
                
            # Find line numbers
            start_pos = match.start()
            start_line = text[:start_pos].count('\n') + 1
            end_line = start_line + content.count('\n')
            
            # Clean up language identifier
            if language:
                language = language.lower().strip()
            
            blocks.append(CodeBlock(
                content=content,
                language=language,
                start_line=start_line,
                end_line=end_line
            ))
        
        return blocks
    
    def _extract_indented_blocks(self, text: str) -> List[CodeBlock]:
        """Extract indented code blocks (4+ spaces or 1+ tabs)."""
        blocks = []
        lines = text.split('\n')
        current_block = []
        start_line = None
        
        for i, line in enumerate(lines):
            if self.indented_pattern.match(line):
                if start_line is None:
                    start_line = i + 1
                # Remove the indentation (4 spaces or 1 tab)
                if line.startswith('    '):
                    current_block.append(line[4:])
                elif line.startswith('\t'):
                    current_block.append(line[1:])
                else:
                    current_block.append(line)
            else:
                if current_block and start_line is not None:
                    content = '\n'.join(current_block).strip()
                    if content:  # Only add non-empty blocks
                        blocks.append(CodeBlock(
                            content=content,
                            language=None,  # No language info for indented blocks
                            start_line=start_line,
                            end_line=i
                        ))
                    current_block = []
                    start_line = None
        
        # Handle case where file ends with indented block
        if current_block and start_line is not None:
            content = '\n'.join(current_block).strip()
            if content:
                blocks.append(CodeBlock(
                    content=content,
                    language=None,
                    start_line=start_line,
                    end_line=len(lines)
                ))
        
        return blocks
    
    def get_file_extension(self, language: Optional[str]) -> str:
        """
        Get the appropriate file extension for a given language.
        
        Args:
            language: The programming language identifier
            
        Returns:
            File extension string (e.g., '.py', '.js')
        """
        if not language:
            return '.txt'  # Default extension for unknown languages
        
        language_lower = language.lower().strip()
        return self.LANGUAGE_EXTENSIONS.get(language_lower, '.txt')
    
    def generate_filename(self, language: Optional[str], block_index: int = 0) -> str:
        """
        Generate a unique filename for a code block.
        
        Args:
            language: The programming language identifier
            block_index: Index of the code block (for multiple blocks)
            
        Returns:
            Generated filename string
        """
        extension = self.get_file_extension(language)
        unique_id = str(uuid.uuid4())[:8]  # Short unique identifier
        
        if language:
            base_name = f"code_{language}_{block_index}_{unique_id}"
        else:
            base_name = f"code_block_{block_index}_{unique_id}"
        
        return f"{base_name}{extension}"
    
    def is_likely_code(self, text: str) -> bool:
        """
        Determine if text is likely to contain code based on heuristics.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text likely contains code
        """
        # Check for common code indicators
        code_indicators = [
            r'\bdef\s+\w+\s*\(',  # Python function definition
            r'\bfunction\s+\w+\s*\(',  # JavaScript function
            r'\bclass\s+\w+',  # Class definition
            r'\bimport\s+\w+',  # Import statement
            r'\bfrom\s+\w+\s+import',  # Python import
            r'#include\s*<',  # C/C++ include
            r'\bpublic\s+class',  # Java class
            r'{\s*$',  # Opening brace on its own line
            r'^\s*}',  # Closing brace
            r';\s*$',  # Semicolon at end of line
            r'=>',  # Arrow function
            r'\$\w+',  # Variable with $
        ]
        
        for pattern in code_indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
