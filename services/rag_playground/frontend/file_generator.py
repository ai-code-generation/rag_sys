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
from typing import Dict, List, NamedTuple, Optional
import logging

from .code_extractor import CodeExtractor, ExtractedCode, CodeBlock

_LOGGER = logging.getLogger(__name__)

# Constants for S32 IDE DEMO Hackathon
S32_TRIGGER_PHRASE = "s32 ide demo hackathon"
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
            # Check for special S32 IDE DEMO Hackathon handling
            if S32_TRIGGER_PHRASE in user_query.lower():
                _LOGGER.info("S32 IDE DEMO Hackathon detected - using special handler")
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
        Clean the git repository by resetting any changes.

        Args:
            repo_path: Path to the git repository
        """
        try:
            # Check if there are any changes
            git_status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            )

            # Only clean if there are changes
            if git_status.stdout.strip():
                subprocess.run(
                    ["git", "clean", "-fd"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                _LOGGER.info("Cleaned git repository")
        except subprocess.CalledProcessError:
            _LOGGER.warning("Git cleanup failed (continuing anyway)")
        except Exception as e:
            _LOGGER.warning(f"Git cleanup error: {e}")

    def _create_demo_test_file(self, project_path: str, code_blocks: list) -> str:
        """
        Create DemoTest.java file in the SWTBot project.

        Args:
            project_path: Path to the SWTBot project
            code_blocks: List of code blocks to combine

        Returns:
            Path to the created file, or None if failed
        """
        try:
            # Create target directory
            demo_test_dir = os.path.join(project_path, DEMO_TEST_RELATIVE_PATH)
            os.makedirs(demo_test_dir, exist_ok=True)

            # Combine code blocks
            demo_test_content = []
            for i, code_block in enumerate(code_blocks, 1):
                demo_test_content.append(code_block.content)
                if not code_block.content.endswith('\n'):
                    demo_test_content.append('\n')
                if i < len(code_blocks):
                    demo_test_content.append('\n')

            # Write file
            demo_test_path = os.path.join(demo_test_dir, DEMO_TEST_FILENAME)
            with open(demo_test_path, 'w', encoding='utf-8') as f:
                f.write(''.join(demo_test_content))

            _LOGGER.info(f"Created DemoTest.java with {len(code_blocks)} code blocks")
            return demo_test_path

        except Exception as e:
            _LOGGER.error(f"Failed to create DemoTest.java: {e}")
            return None

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
        Special handler for S32 IDE DEMO Hackathon requests.
        Creates DemoTest.java in the swtbot-example project and returns a zip file.

        Args:
            response_text: The complete response text to extract code from

        Returns:
            FileGenerationResult with zip file of the swtbot-example project
        """
        try:
            _LOGGER.info("Processing S32 IDE DEMO Hackathon request")

            # Extract code blocks
            extracted_code = self.code_extractor.extract_code_blocks(response_text)

            if not extracted_code.has_code:
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message="No code blocks found for S32 IDE DEMO Hackathon",
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

            # Create DemoTest.java in the project
            demo_test_path = self._create_demo_test_file(SWTBOT_PROJECT_PATH, extracted_code.blocks)
            if not demo_test_path:
                return FileGenerationResult(
                    files=[],
                    success=False,
                    message="Failed to create DemoTest.java file",
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
                message=f"Successfully created S32 IDE DEMO Hackathon project with DemoTest.java containing {len(extracted_code.blocks)} code blocks",
                total_files=1
            )

        except Exception as e:
            _LOGGER.error(f"Error handling S32 IDE DEMO Hackathon: {e}")
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
