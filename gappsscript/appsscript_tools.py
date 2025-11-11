"""
Google Apps Script MCP Tools

This module provides MCP tools for interacting with the Google Apps Script API.
Consolidated from 16 individual operations into 5 resource-based tools.
"""

import logging
import asyncio
from typing import Literal, Optional, List, Dict, Any

from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("manage_script_project", service_type="script")
@require_google_service("script", "script_projects")
async def manage_script_project(
    service,
    user_google_email: str,
    operation: Literal["create", "get", "get_content", "update_content"],
    script_id: Optional[str] = None,
    title: Optional[str] = None,
    parent_id: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
    version_number: Optional[int] = None,
) -> str:
    """
    Manage Google Apps Script projects: create, get metadata, get content, or update content.

    Args:
        user_google_email (str): The user's Google email address. Required.
        operation (str): Operation to perform: "create", "get", "get_content", "update_content".
        script_id (Optional[str]): Script project ID (required for get, get_content, update_content).
        title (Optional[str]): Project title (required for create).
        parent_id (Optional[str]): Parent project ID (optional for create).
        files (Optional[List[Dict]]): List of file objects for update_content. Each file should have:
            - name: str (e.g., "Code.gs", "appsscript.json")
            - type: str (e.g., "SERVER_JS", "JSON")
            - source: str (file content)
        version_number (Optional[int]): Specific version to retrieve (optional for get_content).

    Returns:
        str: Result of the operation with project details.
    """
    logger.info(
        f"[manage_script_project] Operation: {operation}, Email: '{user_google_email}'"
    )

    if operation == "create":
        if not title:
            raise ValueError("'title' is required for create operation")

        body = {"title": title}
        if parent_id:
            body["parentId"] = parent_id

        result = await asyncio.to_thread(
            service.projects().create(body=body).execute
        )

        script_id = result.get("scriptId")
        return (
            f"Successfully created Apps Script project '{title}'.\n"
            f"Script ID: {script_id}\n"
            f"Created: {result.get('createTime')}\n"
            f"Updated: {result.get('updateTime')}"
        )

    elif operation == "get":
        if not script_id:
            raise ValueError("'script_id' is required for get operation")

        result = await asyncio.to_thread(
            service.projects().get(scriptId=script_id).execute
        )

        return (
            f"Script Project Details:\n"
            f"Title: {result.get('title')}\n"
            f"Script ID: {result.get('scriptId')}\n"
            f"Created: {result.get('createTime')}\n"
            f"Updated: {result.get('updateTime')}\n"
            f"Creator: {result.get('creator')}\n"
            f"Last Modified User: {result.get('lastModifyUser')}"
        )

    elif operation == "get_content":
        if not script_id:
            raise ValueError("'script_id' is required for get_content operation")

        params = {"scriptId": script_id}
        if version_number:
            params["versionNumber"] = version_number

        result = await asyncio.to_thread(
            service.projects().getContent(**params).execute
        )

        files_info = result.get("files", [])
        file_summaries = []
        for file in files_info:
            file_summaries.append(
                f"  - {file.get('name')} ({file.get('type')}): {len(file.get('source', ''))} chars"
            )

        content_details = "\n".join(file_summaries) if file_summaries else "  No files"

        return (
            f"Script Project Content (Script ID: {script_id}):\n"
            f"Files ({len(files_info)}):\n{content_details}\n\n"
            f"Full content available in API response."
        )

    elif operation == "update_content":
        if not script_id:
            raise ValueError("'script_id' is required for update_content operation")
        if not files:
            raise ValueError("'files' is required for update_content operation")

        body = {"files": files}

        result = await asyncio.to_thread(
            service.projects().updateContent(scriptId=script_id, body=body).execute
        )

        updated_files = result.get("files", [])
        return (
            f"Successfully updated script project content.\n"
            f"Script ID: {script_id}\n"
            f"Updated {len(updated_files)} files"
        )

    else:
        raise ValueError(f"Invalid operation: {operation}")


@server.tool()
@handle_http_errors("manage_script_version", service_type="script")
@require_google_service("script", "script_projects")
async def manage_script_version(
    service,
    user_google_email: str,
    operation: Literal["create", "get", "list"],
    script_id: str,
    version_number: Optional[int] = None,
    description: Optional[str] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
) -> str:
    """
    Manage Google Apps Script versions: create, get, or list versions.

    Args:
        user_google_email (str): The user's Google email address. Required.
        operation (str): Operation to perform: "create", "get", "list".
        script_id (str): Script project ID. Required.
        version_number (Optional[int]): Version number (required for get).
        description (Optional[str]): Version description (required for create).
        page_size (int): Number of versions per page for list (default: 50).
        page_token (Optional[str]): Pagination token for list.

    Returns:
        str: Result of the operation with version details.
    """
    logger.info(
        f"[manage_script_version] Operation: {operation}, Script ID: {script_id}"
    )

    if operation == "create":
        if not description:
            raise ValueError("'description' is required for create operation")

        body = {"description": description}

        result = await asyncio.to_thread(
            service.projects().versions().create(scriptId=script_id, body=body).execute
        )

        return (
            f"Successfully created version for script {script_id}.\n"
            f"Version Number: {result.get('versionNumber')}\n"
            f"Description: {result.get('description')}\n"
            f"Created: {result.get('createTime')}"
        )

    elif operation == "get":
        if version_number is None:
            raise ValueError("'version_number' is required for get operation")

        result = await asyncio.to_thread(
            service.projects()
            .versions()
            .get(scriptId=script_id, versionNumber=version_number)
            .execute
        )

        return (
            f"Version Details:\n"
            f"Version Number: {result.get('versionNumber')}\n"
            f"Description: {result.get('description')}\n"
            f"Script ID: {result.get('scriptId')}\n"
            f"Created: {result.get('createTime')}"
        )

    elif operation == "list":
        params = {"scriptId": script_id, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token

        result = await asyncio.to_thread(
            service.projects().versions().list(**params).execute
        )

        versions = result.get("versions", [])
        next_page_token = result.get("nextPageToken")

        if not versions:
            return f"No versions found for script {script_id}"

        version_list = []
        for v in versions:
            version_list.append(
                f"  - Version {v.get('versionNumber')}: {v.get('description')} (Created: {v.get('createTime')})"
            )

        output = f"Versions for script {script_id} ({len(versions)}):\n" + "\n".join(
            version_list
        )

        if next_page_token:
            output += f"\n\nNext page token: {next_page_token}"

        return output

    else:
        raise ValueError(f"Invalid operation: {operation}")


@server.tool()
@handle_http_errors("manage_script_deployment", service_type="script")
@require_google_service("script", "script_deployments")
async def manage_script_deployment(
    service,
    user_google_email: str,
    operation: Literal["create", "get", "list", "update", "delete"],
    script_id: str,
    deployment_id: Optional[str] = None,
    version_number: Optional[int] = None,
    manifest_file_name: Optional[str] = None,
    description: Optional[str] = None,
    deployment_config: Optional[Dict[str, Any]] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
) -> str:
    """
    Manage Google Apps Script deployments: create, get, list, update, or delete.

    Args:
        user_google_email (str): The user's Google email address. Required.
        operation (str): Operation: "create", "get", "list", "update", "delete".
        script_id (str): Script project ID. Required.
        deployment_id (Optional[str]): Deployment ID (required for get, update, delete).
        version_number (Optional[int]): Version number (required for create).
        manifest_file_name (Optional[str]): Manifest filename (required for create, typically "appsscript.json").
        description (Optional[str]): Deployment description (required for create).
        deployment_config (Optional[Dict]): Deployment configuration for update.
        page_size (int): Number of deployments per page for list (default: 50).
        page_token (Optional[str]): Pagination token for list.

    Returns:
        str: Result of the operation with deployment details.
    """
    logger.info(
        f"[manage_script_deployment] Operation: {operation}, Script ID: {script_id}"
    )

    if operation == "create":
        if not all([version_number, manifest_file_name, description]):
            raise ValueError(
                "'version_number', 'manifest_file_name', and 'description' are required for create"
            )

        body = {
            "versionNumber": version_number,
            "manifestFileName": manifest_file_name,
            "description": description,
        }

        result = await asyncio.to_thread(
            service.projects().deployments().create(scriptId=script_id, body=body).execute
        )

        return (
            f"Successfully created deployment for script {script_id}.\n"
            f"Deployment ID: {result.get('deploymentId')}\n"
            f"Description: {result.get('description')}\n"
            f"Version: {result.get('versionNumber')}"
        )

    elif operation == "get":
        if not deployment_id:
            raise ValueError("'deployment_id' is required for get operation")

        result = await asyncio.to_thread(
            service.projects()
            .deployments()
            .get(scriptId=script_id, deploymentId=deployment_id)
            .execute
        )

        return (
            f"Deployment Details:\n"
            f"Deployment ID: {result.get('deploymentId')}\n"
            f"Description: {result.get('description')}\n"
            f"Script ID: {result.get('scriptId')}\n"
            f"Version: {result.get('versionNumber')}\n"
            f"Updated: {result.get('updateTime')}"
        )

    elif operation == "list":
        params = {"scriptId": script_id, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token

        result = await asyncio.to_thread(
            service.projects().deployments().list(**params).execute
        )

        deployments = result.get("deployments", [])
        next_page_token = result.get("nextPageToken")

        if not deployments:
            return f"No deployments found for script {script_id}"

        deployment_list = []
        for d in deployments:
            deployment_list.append(
                f"  - {d.get('deploymentId')}: {d.get('description')} (Version: {d.get('versionNumber')})"
            )

        output = f"Deployments for script {script_id} ({len(deployments)}):\n" + "\n".join(
            deployment_list
        )

        if next_page_token:
            output += f"\n\nNext page token: {next_page_token}"

        return output

    elif operation == "update":
        if not deployment_id or not deployment_config:
            raise ValueError(
                "'deployment_id' and 'deployment_config' are required for update"
            )

        result = await asyncio.to_thread(
            service.projects()
            .deployments()
            .update(scriptId=script_id, deploymentId=deployment_id, body=deployment_config)
            .execute
        )

        return (
            f"Successfully updated deployment {deployment_id}.\n"
            f"Description: {result.get('description')}\n"
            f"Updated: {result.get('updateTime')}"
        )

    elif operation == "delete":
        if not deployment_id:
            raise ValueError("'deployment_id' is required for delete operation")

        await asyncio.to_thread(
            service.projects()
            .deployments()
            .delete(scriptId=script_id, deploymentId=deployment_id)
            .execute
        )

        return f"Successfully deleted deployment {deployment_id} from script {script_id}"

    else:
        raise ValueError(f"Invalid operation: {operation}")


@server.tool()
@handle_http_errors("execute_script", service_type="script")
@require_google_service("script", "script_projects")
async def execute_script(
    service,
    user_google_email: str,
    script_id: str,
    function_name: str,
    parameters: Optional[List[Any]] = None,
    dev_mode: bool = False,
) -> str:
    """
    Execute a function in a Google Apps Script project.

    Args:
        user_google_email (str): The user's Google email address. Required.
        script_id (str): Script project ID. Required.
        function_name (str): Name of the function to execute. Required.
        parameters (Optional[List]): List of parameters to pass to the function.
        dev_mode (bool): If true, run in development mode (default: false).

    Returns:
        str: Execution result or error details.
    """
    logger.info(
        f"[execute_script] Executing function '{function_name}' in script {script_id}"
    )

    body = {"function": function_name, "devMode": dev_mode}

    if parameters:
        body["parameters"] = parameters

    try:
        result = await asyncio.to_thread(
            service.scripts().run(scriptId=script_id, body=body).execute
        )

        if "error" in result:
            error_details = result["error"]
            return (
                f"Script execution failed:\n"
                f"Error: {error_details.get('message', 'Unknown error')}\n"
                f"Details: {error_details.get('details', [])}"
            )

        response = result.get("response", {})
        return_value = response.get("result")

        return (
            f"Script executed successfully.\n"
            f"Function: {function_name}\n"
            f"Return value: {return_value}"
        )

    except Exception as e:
        logger.error(f"Script execution error: {e}")
        return f"Script execution failed: {str(e)}"


@server.tool()
@handle_http_errors("monitor_script_execution", service_type="script")
@require_google_service("script", "script_projects")
async def monitor_script_execution(
    service,
    user_google_email: str,
    operation: Literal["list_processes", "get_metrics"],
    script_id: str,
    deployment_id: Optional[str] = None,
    page_size: int = 50,
    page_token: Optional[str] = None,
    # Process filters
    process_types: Optional[List[str]] = None,
    process_statuses: Optional[List[str]] = None,
    function_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    # Metrics parameters
    metrics_granularity: Optional[str] = None,
    metrics_fields: Optional[str] = None,
) -> str:
    """
    Monitor Google Apps Script execution: list processes or get metrics.

    Args:
        user_google_email (str): The user's Google email address. Required.
        operation (str): "list_processes" or "get_metrics".
        script_id (str): Script project ID. Required.
        deployment_id (Optional[str]): Deployment ID (required for get_metrics).
        page_size (int): Results per page for list_processes (default: 50).
        page_token (Optional[str]): Pagination token.
        process_types (Optional[List[str]]): Filter by process types.
        process_statuses (Optional[List[str]]): Filter by statuses (e.g., RUNNING, COMPLETED, FAILED).
        function_name (Optional[str]): Filter by function name.
        start_time (Optional[str]): Filter by start time (RFC 3339).
        end_time (Optional[str]): Filter by end time (RFC 3339).
        metrics_granularity (Optional[str]): Metrics granularity (required for get_metrics).
        metrics_fields (Optional[str]): Specific metric fields to retrieve.

    Returns:
        str: Process list or metrics data.
    """
    logger.info(
        f"[monitor_script_execution] Operation: {operation}, Script ID: {script_id}"
    )

    if operation == "list_processes":
        params = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        if process_types:
            params["userProcessFilter.processTypes"] = process_types
        if process_statuses:
            params["userProcessFilter.statuses"] = process_statuses
        if function_name:
            params["userProcessFilter.functionName"] = function_name
        if start_time:
            params["userProcessFilter.startTime"] = start_time
        if end_time:
            params["userProcessFilter.endTime"] = end_time

        result = await asyncio.to_thread(
            service.processes().list(**params).execute
        )

        processes = result.get("processes", [])
        next_page_token = result.get("nextPageToken")

        if not processes:
            return f"No processes found for script {script_id}"

        process_list = []
        for p in processes:
            process_list.append(
                f"  - {p.get('processType')}: {p.get('processStatus')} "
                f"(Started: {p.get('startTime')}, Function: {p.get('functionName', 'N/A')})"
            )

        output = f"Script Processes ({len(processes)}):\n" + "\n".join(process_list)

        if next_page_token:
            output += f"\n\nNext page token: {next_page_token}"

        return output

    elif operation == "get_metrics":
        if not deployment_id or not metrics_granularity:
            raise ValueError(
                "'deployment_id' and 'metrics_granularity' are required for get_metrics"
            )

        params = {
            "scriptId": script_id,
            "metricsGranularity": metrics_granularity,
        }
        if metrics_fields:
            params["fields"] = metrics_fields

        result = await asyncio.to_thread(
            service.projects()
            .deployments()
            .get(scriptId=script_id, deploymentId=deployment_id)
            .execute
        )

        return f"Metrics data for deployment {deployment_id}:\n{result}"

    else:
        raise ValueError(f"Invalid operation: {operation}")
