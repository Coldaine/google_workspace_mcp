"""
Google Drive MCP Tools

This module provides MCP tools for interacting with Google Drive API.
"""
import logging
import asyncio
from typing import Literal, Optional
from tempfile import NamedTemporaryFile

from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import httpx

from auth.service_decorator import require_google_service
from auth.oauth_config import is_stateless_mode
from core.utils import extract_office_xml_text, handle_http_errors
from core.server import server
from gdrive.drive_helpers import (
    DRIVE_QUERY_PATTERNS,
    build_drive_list_params,
    check_public_link_permission,
    get_drive_image_url,
)

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE_BYTES = 256 * 1024  # 256 KB
UPLOAD_CHUNK_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB (Google recommended minimum)

@server.tool()
@handle_http_errors("search_drive_files", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def search_drive_files(
    service,
    user_google_email: str,
    query: str,
    page_size: int = 10,
    drive_id: Optional[str] = None,
    include_items_from_all_drives: bool = True,
    corpora: Optional[str] = None,
) -> str:
    """
    Searches for files and folders within a user's Google Drive, including shared drives.

    Args:
        user_google_email (str): The user's Google email address. Required.
        query (str): The search query string. Supports Google Drive search operators.
        page_size (int): The maximum number of files to return. Defaults to 10.
        drive_id (Optional[str]): ID of the shared drive to search. If None, behavior depends on `corpora` and `include_items_from_all_drives`.
        include_items_from_all_drives (bool): Whether shared drive items should be included in results. Defaults to True. This is effective when not specifying a `drive_id`.
        corpora (Optional[str]): Bodies of items to query (e.g., 'user', 'domain', 'drive', 'allDrives').
                                 If 'drive_id' is specified and 'corpora' is None, it defaults to 'drive'.
                                 Otherwise, Drive API default behavior applies. Prefer 'user' or 'drive' over 'allDrives' for efficiency.

    Returns:
        str: A formatted list of found files/folders with their details (ID, name, type, size, modified time, link).
    """
    logger.info(f"[search_drive_files] Invoked. Email: '{user_google_email}', Query: '{query}'")

    # Check if the query looks like a structured Drive query or free text
    # Look for Drive API operators and structured query patterns
    is_structured_query = any(pattern.search(query) for pattern in DRIVE_QUERY_PATTERNS)

    if is_structured_query:
        final_query = query
        logger.info(f"[search_drive_files] Using structured query as-is: '{final_query}'")
    else:
        # For free text queries, wrap in fullText contains
        escaped_query = query.replace("'", "\\'")
        final_query = f"fullText contains '{escaped_query}'"
        logger.info(f"[search_drive_files] Reformatting free text query '{query}' to '{final_query}'")

    list_params = build_drive_list_params(
        query=final_query,
        page_size=page_size,
        drive_id=drive_id,
        include_items_from_all_drives=include_items_from_all_drives,
        corpora=corpora,
    )

    results = await asyncio.to_thread(
        service.files().list(**list_params).execute
    )
    files = results.get('files', [])
    if not files:
        return f"No files found for '{query}'."

    formatted_files_text_parts = [f"Found {len(files)} files for {user_google_email} matching '{query}':"]
    for item in files:
        size_str = f", Size: {item.get('size', 'N/A')}" if 'size' in item else ""
        formatted_files_text_parts.append(
            f"- Name: \"{item['name']}\" (ID: {item['id']}, Type: {item['mimeType']}{size_str}, Modified: {item.get('modifiedTime', 'N/A')}) Link: {item.get('webViewLink', '#')}"
        )
    text_output = "\n".join(formatted_files_text_parts)
    return text_output

@server.tool()
@handle_http_errors("get_drive_file_content", is_read_only=True, service_type="drive")
@require_google_service("drive", "drive_read")
async def get_drive_file_content(
    service,
    user_google_email: str,
    file_id: str,
) -> str:
    """
    Retrieves the content of a specific Google Drive file by ID, supporting files in shared drives.

    • Native Google Docs, Sheets, Slides → exported as text / CSV.
    • Office files (.docx, .xlsx, .pptx) → unzipped & parsed with std-lib to
      extract readable text.
    • Any other file → downloaded; tries UTF-8 decode, else notes binary.

    Args:
        user_google_email: The user’s Google email address.
        file_id: Drive file ID.

    Returns:
        str: The file content as plain text with metadata header.
    """
    logger.info(f"[get_drive_file_content] Invoked. File ID: '{file_id}'")

    file_metadata = await asyncio.to_thread(
        service.files().get(
            fileId=file_id, fields="id, name, mimeType, webViewLink", supportsAllDrives=True
        ).execute
    )
    mime_type = file_metadata.get("mimeType", "")
    file_name = file_metadata.get("name", "Unknown File")
    export_mime_type = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }.get(mime_type)

    request_obj = (
        service.files().export_media(fileId=file_id, mimeType=export_mime_type, supportsAllDrives=True)
        if export_mime_type
        else service.files().get_media(fileId=file_id, supportsAllDrives=True)
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_obj)
    loop = asyncio.get_event_loop()
    done = False
    while not done:
        status, done = await loop.run_in_executor(None, downloader.next_chunk)

    file_content_bytes = fh.getvalue()

    # Attempt Office XML extraction only for actual Office XML files
    office_mime_types = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    if mime_type in office_mime_types:
        office_text = extract_office_xml_text(file_content_bytes, mime_type)
        if office_text:
            body_text = office_text
        else:
            # Fallback: try UTF-8; otherwise flag binary
            try:
                body_text = file_content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                body_text = (
                    f"[Binary or unsupported text encoding for mimeType '{mime_type}' - "
                    f"{len(file_content_bytes)} bytes]"
                )
    else:
        # For non-Office files (including Google native files), try UTF-8 decode directly
        try:
            body_text = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body_text = (
                f"[Binary or unsupported text encoding for mimeType '{mime_type}' - "
                f"{len(file_content_bytes)} bytes]"
            )

    # Assemble response
    header = (
        f'File: "{file_name}" (ID: {file_id}, Type: {mime_type})\n'
        f'Link: {file_metadata.get("webViewLink", "#")}\n\n--- CONTENT ---\n'
    )
    return header + body_text


@server.tool()
@handle_http_errors("manage_drive_file", service_type="drive")
@require_google_service("drive", "drive_file")
async def manage_drive_file(
    service,
    user_google_email: str,
    operation: Literal["create", "update", "trash", "delete", "move", "copy"],
    file_id: Optional[str] = None,
    file_name: Optional[str] = None,
    content: Optional[str] = None,
    folder_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    fileUrl: Optional[str] = None,
    new_name: Optional[str] = None,
) -> str:
    """
    Manage Google Drive files (create, update, trash, delete, move, copy).

    Args:
        user_google_email (str): The user's Google email address.
        operation (str): The operation to perform.
            - "create": Create a new file. Requires 'file_name'. Optional: 'content', 'fileUrl', 'folder_id', 'mime_type'.
            - "update": Update file content or metadata. Requires 'file_id'. Optional: 'new_name', 'content'.
            - "trash": Move file to trash. Requires 'file_id'.
            - "delete": Permanently delete file. Requires 'file_id'.
            - "move": Move file to a new folder. Requires 'file_id', 'folder_id'.
            - "copy": Copy a file. Requires 'file_id'. Optional: 'new_name', 'folder_id'.
        file_id (Optional[str]): ID of the file to manage (required for all except 'create').
        file_name (Optional[str]): Name for the new file (required for 'create').
        content (Optional[str]): Content to write (for 'create' or 'update').
        folder_id (Optional[str]): Parent folder ID (for 'create', 'move', 'copy'). Defaults to 'root' for create.
        mime_type (Optional[str]): MIME type for creation. Defaults to 'text/plain'.
        fileUrl (Optional[str]): URL to fetch content from (for 'create').
        new_name (Optional[str]): New name for the file (for 'update' or 'copy').

    Returns:
        str: Result message.
    """
    logger.info(f"[manage_drive_file] Operation={operation}, Email={user_google_email}, File ID={file_id}")

    if operation == "create":
        if not file_name:
            raise ValueError("Operation 'create' requires 'file_name'.")
        
        # Default values
        target_folder_id = folder_id if folder_id else 'root'
        target_mime_type = mime_type if mime_type else 'text/plain'

        if not content and not fileUrl:
             # Allow creating empty files (like folders or empty docs) if mime_type implies it, 
             # but for general files warn if no content. 
             # For now, we'll allow empty creation if it's a folder, otherwise require content/url
             if target_mime_type != 'application/vnd.google-apps.folder':
                 # We will allow empty text files too
                 pass

        file_metadata = {
            'name': file_name,
            'parents': [target_folder_id],
            'mimeType': target_mime_type
        }

        media = None
        
        # Handle fileUrl
        if fileUrl:
            logger.info(f"[manage_drive_file] Fetching file from URL: {fileUrl}")
            if is_stateless_mode():
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.get(fileUrl)
                    if resp.status_code != 200:
                        raise Exception(f"Failed to fetch file from URL: {fileUrl} (status {resp.status_code})")
                    file_data = await resp.aread()
                    content_type = resp.headers.get("Content-Type")
                    if content_type and content_type != "application/octet-stream":
                        target_mime_type = content_type
                        file_metadata['mimeType'] = content_type

                media = MediaIoBaseUpload(
                    io.BytesIO(file_data),
                    mimetype=target_mime_type,
                    resumable=True,
                    chunksize=UPLOAD_CHUNK_SIZE_BYTES
                )
            else:
                # Stateful mode with temp file
                # Note: This is a simplified version of the original logic for brevity in this tool
                # Ideally we'd use the same temp file logic if needed, but in-memory is often fine for MCP
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.get(fileUrl)
                    if resp.status_code != 200:
                        raise Exception(f"Failed to fetch file from URL: {fileUrl} (status {resp.status_code})")
                    file_data = await resp.aread()
                    content_type = resp.headers.get("Content-Type")
                    if content_type and content_type != "application/octet-stream":
                        target_mime_type = content_type
                        file_metadata['mimeType'] = content_type
                
                media = MediaIoBaseUpload(
                    io.BytesIO(file_data),
                    mimetype=target_mime_type,
                    resumable=True,
                    chunksize=UPLOAD_CHUNK_SIZE_BYTES
                )

        elif content:
            file_data = content.encode('utf-8')
            media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=target_mime_type, resumable=True)

        # Execute Create
        if media:
            created_file = await asyncio.to_thread(
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink',
                    supportsAllDrives=True
                ).execute
            )
        else:
            created_file = await asyncio.to_thread(
                service.files().create(
                    body=file_metadata,
                    fields='id, name, webViewLink',
                    supportsAllDrives=True
                ).execute
            )

        link = created_file.get('webViewLink', 'No link available')
        return f"Successfully created file '{created_file.get('name')}' (ID: {created_file.get('id')}). Link: {link}"

    # All other operations require file_id
    if not file_id:
        raise ValueError(f"Operation '{operation}' requires 'file_id'.")

    if operation == "update":
        # Update metadata (name) or content
        file_metadata = {}
        if new_name:
            file_metadata['name'] = new_name
        
        media = None
        if content:
            # For update, we need to know the mimeType to upload correctly, or just use text/plain
            # We'll fetch current metadata to get mimeType
            current_meta = await asyncio.to_thread(
                service.files().get(fileId=file_id, fields="mimeType", supportsAllDrives=True).execute
            )
            current_mime = current_meta.get('mimeType', 'text/plain')
            media = MediaIoBaseUpload(io.BytesIO(content.encode('utf-8')), mimetype=current_mime, resumable=True)

        if media:
            updated_file = await asyncio.to_thread(
                service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink',
                    supportsAllDrives=True
                ).execute
            )
        elif file_metadata:
            updated_file = await asyncio.to_thread(
                service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    fields='id, name, webViewLink',
                    supportsAllDrives=True
                ).execute
            )
        else:
            return "No changes specified for update (provide 'new_name' or 'content')."

        return f"Successfully updated file '{updated_file.get('name')}' (ID: {updated_file.get('id')})."

    elif operation == "trash":
        file_metadata = {'trashed': True}
        updated_file = await asyncio.to_thread(
            service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, name, trashed',
                supportsAllDrives=True
            ).execute
        )
        return f"Successfully moved file '{updated_file.get('name')}' to trash."

    elif operation == "delete":
        await asyncio.to_thread(
            service.files().delete(fileId=file_id, supportsAllDrives=True).execute
        )
        return f"Successfully permanently deleted file ID: {file_id}."

    elif operation == "move":
        if not folder_id:
            raise ValueError("Operation 'move' requires 'folder_id' (destination).")
        
        # Retrieve current parents to remove them
        file = await asyncio.to_thread(
            service.files().get(fileId=file_id, fields='parents', supportsAllDrives=True).execute
        )
        previous_parents = ",".join(file.get('parents', []))
        
        updated_file = await asyncio.to_thread(
            service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents, name',
                supportsAllDrives=True
            ).execute
        )
        return f"Successfully moved file '{updated_file.get('name')}' to folder ID: {folder_id}."

    elif operation == "copy":
        file_metadata = {}
        if new_name:
            file_metadata['name'] = new_name
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        copied_file = await asyncio.to_thread(
            service.files().copy(
                fileId=file_id,
                body=file_metadata,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute
        )
        return f"Successfully copied file to '{copied_file.get('name')}' (ID: {copied_file.get('id')}). Link: {copied_file.get('webViewLink')}"

    raise ValueError(f"Unknown operation: {operation}")

async def _fetch_file_permissions(service, file_id: str) -> dict:
    """Fetch detailed file metadata including permissions."""
    return await asyncio.to_thread(
        service.files().get(
            fileId=file_id,
            fields=(
                "id, name, mimeType, size, modifiedTime, owners, permissions, "
                "webViewLink, webContentLink, shared, sharingUser, viewersCanCopyContent"
            ),
            supportsAllDrives=True,
        ).execute
    )


def _format_permissions_output(file_metadata: dict, file_id: str) -> str:
    permissions = file_metadata.get("permissions", [])
    output_parts = [
        f"File: {file_metadata.get('name', 'Unknown')}",
        f"ID: {file_id}",
        f"Type: {file_metadata.get('mimeType', 'Unknown')}",
        f"Size: {file_metadata.get('size', 'N/A')} bytes",
        f"Modified: {file_metadata.get('modifiedTime', 'N/A')}",
        "",
        "Sharing Status:",
        f"  Shared: {file_metadata.get('shared', False)}",
    ]

    sharing_user = file_metadata.get("sharingUser")
    if sharing_user:
        output_parts.append(
            f"  Shared by: {sharing_user.get('displayName', 'Unknown')} ({sharing_user.get('emailAddress', 'Unknown')})"
        )

    if permissions:
        output_parts.append(f"  Number of permissions: {len(permissions)}")
        output_parts.append("  Permissions:")
        for perm in permissions:
            perm_type = perm.get("type", "unknown")
            role = perm.get("role", "unknown")
            if perm_type == "anyone":
                output_parts.append(f"    - Anyone with the link ({role})")
            elif perm_type == "user":
                email = perm.get("emailAddress", "unknown")
                output_parts.append(f"    - User: {email} ({role})")
            elif perm_type == "domain":
                domain = perm.get("domain", "unknown")
                output_parts.append(f"    - Domain: {domain} ({role})")
            elif perm_type == "group":
                email = perm.get("emailAddress", "unknown")
                output_parts.append(f"    - Group: {email} ({role})")
            else:
                output_parts.append(f"    - {perm_type} ({role})")
    else:
        output_parts.append("  No additional permissions (private file)")

    output_parts.extend(
        [
            "",
            "URLs:",
            f"  View Link: {file_metadata.get('webViewLink', 'N/A')}",
        ]
    )

    web_content_link = file_metadata.get("webContentLink")
    if web_content_link:
        output_parts.append(f"  Direct Download Link: {web_content_link}")

    has_public_link = check_public_link_permission(permissions)
    if has_public_link:
        output_parts.extend(
            [
                "",
                "✅ This file is shared with 'Anyone with the link' - it can be inserted into Google Docs",
            ]
        )
    else:
        output_parts.extend(
            [
                "",
                "❌ This file is NOT shared with 'Anyone with the link' - it cannot be inserted into Google Docs",
                "   To fix: Right-click the file in Google Drive → Share → Anyone with the link → Viewer",
            ]
        )

    return "\n".join(output_parts)


@server.tool()
@handle_http_errors("manage_drive_permissions", is_read_only=False, service_type="drive")
@require_google_service("drive", "drive_file")
async def manage_drive_permissions(
    service,
    user_google_email: str,
    operation: Literal["get", "check_public", "create", "delete"],
    file_id: Optional[str] = None,
    file_name: Optional[str] = None,
    role: Optional[str] = None,
    type: Optional[str] = None,
    email_address: Optional[str] = None,
    permission_id: Optional[str] = None,
) -> str:
    """
    Manage Drive permissions for a file.

    Args:
        user_google_email (str): User email.
        operation (str): Operation to perform:
            - "get": Return full permission metadata (requires file_id).
            - "check_public": Verify "Anyone with the link" access (requires file_id or file_name).
            - "create": Add a permission (share). Requires file_id, role, type. Optional: email_address.
            - "delete": Remove a permission. Requires file_id, permission_id.
        file_id (Optional[str]): ID of the file.
        file_name (Optional[str]): Name of the file (for check_public).
        role (Optional[str]): Role for 'create' (e.g., 'reader', 'writer', 'commenter').
        type (Optional[str]): Type for 'create' (e.g., 'user', 'group', 'domain', 'anyone').
        email_address (Optional[str]): Email for 'create' if type is 'user' or 'group'.
        permission_id (Optional[str]): ID of permission to delete.

    Returns:
        str: Result message.
    """
    logger.info(
        f"[manage_drive_permissions] Operation={operation}, file_id={file_id}"
    )

    if operation == "get":
        if not file_id:
            raise ValueError("Operation 'get' requires 'file_id'.")
        file_metadata = await _fetch_file_permissions(service, file_id)
        return _format_permissions_output(file_metadata, file_id)

    elif operation == "check_public":
        target_file_id = file_id
        output_parts = []

        if not target_file_id:
            if not file_name:
                raise ValueError("Operation 'check_public' requires 'file_name' or 'file_id'.")
            escaped_name = file_name.replace("'", "\\'")
            query = f"name = '{escaped_name}'"
            list_params = {
                "q": query,
                "pageSize": 10,
                "fields": "files(id, name, mimeType, webViewLink)",
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }
            results = await asyncio.to_thread(service.files().list(**list_params).execute)
            files = results.get("files", [])
            if not files:
                return f"No file found with name '{file_name}'"
            if len(files) > 1:
                output_parts.append(f"Found {len(files)} files with name '{file_name}':")
                for f in files:
                    output_parts.append(f"  - {f['name']} (ID: {f['id']})")
                output_parts.append("\nChecking the first file...\n")
            target_file_id = files[0]["id"]

        file_metadata = await _fetch_file_permissions(service, target_file_id)
        permissions = file_metadata.get("permissions", [])
        has_public_link = check_public_link_permission(permissions)

        output_parts.extend(
            [
                f"File: {file_metadata.get('name', 'Unknown')}",
                f"ID: {target_file_id}",
                f"Type: {file_metadata.get('mimeType', 'Unknown')}",
                f"Shared: {file_metadata.get('shared', False)}",
                "",
            ]
        )

        if has_public_link:
            output_parts.extend(
                [
                    "✅ PUBLIC ACCESS ENABLED - This file can be inserted into Google Docs",
                    f"Use with insert_doc_image_url: {get_drive_image_url(target_file_id)}",
                ]
            )
        else:
            output_parts.extend(
                [
                    "❌ NO PUBLIC ACCESS - Cannot insert into Google Docs",
                    "Fix: Drive → Share → 'Anyone with the link' → 'Viewer'",
                ]
            )

        return "\n".join(output_parts)

    elif operation == "create":
        if not file_id:
            raise ValueError("Operation 'create' requires 'file_id'.")
        if not role or not type:
            raise ValueError("Operation 'create' requires 'role' and 'type'.")
        
        permission_body = {
            'role': role,
            'type': type,
        }
        if email_address:
            permission_body['emailAddress'] = email_address
        
        # If type is anyone, we don't need email
        
        result = await asyncio.to_thread(
            service.permissions().create(
                fileId=file_id,
                body=permission_body,
                fields='id',
                supportsAllDrives=True
            ).execute
        )
        return f"Successfully added permission (ID: {result.get('id')}) to file {file_id}."

    elif operation == "delete":
        if not file_id or not permission_id:
            raise ValueError("Operation 'delete' requires 'file_id' and 'permission_id'.")
        
        await asyncio.to_thread(
            service.permissions().delete(
                fileId=file_id,
                permissionId=permission_id,
                supportsAllDrives=True
            ).execute
        )
        return f"Successfully deleted permission {permission_id} from file {file_id}."

    raise ValueError(f"Unsupported operation '{operation}'.")
