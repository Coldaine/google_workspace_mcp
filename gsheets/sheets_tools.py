"""
Google Sheets MCP Tools

This module provides MCP tools for interacting with Google Sheets API.
"""

import logging
import asyncio
import json
from typing import List, Literal, Optional, Union


from auth.service_decorator import require_google_service, require_multiple_services
from core.server import server
from core.utils import handle_http_errors
from core.comments import create_comment_tools

# Configure module logger
logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("get_spreadsheet_info", is_read_only=True, service_type="sheets")
@require_multiple_services([
    {"service_type": "drive", "scopes": "drive_read", "param_name": "drive_service"},
    {"service_type": "sheets", "scopes": "sheets_read", "param_name": "sheets_service"},
])
async def get_spreadsheet_info(
    drive_service,
    sheets_service,
    user_google_email: str,
    operation: Literal["get", "list"],
    spreadsheet_id: Optional[str] = None,
    max_results: int = 25,
) -> str:
    """
    Retrieve spreadsheet metadata or list available spreadsheets.

    operation: Literal["get", "list"]
    - get: Return sheet names and sizes for a spreadsheet (requires spreadsheet_id).
    - list: List accessible spreadsheets from Drive (uses Drive API, respects shared drives).
    
    Examples:
    - get_spreadsheet_info(..., operation="list", max_results=10)
    - get_spreadsheet_info(..., operation="get", spreadsheet_id="abc123")
    """
    logger.info(
        f"[get_spreadsheet_info] Operation={operation}, Spreadsheet ID={spreadsheet_id}, Max={max_results}"
    )

    if operation == "list":
        files_response = await asyncio.to_thread(
            drive_service.files()
            .list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=max_results,
                fields="files(id,name,modifiedTime,webViewLink)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute
        )

        files = files_response.get("files", [])
        if not files:
            return f"No spreadsheets found for {user_google_email}."

        spreadsheets_list = [
            f"- \"{file['name']}\" (ID: {file['id']}) | Modified: {file.get('modifiedTime', 'Unknown')} | Link: {file.get('webViewLink', 'No link')}"
            for file in files
        ]

        logger.info(f"Successfully listed {len(files)} spreadsheets for {user_google_email}.")
        return (
            f"Successfully listed {len(files)} spreadsheets for {user_google_email}:\n"
            + "\n".join(spreadsheets_list)
        )

    if operation == "get":
        if not spreadsheet_id:
            raise Exception("Operation 'get' requires 'spreadsheet_id'.")

        spreadsheet = await asyncio.to_thread(
            sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute
        )

        title = spreadsheet.get("properties", {}).get("title", "Unknown")
        sheets = spreadsheet.get("sheets", [])

        sheets_info = []
        for sheet in sheets:
            sheet_props = sheet.get("properties", {})
            sheet_name = sheet_props.get("title", "Unknown")
            sheet_id = sheet_props.get("sheetId", "Unknown")
            grid_props = sheet_props.get("gridProperties", {})
            rows = grid_props.get("rowCount", "Unknown")
            cols = grid_props.get("columnCount", "Unknown")

            sheets_info.append(
                f"  - \"{sheet_name}\" (ID: {sheet_id}) | Size: {rows}x{cols}"
            )

        logger.info(f"Successfully retrieved info for spreadsheet {spreadsheet_id} for {user_google_email}.")
        return (
            f"Spreadsheet: \"{title}\" (ID: {spreadsheet_id})\n"
            f"Sheets ({len(sheets)}):\n"
            + ("\n".join(sheets_info) if sheets_info else "  No sheets found")
        )

    raise Exception("Unsupported operation. Use 'get' or 'list'.")


@server.tool()
@handle_http_errors("read_sheet_values", is_read_only=True, service_type="sheets")
@require_google_service("sheets", "sheets_read")
async def read_sheet_values(
    service,
    user_google_email: str,
    spreadsheet_id: str,
    range_name: str = "A1:Z1000",
) -> str:
    """
    Reads values from a specific range in a Google Sheet.

    Args:
        user_google_email (str): The user's Google email address. Required.
        spreadsheet_id (str): The ID of the spreadsheet. Required.
        range_name (str): The range to read (e.g., "Sheet1!A1:D10", "A1:D10"). Defaults to "A1:Z1000".

    Returns:
        str: The formatted values from the specified range.
    """
    logger.info(f"[read_sheet_values] Invoked. Email: '{user_google_email}', Spreadsheet: {spreadsheet_id}, Range: {range_name}")

    result = await asyncio.to_thread(
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute
    )

    values = result.get("values", [])
    if not values:
        return f"No data found in range '{range_name}' for {user_google_email}."

    # Format the output as a readable table
    formatted_rows = []
    for i, row in enumerate(values, 1):
        # Pad row with empty strings to show structure
        padded_row = row + [""] * max(0, len(values[0]) - len(row)) if values else row
        formatted_rows.append(f"Row {i:2d}: {padded_row}")

    text_output = (
        f"Successfully read {len(values)} rows from range '{range_name}' in spreadsheet {spreadsheet_id} for {user_google_email}:\n"
        + "\n".join(formatted_rows[:50])  # Limit to first 50 rows for readability
        + (f"\n... and {len(values) - 50} more rows" if len(values) > 50 else "")
    )

    logger.info(f"Successfully read {len(values)} rows for {user_google_email}.")
    return text_output


@server.tool()
@handle_http_errors("modify_sheet_values", service_type="sheets")
@require_google_service("sheets", "sheets_write")
async def modify_sheet_values(
    service,
    user_google_email: str,
    spreadsheet_id: str,
    range_name: str,
    values: Optional[Union[str, List[List[str]]]] = None,
    value_input_option: str = "USER_ENTERED",
    clear_values: bool = False,
) -> str:
    """
    Modifies values in a specific range of a Google Sheet - can write, update, or clear values.

    Args:
        user_google_email (str): The user's Google email address. Required.
        spreadsheet_id (str): The ID of the spreadsheet. Required.
        range_name (str): The range to modify (e.g., "Sheet1!A1:D10", "A1:D10"). Required.
        values (Optional[Union[str, List[List[str]]]]): 2D array of values to write/update. Can be a JSON string or Python list. Required unless clear_values=True.
        value_input_option (str): How to interpret input values ("RAW" or "USER_ENTERED"). Defaults to "USER_ENTERED".
        clear_values (bool): If True, clears the range instead of writing values. Defaults to False.

    Returns:
        str: Confirmation message of the successful modification operation.
    """
    operation = "clear" if clear_values else "write"
    logger.info(f"[modify_sheet_values] Invoked. Operation: {operation}, Email: '{user_google_email}', Spreadsheet: {spreadsheet_id}, Range: {range_name}")

    # Parse values if it's a JSON string (MCP passes parameters as JSON strings)
    if values is not None and isinstance(values, str):
        try:
            parsed_values = json.loads(values)
            if not isinstance(parsed_values, list):
                raise ValueError(f"Values must be a list, got {type(parsed_values).__name__}")
            # Validate it's a list of lists
            for i, row in enumerate(parsed_values):
                if not isinstance(row, list):
                    raise ValueError(f"Row {i} must be a list, got {type(row).__name__}")
            values = parsed_values
            logger.info(f"[modify_sheet_values] Parsed JSON string to Python list with {len(values)} rows")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format for values: {e}")
        except ValueError as e:
            raise Exception(f"Invalid values structure: {e}")

    if not clear_values and not values:
        raise Exception("Either 'values' must be provided or 'clear_values' must be True.")

    if clear_values:
        result = await asyncio.to_thread(
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=range_name)
            .execute
        )

        cleared_range = result.get("clearedRange", range_name)
        text_output = f"Successfully cleared range '{cleared_range}' in spreadsheet {spreadsheet_id} for {user_google_email}."
        logger.info(f"Successfully cleared range '{cleared_range}' for {user_google_email}.")
    else:
        body = {"values": values}

        result = await asyncio.to_thread(
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute
        )

        updated_cells = result.get("updatedCells", 0)
        updated_rows = result.get("updatedRows", 0)
        updated_columns = result.get("updatedColumns", 0)

        text_output = (
            f"Successfully updated range '{range_name}' in spreadsheet {spreadsheet_id} for {user_google_email}. "
            f"Updated: {updated_cells} cells, {updated_rows} rows, {updated_columns} columns."
        )
        logger.info(f"Successfully updated {updated_cells} cells for {user_google_email}.")

    return text_output


@server.tool()
@handle_http_errors("create_spreadsheet", service_type="sheets")
@require_google_service("sheets", "sheets_write")
async def create_spreadsheet(
    service,
    user_google_email: str,
    operation: Literal["create_new", "add_sheet"],
    title: Optional[str] = None,
    sheet_names: Optional[List[str]] = None,
    spreadsheet_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> str:
    """
    Create a spreadsheet or add a sheet to an existing one.

    operation: Literal["create_new", "add_sheet"]
    - create_new: Make a new spreadsheet (requires title; optional sheet_names list).
    - add_sheet: Add a sheet to an existing spreadsheet (requires spreadsheet_id and sheet_name).
    
    Examples:
    - create_spreadsheet(..., operation="create_new", title="Roadmap", sheet_names=["Q1", "Q2"])
    - create_spreadsheet(..., operation="add_sheet", spreadsheet_id="abc123", sheet_name="New Data")
    """
    logger.info(
        f"[create_spreadsheet] Operation={operation}, Title={title}, Spreadsheet ID={spreadsheet_id}, Sheet Name={sheet_name}"
    )

    if operation == "create_new":
        if not title:
            raise Exception("Operation 'create_new' requires 'title'.")

        spreadsheet_body = {
            "properties": {
                "title": title
            }
        }

        if sheet_names:
            spreadsheet_body["sheets"] = [
                {"properties": {"title": name}} for name in sheet_names
            ]

        spreadsheet = await asyncio.to_thread(
            service.spreadsheets().create(body=spreadsheet_body).execute
        )

        spreadsheet_id = spreadsheet.get("spreadsheetId")
        spreadsheet_url = spreadsheet.get("spreadsheetUrl")

        logger.info(f"Successfully created spreadsheet for {user_google_email}. ID: {spreadsheet_id}")
        return (
            f"Successfully created spreadsheet '{title}' for {user_google_email}. "
            f"ID: {spreadsheet_id} | URL: {spreadsheet_url}"
        )

    if operation == "add_sheet":
        if not spreadsheet_id or not sheet_name:
            raise Exception("Operation 'add_sheet' requires 'spreadsheet_id' and 'sheet_name'.")

        request_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                }
            ]
        }

        response = await asyncio.to_thread(
            service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=request_body)
            .execute
        )

        sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]

        logger.info(f"Successfully created sheet for {user_google_email}. Sheet ID: {sheet_id}")
        return (
            f"Successfully created sheet '{sheet_name}' (ID: {sheet_id}) in spreadsheet {spreadsheet_id} for {user_google_email}."
        )

    raise Exception("Unsupported operation. Use 'create_new' or 'add_sheet'.")


# Create comment management tools for sheets
_comment_tools = create_comment_tools("spreadsheet", "spreadsheet_id")

# Extract and register the functions
read_sheet_comments = _comment_tools['read_comments']
create_sheet_comment = _comment_tools['create_comment']
reply_to_sheet_comment = _comment_tools['reply_to_comment']
resolve_sheet_comment = _comment_tools['resolve_comment']


