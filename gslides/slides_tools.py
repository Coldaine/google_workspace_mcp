"""
Google Slides MCP Tools

This module provides MCP tools for interacting with Google Slides API.
"""

import logging
import asyncio
from typing import List, Dict, Any, Literal, Optional


from auth.service_decorator import require_google_service
from core.server import server
from core.utils import handle_http_errors
from core.comments import create_comment_tools

logger = logging.getLogger(__name__)


@server.tool()
@handle_http_errors("create_presentation", service_type="slides")
@require_google_service("slides", "slides")
async def create_presentation(
    service,
    user_google_email: str,
    title: str = "Untitled Presentation"
) -> str:
    """
    Create a new Google Slides presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        title (str): The title for the new presentation. Defaults to "Untitled Presentation".

    Returns:
        str: Details about the created presentation including ID and URL.
    """
    logger.info(f"[create_presentation] Invoked. Email: '{user_google_email}', Title: '{title}'")

    body = {
        'title': title
    }

    result = await asyncio.to_thread(
        service.presentations().create(body=body).execute
    )

    presentation_id = result.get('presentationId')
    presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    confirmation_message = f"""Presentation Created Successfully for {user_google_email}:
- Title: {title}
- Presentation ID: {presentation_id}
- URL: {presentation_url}
- Slides: {len(result.get('slides', []))} slide(s) created"""

    logger.info(f"Presentation created successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("batch_update_presentation", service_type="slides")
@require_google_service("slides", "slides")
async def batch_update_presentation(
    service,
    user_google_email: str,
    presentation_id: str,
    requests: List[Dict[str, Any]]
) -> str:
    """
    Apply batch updates to a Google Slides presentation.

    Args:
        user_google_email (str): The user's Google email address. Required.
        presentation_id (str): The ID of the presentation to update.
        requests (List[Dict[str, Any]]): List of update requests to apply.

    Returns:
        str: Details about the batch update operation results.
    """
    logger.info(f"[batch_update_presentation] Invoked. Email: '{user_google_email}', ID: '{presentation_id}', Requests: {len(requests)}")

    body = {
        'requests': requests
    }

    result = await asyncio.to_thread(
        service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=body
        ).execute
    )

    replies = result.get('replies', [])

    confirmation_message = f"""Batch Update Completed for {user_google_email}:
- Presentation ID: {presentation_id}
- URL: https://docs.google.com/presentation/d/{presentation_id}/edit
- Requests Applied: {len(requests)}
- Replies Received: {len(replies)}"""

    if replies:
        confirmation_message += "\n\nUpdate Results:"
        for i, reply in enumerate(replies, 1):
            if 'createSlide' in reply:
                slide_id = reply['createSlide'].get('objectId', 'Unknown')
                confirmation_message += f"\n  Request {i}: Created slide with ID {slide_id}"
            elif 'createShape' in reply:
                shape_id = reply['createShape'].get('objectId', 'Unknown')
                confirmation_message += f"\n  Request {i}: Created shape with ID {shape_id}"
            else:
                confirmation_message += f"\n  Request {i}: Operation completed"

    logger.info(f"Batch update completed successfully for {user_google_email}")
    return confirmation_message


@server.tool()
@handle_http_errors("get_presentation_info", is_read_only=True, service_type="slides")
@require_google_service("slides", "slides_read")
async def get_presentation_info(
    service,
    user_google_email: str,
    operation: Literal["presentation", "page", "thumbnail"],
    presentation_id: str,
    page_object_id: Optional[str] = None,
    thumbnail_size: str = "MEDIUM"
) -> str:
    """
    Retrieve presentation details, a specific page, or a page thumbnail.

    operation: Literal["presentation", "page", "thumbnail"]
    - presentation: Summary of slides and metadata.
    - page: Details of a specific slide (requires page_object_id).
    - thumbnail: Generate a thumbnail URL for a slide (requires page_object_id).
    
    Examples:
    - get_presentation_info(..., operation="presentation", presentation_id="abc123")
    - get_presentation_info(..., operation="page", presentation_id="abc123", page_object_id="p1")
    - get_presentation_info(..., operation="thumbnail", presentation_id="abc123", page_object_id="p1", thumbnail_size="LARGE")
    """
    logger.info(
        f"[get_presentation_info] Operation={operation}, Presentation={presentation_id}, Page={page_object_id}, Size={thumbnail_size}"
    )

    if operation == "presentation":
        result = await asyncio.to_thread(
            service.presentations().get(presentationId=presentation_id).execute
        )

        title = result.get('title', 'Untitled')
        slides = result.get('slides', [])
        page_size = result.get('pageSize', {})

        slides_info = []
        for i, slide in enumerate(slides, 1):
            slide_id = slide.get('objectId', 'Unknown')
            page_elements = slide.get('pageElements', [])
            slides_info.append(f"  Slide {i}: ID {slide_id}, {len(page_elements)} element(s)")

        logger.info(f"Presentation retrieved successfully for {user_google_email}")
        return f"""Presentation Details for {user_google_email}:
- Title: {title}
- Presentation ID: {presentation_id}
- URL: https://docs.google.com/presentation/d/{presentation_id}/edit
- Total Slides: {len(slides)}
- Page Size: {page_size.get('width', {}).get('magnitude', 'Unknown')} x {page_size.get('height', {}).get('magnitude', 'Unknown')} {page_size.get('width', {}).get('unit', '')}

Slides Breakdown:
{chr(10).join(slides_info) if slides_info else '  No slides found'}"""

    if operation == "page":
        if not page_object_id:
            raise Exception("Operation 'page' requires 'page_object_id'.")

        result = await asyncio.to_thread(
            service.presentations().pages().get(
                presentationId=presentation_id,
                pageObjectId=page_object_id
            ).execute
        )

        page_type = result.get('pageType', 'Unknown')
        page_elements = result.get('pageElements', [])

        elements_info = []
        for element in page_elements:
            element_id = element.get('objectId', 'Unknown')
            if 'shape' in element:
                shape_type = element['shape'].get('shapeType', 'Unknown')
                elements_info.append(f"  Shape: ID {element_id}, Type: {shape_type}")
            elif 'table' in element:
                table = element['table']
                rows = table.get('rows', 0)
                cols = table.get('columns', 0)
                elements_info.append(f"  Table: ID {element_id}, Size: {rows}x{cols}")
            elif 'line' in element:
                line_type = element['line'].get('lineType', 'Unknown')
                elements_info.append(f"  Line: ID {element_id}, Type: {line_type}")
            else:
                elements_info.append(f"  Element: ID {element_id}, Type: Unknown")

        logger.info(f"Page retrieved successfully for {user_google_email}")
        return f"""Page Details for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_object_id}
- Page Type: {page_type}
- Total Elements: {len(page_elements)}

Page Elements:
{chr(10).join(elements_info) if elements_info else '  No elements found'}"""

    if operation == "thumbnail":
        if not page_object_id:
            raise Exception("Operation 'thumbnail' requires 'page_object_id'.")

        result = await asyncio.to_thread(
            service.presentations().pages().getThumbnail(
                presentationId=presentation_id,
                pageObjectId=page_object_id,
                thumbnailProperties_thumbnailSize=thumbnail_size,
                thumbnailProperties_mimeType='PNG'
            ).execute
        )

        thumbnail_url = result.get('contentUrl', '')

        logger.info(f"Thumbnail generated successfully for {user_google_email}")
        return f"""Thumbnail Generated for {user_google_email}:
- Presentation ID: {presentation_id}
- Page ID: {page_object_id}
- Thumbnail Size: {thumbnail_size}
- Thumbnail URL: {thumbnail_url}

You can view or download the thumbnail using the provided URL."""

    raise Exception("Unsupported operation. Use 'presentation', 'page', or 'thumbnail'.")


# Create comment management tools for slides
_comment_tools = create_comment_tools("presentation", "presentation_id")
read_presentation_comments = _comment_tools['read_comments']
create_presentation_comment = _comment_tools['create_comment']
reply_to_presentation_comment = _comment_tools['reply_to_comment']
resolve_presentation_comment = _comment_tools['resolve_comment']

# Aliases for backwards compatibility and intuitive naming
read_slide_comments = read_presentation_comments
create_slide_comment = create_presentation_comment
reply_to_slide_comment = reply_to_presentation_comment
resolve_slide_comment = resolve_presentation_comment
