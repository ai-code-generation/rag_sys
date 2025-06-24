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
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
import logging

from .code_extractor import CodeExtractor, ExtractedCode, CodeBlock

_LOGGER = logging.getLogger(__name__)


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
    
    def generate_files_from_response(self, response_text: str) -> FileGenerationResult:
        """
        Generate a single downloadable file from all code blocks in response text.

        Args:
            response_text: The complete response text to extract code from

        Returns:
            FileGenerationResult with information about generated file
        """
        try:
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
        Create a single file combining all code blocks.

        Args:
            code_blocks: List of code blocks to combine

        Returns:
            GeneratedFile object or None if creation failed
        """
        try:
            # Generate filename for combined file
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            filename = f"extracted_code_{unique_id}.md"
            filepath = os.path.join(self.temp_dir, filename)

            # Create combined content
            combined_content = []
            combined_content.append("# Extracted Code Blocks\n")
            combined_content.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            combined_content.append(f"Total blocks: {len(code_blocks)}\n\n")

            for i, code_block in enumerate(code_blocks, 1):
                # Add section header
                language_info = f" ({code_block.language})" if code_block.language else ""
                combined_content.append(f"## Code Block {i}{language_info}\n\n")

                # Add the code block with proper markdown formatting
                if code_block.language:
                    combined_content.append(f"```{code_block.language}\n")
                else:
                    combined_content.append("```\n")
                combined_content.append(code_block.content)
                if not code_block.content.endswith('\n'):
                    combined_content.append('\n')
                combined_content.append("```\n\n")

                # Add separator between blocks
                if i < len(code_blocks):
                    combined_content.append("---\n\n")

            # Write combined content to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(''.join(combined_content))

            # Get file size
            file_size = os.path.getsize(filepath)

            return GeneratedFile(
                filename=filename,
                filepath=filepath,
                language="markdown",  # Combined file is markdown
                size=file_size,
                created_at=time.time()
            )

        except Exception as e:
            _LOGGER.error(f"Error creating combined file: {e}")
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
