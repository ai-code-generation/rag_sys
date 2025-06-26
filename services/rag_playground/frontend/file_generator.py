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

"""File generation service for creating downloadable code files."""

import os
import tempfile
import time
import threading
import subprocess
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
import logging

from .code_extractor import CodeExtractor, ExtractedCode, CodeBlock

_LOGGER = logging.getLogger(__name__)

# Constants for S32DSGEN
S32_TRIGGER_PHRASE = "S32DSGEN"
SWTBOT_PROJECT_PATH = "/swtbot-example"
DEMO_TEST_RELATIVE_PATH = "src/test/java/com/fpt/ai/scripts"
DEMO_TEST_FILENAME = "DemoTest.java"


class GeneratedFile(NamedTuple):
    """Represents a generated code file."""
    filename: str
    filepath: str
    language: Optional[str]
    size: int
    created_at: float


class FileGenerationResult(NamedTuple):
    """Result of file generation operation."""
    files: List[GeneratedFile]
    success: bool
    message: str
    total_files: int


class FileGenerator:
    """Service for generating temporary code files from extracted code blocks."""
    
    def __init__(self, temp_dir: Optional[str] = None, cleanup_interval: int = 3600):
        """
        Initialize the file generator.
        
        Args:
            temp_dir: Directory for temporary files (defaults to system temp)
            cleanup_interval: Interval in seconds for cleaning up old files
        """
        self.temp_dir = temp_dir or os.path.join(tempfile.gettempdir(), "rag_playground_code")
        self.cleanup_interval = cleanup_interval
        self.code_extractor = CodeExtractor()
        self._generated_files: Dict[str, GeneratedFile] = {}
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Background worker for cleaning up old files."""
        while not self._stop_cleanup.wait(self.cleanup_interval):
            try:
                self._cleanup_old_files()
            except Exception as e:
                _LOGGER.error(f"Error during file cleanup: {e}")
    
    def _cleanup_old_files(self, max_age: int = 3600):
        """
        Clean up files older than max_age seconds.
        
        Args:
            max_age: Maximum age in seconds before files are deleted
        """
        current_time = time.time()
        files_to_remove = []
        
        for filename, file_info in self._generated_files.items():
            if current_time - file_info.created_at > max_age:
                try:
                    if os.path.exists(file_info.filepath):
                        os.remove(file_info.filepath)
                    files_to_remove.append(filename)
                    _LOGGER.debug(f"Cleaned up old file: {filename}")
                except Exception as e:
                    _LOGGER.error(f"Error removing file {filename}: {e}")
        
        # Remove from tracking
        for filename in files_to_remove:
            self._generated_files.pop(filename, None)
    
    def generate_files_from_response(self, response_text: str, user_query: str = "") -> FileGenerationResult:
        """
        Generate a single downloadable file from all code blocks in response text.

        Args:
            response_text: The complete response text to extract code from
            user_query: The original user query (for special handling)

        Returns:
            FileGenerationResult with information about generated file
        """
        try:
            # Check for special S32DSGEN handling
            if S32_TRIGGER_PHRASE in user_query:
                _LOGGER.info("S32DSGEN detected - using special handler")
                return self._handle_s32_demo_hackathon(response_text)

            # Extract code blocks
            extracted_code = self.code_extractor.extract_code_blocks(response_text)

            if not extracted_code.has_code:
                return FileGenerationResult(
                    files=[],
                    success=True,
                    message="No code blocks found in response",
                    total_files=0
                )

            # Generate a single combined file
            try:
                generated_file = self._create_combined_file(extracted_code.blocks)
                if generated_file:
                    self._generated_files[generated_file.filename] = generated_file
                    return FileGenerationResult(
                        files=[generated_file],
                        success=True,
                        message=f"Successfully generated combined code file with {extracted_code.total_blocks} code blocks",
                        total_files=1
                    )
                else:
                    return FileGenerationResult(
                        files=[],
                        success=False,
                        message="Failed to generate combined code file",
                        total_files=0
                    )
            except Exception as e:
                _LOGGER.error(f"Error generating combined file: {e}")
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message=f"Error generating combined file: {str(e)}",
                    total_files=0
                )

        except Exception as e:
            _LOGGER.error(f"Error in generate_files_from_response: {e}")
            return FileGenerationResult(
                files=[],
                success=False,
                message=f"Error generating files: {str(e)}",
                total_files=0
            )
    
    def _create_combined_file(self, code_blocks: List[CodeBlock]) -> Optional[GeneratedFile]:
        """
        Create a single file combining all code blocks with raw code only.

        Args:
            code_blocks: List of code blocks to combine

        Returns:
            GeneratedFile object or None if creation failed
        """
        try:
            # Generate filename for combined file
            import uuid
            unique_id = str(uuid.uuid4())[:8]

            # Determine file extension based on most common language or use .txt
            language_counts = {}
            for block in code_blocks:
                detected_language = block.language

                # If no language tag, try to detect from content
                if not detected_language or detected_language.lower() in ['none', 'text', '']:
                    detected_language = self._detect_language_from_content(block.content)

                if detected_language:
                    # Normalize language name for better detection
                    normalized_lang = self._normalize_language_name(detected_language)
                    language_counts[normalized_lang] = language_counts.get(normalized_lang, 0) + 1

            if language_counts:
                # Use the most common language for file extension
                most_common_language = max(language_counts, key=language_counts.get)
                extension = self.code_extractor.get_file_extension(most_common_language)
                filename = f"extracted_code_{unique_id}{extension}"
            else:
                filename = f"extracted_code_{unique_id}.txt"

            filepath = os.path.join(self.temp_dir, filename)

            # Create combined content with raw code only (no comments)
            combined_content = []

            for i, code_block in enumerate(code_blocks, 1):
                # Add the raw code content directly
                combined_content.append(code_block.content)

                # Ensure proper line ending
                if not code_block.content.endswith('\n'):
                    combined_content.append('\n')

                # Add blank line separator between blocks (only if multiple blocks)
                if i < len(code_blocks):
                    combined_content.append('\n')

            # Write combined content to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(''.join(combined_content))

            # Get file size
            file_size = os.path.getsize(filepath)

            return GeneratedFile(
                filename=filename,
                filepath=filepath,
                language=most_common_language if language_counts else "text",
                size=file_size,
                created_at=time.time()
            )

        except Exception as e:
            _LOGGER.error(f"Error creating combined file: {e}")
            return None

    def _normalize_language_name(self, language: str) -> str:
        """
        Normalize language names for better detection.

        Args:
            language: Raw language name from code block

        Returns:
            Normalized language name
        """
        if not language:
            return "text"

        lang_lower = language.lower().strip()

        # Language mappings for common variations
        language_mappings = {
            # Python variations
            'py': 'python',
            'python3': 'python',
            'python2': 'python',

            # JavaScript variations
            'js': 'javascript',
            'jsx': 'javascript',
            'node': 'javascript',
            'nodejs': 'javascript',

            # TypeScript variations
            'ts': 'typescript',
            'tsx': 'typescript',

            # Java variations
            'java': 'java',

            # C/C++ variations
            'c++': 'cpp',
            'cxx': 'cpp',
            'cc': 'cpp',

            # C# variations
            'c#': 'csharp',
            'cs': 'csharp',

            # Shell variations
            'bash': 'shell',
            'sh': 'shell',
            'zsh': 'shell',

            # Web languages
            'html': 'html',
            'htm': 'html',
            'css': 'css',
            'scss': 'css',
            'sass': 'css',

            # Data formats
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',

            # Database
            'sql': 'sql',
            'mysql': 'sql',
            'postgresql': 'sql',
            'postgres': 'sql',

            # Other languages
            'go': 'go',
            'golang': 'go',
            'rust': 'rust',
            'rs': 'rust',
            'php': 'php',
            'ruby': 'ruby',
            'rb': 'ruby',
            'swift': 'swift',
            'kotlin': 'kotlin',
            'kt': 'kotlin',
            'scala': 'scala',
            'r': 'r',
            'matlab': 'matlab',
            'perl': 'perl',
            'lua': 'lua',
        }

        return language_mappings.get(lang_lower, lang_lower)

    def _cleanup_git_repository(self, repo_path: str) -> None:
        """
        Clean the git repository by resetting any changes and ensuring clean state.

        Args:
            repo_path: Path to the git repository
        """
        try:
            _LOGGER.info(f"Cleaning git repository at {repo_path}")

            # Check if there are any changes
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )

            changes = git_status.stdout.strip()
            if changes:
                _LOGGER.info(f"Found git changes: {changes}")

                # Clean untracked files and directories
                subprocess.run(
                    ["git", "clean", "-fd"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                _LOGGER.info("Cleaned untracked files")

                # Reset all changes to HEAD
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                _LOGGER.info("Reset to HEAD")
            else:
                _LOGGER.info("No git changes found")

            # Always do a hard reset to ensure we're at a clean state
            subprocess.run(
                ["git", "reset", "--hard", "HEAD"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            _LOGGER.info("Git repository cleaned successfully")

        except subprocess.CalledProcessError as e:
            _LOGGER.warning(f"Git cleanup failed: {e}")
        except Exception as e:
            _LOGGER.warning(f"Git cleanup error: {e}")

    def _create_demo_test_file(self, project_path: str, code_blocks: list) -> Tuple[Optional[str], int]:
        """
        Update DemoTest.java file in the SWTBot project by appending code after //CODE_GENERATE comment.
        This method now only uses the existing DemoTest.java template file and requires it to exist.

        Args:
            project_path: Path to the SWTBot project
            code_blocks: List of code blocks to combine

        Returns:
            Tuple of (path to the updated file, number of unique code blocks used), or (None, 0) if failed
        """
        try:
            # Create target directory
            demo_test_dir = os.path.join(project_path, DEMO_TEST_RELATIVE_PATH)
            demo_test_path = os.path.join(demo_test_dir, DEMO_TEST_FILENAME)

            # Template file must exist - no fallback to hardcoded template
            if not os.path.exists(demo_test_path):
                _LOGGER.error(f"DemoTest.java template file not found at {demo_test_path}")
                return None, 0

            # Read existing template file
            with open(demo_test_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Find the //CODE_GENERATE comment
            code_generate_marker = "//CODE_GENERATE"
            if code_generate_marker not in template_content:
                _LOGGER.error(f"//CODE_GENERATE marker not found in template file at {demo_test_path}")
                return None, 0

            # Split content at the marker
            parts = template_content.split(code_generate_marker, 1)
            template_before = parts[0] + code_generate_marker

            # Check if template already has content after the marker (from previous runs)
            existing_content_after_marker = ""
            if len(parts) > 1:
                existing_content_after_marker = parts[1]
                existing_methods_count = (
                    existing_content_after_marker.count("public void step01CreateProject()") +
                    existing_content_after_marker.count("public void step01()")
                )
                if existing_methods_count > 0:
                    _LOGGER.warning(f"Template already contains {existing_methods_count} methods after //CODE_GENERATE marker - will replace with new content")
                    # We'll ignore the existing content and replace it entirely

            # Deduplicate code blocks by content to avoid duplicates
            unique_code_blocks = []
            seen_content = set()

            for i, code_block in enumerate(code_blocks):
                # Normalize content for comparison (strip whitespace and normalize line endings)
                normalized_content = code_block.content.strip()
                # Further normalize by removing extra whitespace and standardizing line endings
                normalized_content = '\n'.join(line.strip() for line in normalized_content.split('\n') if line.strip())

                if normalized_content and normalized_content not in seen_content:
                    unique_code_blocks.append(code_block)
                    seen_content.add(normalized_content)
                    _LOGGER.debug(f"Added unique code block {i+1}: {len(normalized_content)} chars")
                else:
                    _LOGGER.debug(f"Skipped duplicate code block {i+1}: {len(normalized_content)} chars")

            _LOGGER.info(f"Deduplicated {len(code_blocks)} code blocks to {len(unique_code_blocks)} unique blocks")

            # Combine unique extracted code blocks
            extracted_code_content = []
            for i, code_block in enumerate(unique_code_blocks, 1):
                extracted_code_content.append('\n    ')  # Add proper indentation
                extracted_code_content.append(code_block.content.replace('\n', '\n    '))  # Indent all lines
                if not code_block.content.endswith('\n'):
                    extracted_code_content.append('\n')
                if i < len(unique_code_blocks):
                    extracted_code_content.append('\n')

            # Always use a clean closing brace to avoid preserving any duplicate content
            # This ensures we start fresh each time and don't accumulate duplicates
            template_after = '\n}'

            # Combine template with extracted code
            final_content = template_before + ''.join(extracted_code_content) + template_after

            # Write updated file
            with open(demo_test_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

            _LOGGER.info(f"Updated DemoTest.java template with {len(unique_code_blocks)} unique code blocks (from {len(code_blocks)} total blocks)")
            return demo_test_path, len(unique_code_blocks)

        except Exception as e:
            _LOGGER.error(f"Failed to update DemoTest.java: {e}")
            return None, 0

    def _create_project_zip(self, project_path: str) -> GeneratedFile:
        """
        Create a zip file of the entire SWTBot project.

        Args:
            project_path: Path to the SWTBot project

        Returns:
            GeneratedFile object for the zip file, or None if failed
        """
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            zip_filename = f"swtbot-s32-demo-{unique_id}.zip"
            zip_filepath = os.path.join(self.temp_dir, zip_filename)

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(project_path):
                    # Skip .git directory for security
                    if '.git' in dirs:
                        dirs.remove('.git')

                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_path)
                        zipf.write(file_path, arcname)

            zip_size = os.path.getsize(zip_filepath)

            generated_file = GeneratedFile(
                filename=zip_filename,
                filepath=zip_filepath,
                language="java",
                size=zip_size,
                created_at=time.time()
            )

            self._generated_files[zip_filename] = generated_file
            _LOGGER.info(f"Created project zip: {zip_filename} ({zip_size} bytes)")
            return generated_file

        except Exception as e:
            _LOGGER.error(f"Failed to create project zip: {e}")
            return None

    def _handle_s32_demo_hackathon(self, response_text: str) -> FileGenerationResult:
        """
        Special handler for S32DSGEN requests.
        Updates the existing DemoTest.java template by appending extracted code after the //CODE_GENERATE comment,
        then returns a zip file of the swtbot-example project.

        Args:
            response_text: The complete response text to extract code from

        Returns:
            FileGenerationResult with zip file of the swtbot-example project
        """
        try:
            _LOGGER.info("Processing S32DSGEN request")

            # Extract code blocks
            extracted_code = self.code_extractor.extract_code_blocks(response_text)

            if not extracted_code.has_code:
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message="No code blocks found for S32DSGEN",
                    total_files=0
                )

            # Check if the mounted SWTBot project exists
            if not os.path.exists(SWTBOT_PROJECT_PATH):
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message=f"SWTBot example project not found at {SWTBOT_PROJECT_PATH}",
                    total_files=0
                )

            # Clean the git repository (reset any changes) - but don't fail if it doesn't work
            self._cleanup_git_repository(SWTBOT_PROJECT_PATH)

            # Verify template file state after git cleanup
            demo_test_path_check = os.path.join(SWTBOT_PROJECT_PATH, DEMO_TEST_RELATIVE_PATH, DEMO_TEST_FILENAME)
            if os.path.exists(demo_test_path_check):
                with open(demo_test_path_check, 'r', encoding='utf-8') as f:
                    template_content_check = f.read()

                # Count existing methods in template after cleanup
                step01_create_count = template_content_check.count("public void step01CreateProject()")
                step01_count = template_content_check.count("public void step01()")

                _LOGGER.info(f"Template state after git cleanup - step01CreateProject(): {step01_create_count}, step01(): {step01_count}")

                if step01_create_count > 0 or step01_count > 0:
                    _LOGGER.warning("Template file already contains methods after git cleanup - this suggests the clean template in git has duplicates")
            else:
                _LOGGER.info("Template file does not exist after git cleanup")

            # Update DemoTest.java template in the project
            demo_test_result = self._create_demo_test_file(SWTBOT_PROJECT_PATH, extracted_code.blocks)
            demo_test_path, unique_blocks_count = demo_test_result
            if not demo_test_path:
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message="Failed to update DemoTest.java template file",
                    total_files=0
                )

            # Create zip file of the entire project
            generated_file = self._create_project_zip(SWTBOT_PROJECT_PATH)
            if not generated_file:
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message="Failed to create project zip file",
                    total_files=0
                )

            return FileGenerationResult(
                files=[generated_file],
                success=True,
                message=f"Successfully updated S32DSGEN project with DemoTest.java template containing {unique_blocks_count} unique code blocks (from {len(extracted_code.blocks)} total blocks)",
                total_files=1
            )

        except Exception as e:
            _LOGGER.error(f"Error handling S32DSGEN: {e}")
            return FileGenerationResult(
                files=[],
                success=False,
                message=f"Error creating S32 IDE DEMO project: {str(e)}",
                total_files=0
            )

    def _detect_language_from_content(self, content: str) -> Optional[str]:
        """
        Detect programming language from code content using patterns.

        Args:
            content: The code content to analyze

        Returns:
            Detected language name or None
        """
        if not content or not content.strip():
            return None

        content_lower = content.lower().strip()

        # Python patterns (more comprehensive)
        python_patterns = [
            'def ', 'import ', 'from ', 'print(', 'if __name__', 'elif ',
            'class ', 'self.', 'self,', 'return ', 'input(', 'len(', 'range(',
            'for ', 'while ', 'try:', 'except:', 'finally:', 'with ', 'lambda ',
            'True', 'False', 'None', '__init__', '__str__', '__repr__',
            # More basic patterns
            ' = ', '==', '!=', 'and ', 'or ', 'not ', 'in ', 'is ', 'if ',
            'else:', 'elif:', 'pass', 'break', 'continue', 'yield', 'assert'
        ]

        # Java patterns (more comprehensive and specific)
        java_patterns = [
            'public class', 'private ', 'public static void main', 'System.out.print',
            'import java.', 'import org.', 'public static', 'private static',
            'public void', 'private void', 'protected ', '@Test', '@Override',
            'new ', 'extends ', 'implements ', 'throws ', 'catch ', 'finally ',
            'String ', 'int ', 'boolean ', 'void ', 'null', 'true', 'false'
        ]

        # JavaScript patterns
        js_patterns = [
            'function ', 'var ', 'let ', 'const ', 'console.log', 'document.',
            'window.', '=>', 'async ', 'await ', 'require(', 'module.exports'
        ]

        # HTML patterns
        html_patterns = [
            '<!doctype', '<html', '<head>', '<body>', '<div', '<span', '<p>',
            '</html>', '</head>', '</body>', '</div>', '</span>', '</p>'
        ]

        # CSS patterns (more specific to avoid false positives)
        css_patterns = [
            '{', '}', 'color:', 'background:', 'margin:', 'padding:',
            'font-', 'border:', 'width:', 'height:', '@media', 'px', 'em',
            'display:', 'position:', 'float:', 'clear:', 'overflow:', 'z-index:'
        ]

        # SQL patterns
        sql_patterns = [
            'select ', 'from ', 'where ', 'insert into', 'update ', 'delete from',
            'create table', 'alter table', 'drop table', 'join ', 'group by', 'order by'
        ]

        # Shell/Bash patterns
        shell_patterns = [
            '#!/bin/bash', '#!/bin/sh', 'echo ', 'cd ', 'ls ', 'grep ', 'awk ',
            'sed ', 'chmod ', 'chown ', '$1', '$2', '${', 'export '
        ]

        # Count pattern matches for each language
        scores = {}

        # Java (check first to avoid Python false positives)
        java_score = sum(1 for pattern in java_patterns if pattern in content_lower)
        # Boost score for strong Java indicators
        if 'public class' in content_lower:
            java_score += 3
        if 'import java.' in content_lower or 'import org.' in content_lower:
            java_score += 2
        if '@test' in content_lower or '@override' in content_lower:
            java_score += 2
        if java_score > 0:
            scores['java'] = java_score

        # Python (only if Java score is low)
        python_score = sum(1 for pattern in python_patterns if pattern in content_lower)
        # Reduce Python score if Java indicators are present
        if java_score > 2:
            python_score = max(0, python_score - 2)
        if python_score > 0:
            scores['python'] = python_score

        # JavaScript
        js_score = sum(1 for pattern in js_patterns if pattern in content_lower)
        if js_score > 0:
            scores['javascript'] = js_score

        # HTML
        html_score = sum(1 for pattern in html_patterns if pattern in content_lower)
        if html_score > 0:
            scores['html'] = html_score

        # CSS (only if not HTML and has strong CSS indicators)
        if html_score == 0:  # Don't detect CSS if HTML is present
            css_score = sum(1 for pattern in css_patterns if pattern in content_lower)
            # Require both braces and CSS properties for CSS detection
            has_braces = '{' in content_lower and '}' in content_lower
            has_css_properties = any(prop in content_lower for prop in ['color:', 'background:', 'margin:', 'padding:', 'font-', 'border:'])
            if css_score > 2 and has_braces and has_css_properties:
                scores['css'] = css_score

        # SQL
        sql_score = sum(1 for pattern in sql_patterns if pattern in content_lower)
        if sql_score > 0:
            scores['sql'] = sql_score

        # Shell
        shell_score = sum(1 for pattern in shell_patterns if pattern in content_lower)
        if shell_score > 0:
            scores['shell'] = shell_score

        # Return the language with the highest score
        if scores:
            detected_language = max(scores, key=scores.get)
            max_score = scores[detected_language]

            # Only return if we have a reasonable confidence
            # Lower threshold for Python since it's commonly requested
            min_threshold = 1 if detected_language == 'python' else 2
            if max_score >= min_threshold:
                return detected_language

        return None



    def _create_file_from_block(self, code_block: CodeBlock, block_index: int) -> Optional[GeneratedFile]:
        """
        Create a file from a single code block.

        Args:
            code_block: The code block to create a file from
            block_index: Index of the code block

        Returns:
            GeneratedFile object or None if creation failed
        """
        try:
            # Generate filename
            filename = self.code_extractor.generate_filename(code_block.language, block_index)
            filepath = os.path.join(self.temp_dir, filename)

            # Write code content to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code_block.content)

            # Get file size
            file_size = os.path.getsize(filepath)

            return GeneratedFile(
                filename=filename,
                filepath=filepath,
                language=code_block.language,
                size=file_size,
                created_at=time.time()
            )

        except Exception as e:
            _LOGGER.error(f"Error creating file from code block: {e}")
            return None
    
    def get_file_info(self, filename: str) -> Optional[GeneratedFile]:
        """
        Get information about a generated file.
        
        Args:
            filename: Name of the file to get info for
            
        Returns:
            GeneratedFile object or None if not found
        """
        return self._generated_files.get(filename)
    
    def get_file_path(self, filename: str) -> Optional[str]:
        """
        Get the full path to a generated file.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full file path or None if not found
        """
        file_info = self.get_file_info(filename)
        if file_info and os.path.exists(file_info.filepath):
            return file_info.filepath
        return None
    
    def list_generated_files(self) -> List[GeneratedFile]:
        """
        List all currently generated files.
        
        Returns:
            List of GeneratedFile objects
        """
        # Filter out files that no longer exist
        existing_files = []
        for file_info in self._generated_files.values():
            if os.path.exists(file_info.filepath):
                existing_files.append(file_info)
        
        return existing_files
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a generated file.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if file was deleted successfully
        """
        file_info = self._generated_files.get(filename)
        if not file_info:
            return False
        
        try:
            if os.path.exists(file_info.filepath):
                os.remove(file_info.filepath)
            self._generated_files.pop(filename, None)
            return True
        except Exception as e:
            _LOGGER.error(f"Error deleting file {filename}: {e}")
            return False
    
    def cleanup_all_files(self):
        """Clean up all generated files."""
        for filename in list(self._generated_files.keys()):
            self.delete_file(filename)
    
    def stop(self):
        """Stop the file generator and cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        self.cleanup_all_files()


# Global file generator instance
_file_generator: Optional[FileGenerator] = None


def get_file_generator() -> FileGenerator:
    """Get the global file generator instance."""
    global _file_generator
    if _file_generator is None:
        _file_generator = FileGenerator()
    return _file_generator


def cleanup_file_generator():
    """Cleanup the global file generator instance."""
    global _file_generator
    if _file_generator is not None:
        _file_generator.stop()
        _file_generator = None
