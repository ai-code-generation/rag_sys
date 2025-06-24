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

"""This module contains the frontend gui for having a conversation."""
import functools
import logging
from typing import Any, Dict, List, Tuple, Union

import gradio as gr

from frontend import assets, chat_client
from frontend.file_generator import get_file_generator

_LOGGER = logging.getLogger(__name__)
PATH = "/converse"
TITLE = "Converse"
OUTPUT_TOKENS = 1024
MAX_DOCS = 5

_LOCAL_CSS = """

#contextbox {
    overflow-y: scroll !important;
    max-height: 400px;
}
"""


def build_page(client: chat_client.ChatClient) -> gr.Blocks:
    """Build the gradio page to be mounted in the frame."""
    kui_theme, kui_styles = assets.load_theme("kaizen")

    with gr.Blocks(title=TITLE, theme=kui_theme, css=kui_styles + _LOCAL_CSS) as page:

        # create the page header
        gr.Markdown(f"# {TITLE}")

        # chat logs
        with gr.Row(equal_height=True):
            chatbot = gr.Chatbot(scale=2, label=client.model_name)
            latest_response = gr.Textbox(visible=False)
            context = gr.JSON(scale=1, label="Knowledge Base Context", visible=False, elem_id="contextbox",)

        # code download section
        with gr.Row(visible=False) as download_row:
            with gr.Column():
                gr.Markdown("### 📁 Generated Code File")
                download_files = gr.HTML(value="", visible=True)
                download_status = gr.Textbox(label="Status", visible=False)

        # check boxes
        with gr.Row():
            with gr.Column(scale=10, min_width=150):
                kb_checkbox = gr.Checkbox(label="Use knowledge base", info="", value=False)

        # text input boxes
        with gr.Row():
            with gr.Column(scale=10, min_width=500):
                msg = gr.Textbox(show_label=False, placeholder="Enter text and press ENTER", container=False,)

        # user feedback
        with gr.Row():
            # _ = gr.Button(value="👍  Upvote")
            # _ = gr.Button(value="👎  Downvote")
            # _ = gr.Button(value="⚠️  Flag")
            submit_btn = gr.Button(value="Submit")
            _ = gr.ClearButton(msg)
            _ = gr.ClearButton([msg, chatbot], value="Clear History")
            ctx_show = gr.Button(value="Show Context")
            ctx_hide = gr.Button(value="Hide Context", visible=False)

        # hide/show context
        def _toggle_context(btn: str) -> Dict[gr.component, Dict[Any, Any]]:
            if btn == "Show Context":
                out = [True, False, True]
            if btn == "Hide Context":
                out = [False, True, False]
            return {
                context: gr.update(visible=out[0]),
                ctx_show: gr.update(visible=out[1]),
                ctx_hide: gr.update(visible=out[2]),
            }

        ctx_show.click(_toggle_context, [ctx_show], [context, ctx_show, ctx_hide])
        ctx_hide.click(_toggle_context, [ctx_hide], [context, ctx_show, ctx_hide])

        # form actions
        _my_build_stream = functools.partial(_stream_predict, client)
        msg.submit(_my_build_stream, [kb_checkbox, msg, chatbot], [msg, chatbot, context, latest_response, download_row, download_files, download_status])
        submit_btn.click(_my_build_stream, [kb_checkbox, msg, chatbot], [msg, chatbot, context, latest_response, download_row, download_files, download_status])

    page.queue()
    return page


def _stream_predict(
    client: chat_client.ChatClient, use_knowledge_base: bool, question: str, chat_history: List[Tuple[str, str]],
) -> Any:
    """Make a prediction of the response to the prompt."""
    chunks = ""
    chat_history = chat_history or []
    _LOGGER.info(
        "processing inference request - %s", str({"prompt": question, "use_knowledge_base": use_knowledge_base}),
    )

    documents: Union[None, List[Dict[str, Union[str, float]]]] = None
    if use_knowledge_base:
        documents = client.search(prompt=question)

    for chunk in client.predict(query=question, use_knowledge_base=use_knowledge_base, num_tokens=OUTPUT_TOKENS):
        if chunk:
            chunks += chunk
            yield "", chat_history + [[question, chunks]], documents, "", gr.update(visible=False), "", ""
        else:
            # Response is complete, check for code blocks and generate files
            download_html, download_visible, status_msg = _process_code_blocks(chunks)
            yield "", chat_history + [[question, chunks]], documents, chunks, gr.update(visible=download_visible), download_html, status_msg


def _process_code_blocks(response_text: str) -> Tuple[str, bool, str]:
    """
    Process response text for code blocks and generate downloadable files.

    Args:
        response_text: Complete response text to process

    Returns:
        Tuple of (download_html, download_visible, status_message)
    """
    try:
        file_generator = get_file_generator()

        # Clean up any existing files from previous requests
        file_generator.cleanup_all_files()

        result = file_generator.generate_files_from_response(response_text)

        if not result.success or result.total_files == 0:
            return "", False, ""

        # Generate HTML for download links
        download_html = _generate_download_html(result.files)
        status_msg = result.message

        _LOGGER.info(f"Generated {result.total_files} code files for download")
        return download_html, True, status_msg

    except Exception as e:
        _LOGGER.error(f"Error processing code blocks: {e}")
        return "", False, f"Error processing code: {str(e)}"


def _generate_download_html(files) -> str:
    """Generate HTML for download link."""
    if not files:
        return ""

    # Since we now generate only one combined file
    file_info = files[0]

    size_kb = file_info.size / 1024
    size_text = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{file_info.size} bytes"

    download_link = f'/download/{file_info.filename}'

    # Get language badge
    language_display = file_info.language if file_info.language and file_info.language != "text" else "Code"

    html = f'''
    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px 0; background-color: #f9f9f9;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="background-color: #e8f5e8; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 8px;">
                        📄 {language_display}
                    </span>
                    <strong>{file_info.filename}</strong>
                </div>
                <div style="color: #666; font-size: 0.9em;">
                    Raw code blocks combined • {size_text}
                </div>
            </div>
            <a href="{download_link}" download="{file_info.filename}"
               style="background-color: #1976d2; color: white; padding: 10px 16px; text-decoration: none; border-radius: 6px; font-size: 0.9em; font-weight: 500;">
                📥 Download Code
            </a>
        </div>
    </div>
    '''

    return html
