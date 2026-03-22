from __future__ import annotations

from typing import Any

from packages.runtime_core.capability_loader import ToolModule

from app.local_tools import LocalToolExecutor


def get_tool_executor(config: Any) -> LocalToolExecutor:
    return LocalToolExecutor(config)


def build_office_tool_modules() -> tuple[ToolModule, ...]:
    return (
        ToolModule(
            module_id="workspace_tools",
            title="Workspace Tool Module",
            description="工作区与代码库操作工具模块，当前承载共享工具执行器。",
            build_executor=get_tool_executor,
            default=True,
            tool_names=(
                "run_shell",
                "list_directory",
                "search_codebase",
                "copy_file",
                "extract_zip",
                "extract_msg_attachments",
            ),
            metadata={"family": "office", "executor": "LocalToolExecutor", "group": "workspace"},
        ),
        ToolModule(
            module_id="file_tools",
            title="File Tool Module",
            description="文档读取、检索、结构提取与事实核验。",
            build_executor=None,
            default=False,
            tool_names=(
                "read_text_file",
                "search_text_in_file",
                "multi_query_search",
                "doc_index_build",
                "read_section_by_heading",
                "table_extract",
                "fact_check_file",
            ),
            metadata={"family": "office", "group": "file"},
        ),
        ToolModule(
            module_id="web_tools",
            title="Web Tool Module",
            description="联网抓取、搜索与网页下载工具。",
            build_executor=None,
            default=False,
            tool_names=(
                "fetch_web",
                "download_web_file",
                "search_web",
            ),
            metadata={"family": "office", "group": "web"},
        ),
        ToolModule(
            module_id="write_tools",
            title="Write Tool Module",
            description="文本写入、追加和精确替换工具。",
            build_executor=None,
            default=False,
            tool_names=(
                "write_text_file",
                "append_text_file",
                "replace_in_file",
            ),
            metadata={"family": "office", "group": "write"},
        ),
        ToolModule(
            module_id="session_tools",
            title="Session Tool Module",
            description="跨会话浏览与历史检索工具。",
            build_executor=None,
            default=False,
            tool_names=(
                "list_sessions",
                "read_session_history",
            ),
            metadata={"family": "office", "group": "session"},
        ),
    )
