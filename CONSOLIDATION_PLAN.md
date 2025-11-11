# Google Workspace MCP Tool Consolidation Plan

## Executive Summary

**Goal:** Reduce tool count from 77 tools to ~45 tools (41% reduction) through operation-based consolidation.

**Status:** Phase 1 partially complete
- ✅ **Apps Script**: Added 5 new consolidated tools (ported from Node.js)
- ✅ **Tasks**: Consolidated 12 → 3 tools (75% reduction, -9 tools)
- ⏳ **Gmail**: Ready for consolidation (12 → 6 tools, -6 tools)
- ⏳ **Docs**: Ready for consolidation (14 → 7 tools, -7 tools)

**Current Progress:** 77 → 68 tools (12% reduction so far)

---

## Completed Work

### 1. Google Apps Script Integration ✅

**New Service Added:** `gappsscript/appsscript_tools.py`

Created 5 consolidated tools (replacing 16 from original Node.js implementation):

1. **`manage_script_project`** - Project CRUD
   - Operations: `create | get | get_content | update_content`
   - Replaces 4 separate tools

2. **`manage_script_version`** - Version management
   - Operations: `create | get | list`
   - Replaces 3 separate tools

3. **`manage_script_deployment`** - Deployment lifecycle
   - Operations: `create | get | list | update | delete`
   - Replaces 5 separate tools

4. **`execute_script`** - Run Apps Script functions
   - Single consolidated operation

5. **`monitor_script_execution`** - Process & metrics monitoring
   - Operations: `list_processes | get_metrics`
   - Replaces 3 separate tools

**Files Modified:**
- Created: `gappsscript/appsscript_tools.py` (598 lines)
- Updated: `auth/scopes.py` (added 5 Apps Script scopes)
- Updated: `auth/service_decorator.py` (added script service config)
- Updated: `main.py` (added 'script' to tool imports)

**Commit:** `83556e3` - "Add Google Apps Script MCP integration with 5 consolidated tools"

---

### 2. Google Tasks Consolidation ✅

**File:** `gtasks/tasks_tools.py`

**Before (12 tools):**
```
Task Lists:
- list_task_lists
- get_task_list
- create_task_list
- update_task_list
- delete_task_list

Tasks:
- list_tasks
- get_task
- create_task
- update_task
- delete_task
- move_task

Special:
- clear_completed_tasks
```

**After (3 tools):**

1. **`manage_task_list`** (replaces 5 tools)
   ```python
   operation: Literal["list", "get", "create", "update", "delete"]
   task_list_id: Optional[str]  # required for get/update/delete
   title: Optional[str]  # required for create/update
   max_results: int = 1000
   page_token: Optional[str]
   ```

2. **`manage_task`** (replaces 6 tools)
   ```python
   operation: Literal["list", "get", "create", "update", "delete", "move"]
   task_list_id: str  # always required
   task_id: Optional[str]  # required for get/update/delete/move
   title, notes, status, due: Optional parameters
   parent, previous, destination_task_list: Optional[str]
   # Plus 10+ list filtering parameters
   ```

3. **`clear_completed_tasks`** (unchanged - special operation)
   ```python
   # Kept as distinct tool (bulk operation with no variants)
   ```

**Preserved Features:**
- ✅ All helper functions maintained
- ✅ `StructuredTask` class for hierarchical tasks
- ✅ Multi-page pagination logic
- ✅ Due date boundary adjustments
- ✅ Task positioning and movement
- ✅ Comprehensive filtering options

**Reduction:** 12 → 3 tools (75% reduction, -9 tools)

**Commit:** `19602d4` - "Consolidate Google Tasks tools from 12 to 3 (75% reduction)"

---

## Remaining Work

### Phase 1: Core Services (In Progress)

#### 3. Gmail Consolidation (12 → 6 tools) ⏳

**Current Tools:**
```
1. search_gmail_messages  → KEEP
2. get_gmail_message_content  ↘
3. get_gmail_messages_content_batch  → CONSOLIDATE to get_gmail_content
4. get_gmail_attachment_content  ↗
5. send_gmail_message  → KEEP
6. draft_gmail_message  → KEEP
7. get_gmail_thread_content  ↘
8. get_gmail_threads_content_batch  → CONSOLIDATE to get_gmail_content
9. list_gmail_labels  → KEEP
10. manage_gmail_label  → KEEP (already consolidated)
11. modify_gmail_message_labels  → CONSOLIDATE to modify_gmail_labels
12. batch_modify_gmail_message_labels  ↗
```

**Target Tools:**

1. **`search_gmail_messages`** ✅ (unchanged)
2. **`get_gmail_content`** 🆕 (consolidates 5 → 1)
   ```python
   operation: Literal["message", "messages_batch", "thread", "threads_batch", "attachment"]
   message_id: Optional[str]  # for message/thread
   message_ids: Optional[List[str]]  # for batch operations
   thread_id: Optional[str]  # for thread
   thread_ids: Optional[List[str]]  # for threads_batch
   attachment_id: Optional[str]  # for attachment
   format: str = "full"
   ```

3. **`send_gmail_message`** ✅ (unchanged)
4. **`draft_gmail_message`** ✅ (unchanged)
5. **`manage_gmail_label`** ✅ (already good)
6. **`modify_gmail_labels`** 🆕 (consolidates 2 → 1)
   ```python
   operation: Literal["single", "batch"]
   message_id: Optional[str]  # for single
   message_ids: Optional[List[str]]  # for batch
   add_label_ids: Optional[List[str]]
   remove_label_ids: Optional[List[str]]
   ```

**Helper Functions to Preserve:**
- `_extract_message_body()`
- `_extract_message_bodies()`
- `_format_body_content()`
- `_extract_attachments()`
- `_extract_headers()`
- `_prepare_gmail_message()`
- `_generate_gmail_web_url()`
- `_format_gmail_results_plain()`

**Implementation Notes:**
- File: `gmail/gmail_tools.py` (1340 lines)
- Preserve all helper functions (lines 1-320)
- Keep tools at lines: 321 (search), 626 (send), 692 (draft), 1162 (manage_label)
- Replace remaining 7 tools with 2 consolidated versions
- All existing functionality must be preserved

---

#### 4. Docs Consolidation (14 → 7 tools) ⏳

**Current Tools:**
```
1. search_docs  → KEEP
2. get_doc_content  → KEEP
3. list_docs_in_folder  → KEEP
4. create_doc  → KEEP
5. modify_doc_text  ↘
6. find_and_replace_doc  → CONSOLIDATE to modify_doc_content
7. update_doc_headers_footers  ↗
8. insert_doc_elements  ↘
9. insert_doc_image  → CONSOLIDATE to insert_doc_elements (enhanced)
10. create_table_with_data  ↗
11. batch_update_doc  ↘
12. inspect_doc_structure  → CONSOLIDATE to manage_doc_operations
13. debug_table_structure  ↗
14. export_doc_to_pdf  ↗
```

**Target Tools:**

1. **`search_docs`** ✅
2. **`get_doc_content`** ✅
3. **`list_docs_in_folder`** ✅
4. **`create_doc`** ✅
5. **`modify_doc_content`** 🆕 (consolidates 3 → 1)
   ```python
   operation: Literal["edit_text", "find_replace", "headers_footers"]
   document_id: str
   # Operation-specific parameters
   ```

6. **`insert_doc_elements`** 🆕 (consolidates 3 → 1, enhanced)
   ```python
   operation: Literal["table", "image", "elements"]
   document_id: str
   # Supports all insertion types
   ```

7. **`manage_doc_operations`** 🆕 (consolidates 3 → 1)
   ```python
   operation: Literal["batch_update", "inspect_structure", "debug_table", "export_pdf"]
   document_id: str
   # Operation-specific parameters
   ```

---

### Phase 2: Data Services (Not Started)

#### 5. Drive Consolidation (6 → 4 tools) ⏳

**Consolidation:**
- Keep: `search_drive_files`, `get_drive_file_content`, `create_drive_file`
- Consolidate permissions: `get_drive_file_permissions` + `check_drive_file_public_access` → `manage_drive_permissions`
- Remove: `list_drive_items` (duplicate of search with folder filter)

**Reduction:** -2 tools

---

#### 6. Sheets Consolidation (6 → 4 tools) ⏳

**Consolidation:**
- `list_spreadsheets` + `get_spreadsheet_info` → `get_spreadsheet_info` (operation: list | get)
- `create_spreadsheet` + `create_sheet` → `create_spreadsheet` (operation: new_spreadsheet | add_sheet)
- Keep: `read_sheet_values`, `modify_sheet_values`

**Reduction:** -2 tools

---

### Phase 3: Content Services (Not Started)

#### 7. Forms Consolidation (5 → 3 tools) ⏳

- `get_form` + `set_publish_settings` → `manage_form` (operation: get | set_publish_settings)
- `get_form_response` + `list_form_responses` → `get_form_responses` (operation: get_single | list)
- Keep: `create_form`

**Reduction:** -2 tools

---

#### 8. Slides Consolidation (5 → 3 tools) ⏳

- `get_presentation` + `get_page` + `get_page_thumbnail` → `get_presentation_info` (operation: presentation | page | thumbnail)
- Keep: `create_presentation`, `batch_update_presentation`

**Reduction:** -2 tools

---

#### 9. Chat Consolidation (4 → 3 tools) ⏳

- `get_messages` + `search_messages` → `get_chat_messages` (operation: get | search)
- Keep: `list_spaces`, `send_message`

**Reduction:** -1 tool

---

#### 10. Search Consolidation (3 → 2 tools) ⏳

- `search_custom` + `search_custom_siterestrict` → `search_custom` (add site_restrict parameter)
- Keep: `get_search_engine_info`

**Reduction:** -1 tool

---

### Phase 4: No Changes

#### 11. Calendar ✅ (5 tools - already optimal)

Tools are already well-organized:
- `list_calendars`
- `get_events`
- `create_event`
- `modify_event`
- `delete_event`

**No changes needed.**

---

## Implementation Checklist

### For Each Service Consolidation:

**1. Code Changes:**
- [ ] Read existing tool file
- [ ] Identify tools to consolidate
- [ ] Create new consolidated tool functions with operation parameter
- [ ] Add `Literal` type hints for operation parameter
- [ ] Implement operation routing logic with clear conditionals
- [ ] Add comprehensive parameter validation
- [ ] Update docstrings with all operation modes and examples
- [ ] Preserve all existing decorators (@server.tool, @require_google_service)
- [ ] Keep all helper functions intact

**2. Testing:**
- [ ] Test each operation variant manually if possible
- [ ] Verify error handling for invalid operations
- [ ] Check parameter validation edge cases
- [ ] Confirm all original functionality preserved

**3. Documentation:**
- [ ] Update tool docstrings with operation examples
- [ ] Document parameter requirements per operation
- [ ] Add usage examples in docstrings

**4. Commit:**
- [ ] Stage changes: `git add <file>`
- [ ] Create descriptive commit message
- [ ] Push: `git push -u origin claude/integrate-google-apps-mcp-011CV1exjSRJGijyVnq9kYoE`

---

## Final Target Summary

| Service | Current | Target | Reduction | Status |
|---------|---------|--------|-----------|---------|
| **Apps Script** | 0 | +5 | +5 new | ✅ Done |
| **Tasks** | 12 | 3 | -9 (75%) | ✅ Done |
| **Gmail** | 12 | 6 | -6 (50%) | ⏳ Ready |
| **Docs** | 14 | 7 | -7 (50%) | ⏳ Ready |
| **Drive** | 6 | 4 | -2 (33%) | ⏳ Planned |
| **Sheets** | 6 | 4 | -2 (33%) | ⏳ Planned |
| **Forms** | 5 | 3 | -2 (40%) | ⏳ Planned |
| **Slides** | 5 | 3 | -2 (40%) | ⏳ Planned |
| **Chat** | 4 | 3 | -1 (25%) | ⏳ Planned |
| **Search** | 3 | 2 | -1 (33%) | ⏳ Planned |
| **Calendar** | 5 | 5 | 0 (0%) | ✅ Optimal |
| **TOTAL** | **77** | **45** | **-32 (41%)** | **12% done** |

---

## Success Criteria

- [x] Apps Script integration complete with 5 consolidated tools
- [x] Tasks reduced from 12 to 3 tools (proof of concept)
- [ ] Gmail reduced from 12 to 6 tools
- [ ] Docs reduced from 14 to 7 tools
- [ ] Remaining services consolidated per plan
- [ ] All existing functionality preserved
- [ ] Consistent operation parameter pattern across all services
- [ ] Zero breaking changes to API contracts
- [ ] All tests pass (if tests exist)

---

## Benefits

**For AI Agents:**
- Easier tool discovery (fewer tools to choose from)
- Clearer tool purposes (operation parameter makes intent explicit)
- Reduced token usage in tool listings
- Consistent patterns across all services

**For Developers:**
- Easier to maintain (less code duplication)
- Clearer API surface
- Consistent patterns reduce cognitive load
- Better organization

**For Users:**
- Faster responses (fewer tools to evaluate)
- More predictable behavior
- Easier to understand capabilities

---

## Next Steps

1. **Complete Phase 1:**
   - [ ] Consolidate Gmail (12 → 6)
   - [ ] Consolidate Docs (14 → 7)
   - [ ] Test Phase 1 consolidations
   - [ ] Commit Phase 1

2. **Execute Phase 2:**
   - [ ] Consolidate Drive (6 → 4)
   - [ ] Consolidate Sheets (6 → 4)
   - [ ] Commit Phase 2

3. **Execute Phase 3:**
   - [ ] Consolidate Forms, Slides, Chat, Search
   - [ ] Final testing
   - [ ] Final commit

4. **Documentation & Release:**
   - [ ] Update README with new tool structure
   - [ ] Create migration guide if needed
   - [ ] Tag release version

---

## Pattern Examples

### Example: Consolidated Tool Pattern

```python
@server.tool()
@require_google_service("service_name", ["scope1", "scope2"])
@handle_http_errors("tool_name", service_type="service")
async def manage_resource(
    service: Resource,
    user_google_email: str,
    operation: Literal["list", "get", "create", "update", "delete"],
    resource_id: Optional[str] = None,
    # Common parameters
    title: Optional[str] = None,
    # Operation-specific parameters
    ...
) -> str:
    """
    Manage resources: list, get, create, update, or delete.

    Args:
        user_google_email (str): User's Google email. Required.
        operation (str): Operation: "list", "get", "create", "update", "delete".
        resource_id (Optional[str]): Resource ID (required for get/update/delete).
        title (Optional[str]): Resource title (required for create/update).
        ...

    Returns:
        str: Operation result with resource details.

    Examples:
        # List resources
        manage_resource(operation="list", max_results=100)

        # Get resource
        manage_resource(operation="get", resource_id="abc123")

        # Create resource
        manage_resource(operation="create", title="New Resource")
    """
    logger.info(f"[manage_resource] Operation: {operation}")

    try:
        if operation == "list":
            # List implementation
            ...

        elif operation == "get":
            if not resource_id:
                raise ValueError("'resource_id' required for get")
            # Get implementation
            ...

        elif operation == "create":
            if not title:
                raise ValueError("'title' required for create")
            # Create implementation
            ...

        elif operation == "update":
            if not resource_id or not title:
                raise ValueError("'resource_id' and 'title' required for update")
            # Update implementation
            ...

        elif operation == "delete":
            if not resource_id:
                raise ValueError("'resource_id' required for delete")
            # Delete implementation
            ...

        else:
            raise ValueError(f"Invalid operation: {operation}")

    except HttpError as error:
        # Error handling
        ...
```

---

## Commit History

1. **`83556e3`** - Add Google Apps Script MCP integration with 5 consolidated tools
2. **`19602d4`** - Consolidate Google Tasks tools from 12 to 3 (75% reduction)
3. **(Next)** - Consolidate Gmail tools from 12 to 6 (50% reduction)
4. **(Next)** - Consolidate Docs tools from 14 to 7 (50% reduction)
5. **(Next)** - Phase 2 and 3 consolidations

---

*Last Updated: 2025-01-11*
*Branch: `claude/integrate-google-apps-mcp-011CV1exjSRJGijyVnq9kYoE`*
